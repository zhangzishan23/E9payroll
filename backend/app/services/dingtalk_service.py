"""
钉钉内部应用服务模块
- access_token 管理（缓存 + 自动刷新）
- 员工花名册同步（全量/增量）
- 考勤报表数据同步（月度汇总 + 每日明细）
- 同步日志记录
- 数据校验
"""
import time
import logging
import calendar
import re
from datetime import datetime, date, timedelta
from typing import Optional
import httpx

from app.core.config import DINGTALK_CLIENT_ID, DINGTALK_CLIENT_SECRET, DINGTALK_AGENT_ID, DINGTALK_SYNC_DEPT_NAMES
from app.models.models import SysDictBase
from app.services import work_calendar as work_cal

logger = logging.getLogger(__name__)


def _safe_str(value, max_len=200):
    """截断字符串，防止超长值导致数据库写入失败"""
    if not value:
        return ""
    return str(value)[:max_len]

# ========== Token 缓存 ==========
_token_cache: dict = {
    "access_token": None,
    "expires_at": 0,  # Unix timestamp
}


def _get_access_token() -> str:
    """获取旧版 access_token（用于考勤/用户详情等旧版API），带缓存"""
    now = time.time()
    if _token_cache["access_token"] and _token_cache["expires_at"] > now + 60:
        return _token_cache["access_token"]

    url = "https://oapi.dingtalk.com/gettoken"
    params = {"appkey": DINGTALK_CLIENT_ID, "appsecret": DINGTALK_CLIENT_SECRET}
    with httpx.Client(timeout=30) as client:
        resp = client.get(url, params=params)
        data = resp.json()
    if data.get("errcode") != 0:
        raise Exception(f"获取钉钉access_token失败: {data.get('errmsg', '未知错误')}")

    _token_cache["access_token"] = data["access_token"]
    _token_cache["expires_at"] = now + data.get("expires_in", 7200)
    logger.info("钉钉 access_token 已刷新，有效期至 %s", datetime.fromtimestamp(_token_cache["expires_at"]))
    return _token_cache["access_token"]


# ========== 同步日志 ==========

def _write_sync_log(db_session, sync_type: str, status: str, period: str = None,
                    total_count: int = 0, success_count: int = 0, failed_count: int = 0,
                    created_count: int = 0, updated_count: int = 0,
                    error_detail: list = None, started_at: datetime = None,
                    finished_at: datetime = None) -> int:
    """记录同步日志到数据库，返回日志ID"""
    from app.models.models import DingtalkSyncLog
    duration = None
    if started_at and finished_at:
        duration = round((finished_at - started_at).total_seconds(), 2)
    log_entry = DingtalkSyncLog(
        sync_type=sync_type,
        status=status,
        period=period,
        total_count=total_count,
        success_count=success_count,
        failed_count=failed_count,
        created_count=created_count,
        updated_count=updated_count,
        error_detail=error_detail or [],
        started_at=started_at or datetime.now(),
        finished_at=finished_at,
        duration_seconds=duration,
    )
    db_session.add(log_entry)
    db_session.commit()
    return log_entry.id


# ========== 花名册相关 ==========

# ========== 花名册字段元数据 ==========

# 花名册字段 code → 中文名映射（完整版，覆盖钉钉返回的93个字段）
ROSTER_FIELD_MAP = {
    # sys00 - 基本信息
    "sys00-name": "姓名",
    "sys00-workPlace": "办公地点",
    "sys00-mobile": "手机号",
    "sys00-email": "邮箱",
    "sys00-dept": "部门",
    "sys00-position": "职位",
    "sys00-confirmJoinTime": "入职时间",
    "sys00-entryAge": "司龄",
    "sys00-jobNumber": "工号",
    "sys00-reportManager": "直属主管",
    "sys00-remark": "备注",
    "sys00-deptIds": "部门id",
    "sys00-mainDept": "主部门",
    "sys00-mainDeptId": "主部门id",
    "sys00-reportManagerId": "直属主管id",
    "sys00-idCard": "身份证号",
    "sys00-gender": "性别",
    "sys00-staffStatus": "员工状态",
    "sys00-hiredDate": "入职日期",
    "sys00-regularDate": "转正日期",
    "sys00-resignDate": "离职日期",
    # sys01 - 工作信息
    "sys01-employeeType": "员工类型",
    "sys01-employeeStatus": "员工状态",
    "sys01-probationPeriodType": "试用期",
    "sys01-regularTime": "实际转正日期",
    "sys01-positionLevel": "岗位职级",
    "sys01-planRegularTime": "计划转正日期",
    # sys02 - 个人信息
    "sys02-realName": "身份证姓名",
    "sys02-certNo": "证件号码",
    "sys02-birthTime": "出生日期",
    "sys02-certEndTime": "证件有效期",
    "sys02-certAddress": "身份证地址",
    "sys02-age": "年龄",
    "sys02-sexType": "性别",
    "sys02-nationType": "民族",
    "sys02-marriage": "婚姻状况",
    "sys02-joinWorkingTime": "首次参加工作时间",
    "sys02-workAge": "工龄",
    "sys02-politicalStatus": "政治面貌",
    "sys02-residenceType": "户籍类型",
    "sys02-address": "住址",
    # sys03 - 学历信息（has_detail=True）
    "sys03-highestEdu": "学历",
    "sys03-graduateSchool": "毕业院校",
    "sys03-graduationTime": "毕业时间",
    "sys03-major": "所学专业",
    # sys04 - 银行卡
    "sys04-bankAccountNo": "银行卡号",
    "sys04-accountBank": "开户行",
    # sys05 - 合同信息
    "sys05-contractCompanyName": "合同公司",
    "sys05-contractType": "合同类型",
    "sys05-nowContractStartTime": "现合同起始日",
    "sys05-nowContractEndTime": "现合同到期日",
    "sys05-contractPeriodType": "合同期限",
    "sys05-contractRenewCount": "续签次数",
    "sys05-firstContractStartTime": "首次合同起始日",
    "sys05-firstContractEndTime": "首次合同到期日",
    # sys06 - 紧急联系人（has_detail=True）
    "sys06-urgentContactsName": "紧急联系人姓名",
    "sys06-urgentContactsRelation": "联系人关系",
    "sys06-urgentContactsPhone": "联系人电话",
    # sys07 - 家庭成员（has_detail=True）
    "sys07-familyMemberName": "家人姓名",
    "sys07-familyMemberRelation": "家人关系",
    "sys07-familyMemberGender": "家人性别",
    "sys07-familyMemberPhone": "家人电话",
    # sys08 - 附件（DDPhotoField，不可通过API下载）
    "sys08-forntIDcard": "身份证(人像面)",
    "sys08-rearIDcard": "身份证(国徽面)",
    "sys08-academicCertificate": "学历证书",
    "sys08-diplomaCertificate": "学位证书",
    "sys08-releaseLetter": "前公司离职证明",
    "sys08-personalPhoto": "员工照片",
    # sys - 其他
    "sys-authRealName": "实人认证",
}

# 自定义字段 code → 中文名映射（根据grouplist接口实际返回）
CUSTOM_FIELD_MAP = {
    "9fb7651f-40dd-42ea-b197-a95bbb832c42": "中心",
    "9e199205-1337-44e2-94e8-624a92adca9f": "招聘渠道",
    "81922c26-7b0a-40fe-b87c-7373b85a8941": "岗位级别",
    "d4a63ed6-0fbd-4322-ae7e-d899d5c7bd16": "劳务外包类型",
    "1e8e7d6d-6f56-49fc-a7aa-215f3bb5361c": "子女情况",
    "e6535432-0334-4090-bc86-aeec046c45b7": "籍贯",
    "5cb3709a-2ccf-431f-9425-c58f534797a0": "户口簿编号",
    "90300477-bcc9-4c70-a5ee-dbc256df20c5": "特长爱好",
    "453a8588-af7c-46d2-9d36-621164ebbd40": "座右铭",
    "2c28c75c-6a0b-4f90-9ad2-4b71a2c607b4": "身高（cm）",
    "3cbb7191-f4bf-4f86-b61c-814de450adee": "体重（kg）",
    "08824c8f-e380-4f33-b281-03ff49261847": "鞋码",
    "89474793-54fe-4cc8-bbb0-b21a834949dc": "资格证/职称证1",
    "cba563d1-96cd-4739-89e3-18f912bb707e": "资格证/职称证2",
    "c973eb37-4d74-47c3-b84a-c685e73b1e30": "开户行支行",
    "84541989-70e9-4794-9ad8-0717e2ff7be7": "首次签订合同公司",
    "69141b50-0603-490c-939c-259dafe84fcc": "第二次合同起始日",
    "cb577265-8cab-44aa-9b14-1409c3c15eaa": "第二次合同到期日",
    "ca3e7ac2-4844-465b-bb1f-cdb3d701c29d": "变更记录1",
    "bdbef3fb-3e38-4641-9be9-e57817bf8525": "体检报告",
    "41072566-393c-42a7-87f9-b9918179428d": "资格证书",
    "6d119e8d-0cde-4d73-975d-85d15174d0d0": "五险一金起购日期",
    "6ea63544-3d03-47aa-929d-8995277029c4": "社保公积金购买地",
    "fd1cc8aa-8af7-4574-bba4-1986d5acff03": "商业保险类型",
    # 工作经历（明细字段组）
    "13ace56f-d599-4b34-9588-acd5c58f9e6f": "公司名称",
    "9adbcc3a-d697-4b50-8f59-723d8ef7303e": "开始日期",
    "359578f8-2314-47a4-a9c4-33c3e30f57f3": "结束日期",
    "20d2e3ee-ba37-486b-9e97-c11c4a4fd518": "岗位",
    "c3bd6e51-7472-4688-8d19-b653fb78c4d9": "证明人",
    "58bae458-2818-4376-b0d0-8a2fa4bddeb6": "证明人联系方式",
}

# 合并所有字段映射
ALL_FIELD_MAP = {**ROSTER_FIELD_MAP, **CUSTOM_FIELD_MAP}

# 需要同步到 Employee 表的字段 code 列表（排除附件类型、明细字段、计算字段）
ROSTER_FIELD_CODES = [
    # sys00 - 基本信息
    "sys00-name", "sys00-workPlace", "sys00-mobile", "sys00-email",
    "sys00-dept", "sys00-position", "sys00-confirmJoinTime", "sys00-jobNumber",
    "sys00-reportManager", "sys00-remark", "sys00-mainDept",
    "sys00-idCard", "sys00-gender", "sys00-staffStatus",
    "sys00-hiredDate", "sys00-regularDate", "sys00-resignDate",
    # sys01 - 工作信息
    "sys01-employeeType", "sys01-employeeStatus", "sys01-positionLevel",
    "sys01-planRegularTime", "sys01-regularTime",
    # sys02 - 个人信息
    "sys02-certNo", "sys02-birthTime", "sys02-certAddress", "sys02-sexType",
    "sys02-nationType", "sys02-marriage", "sys02-joinWorkingTime",
    "sys02-politicalStatus", "sys02-residenceType", "sys02-address",
    # sys03 - 学历信息
    "sys03-highestEdu", "sys03-graduateSchool", "sys03-graduationTime", "sys03-major",
    # sys04 - 银行卡
    "sys04-bankAccountNo", "sys04-accountBank",
    # sys05 - 合同信息
    "sys05-contractCompanyName", "sys05-contractType",
    "sys05-nowContractStartTime", "sys05-nowContractEndTime",
    # sys06 - 紧急联系人
    "sys06-urgentContactsName", "sys06-urgentContactsRelation", "sys06-urgentContactsPhone",
    # 自定义字段
    "9e199205-1337-44e2-94e8-624a92adca9f",  # 招聘渠道
    "81922c26-7b0a-40fe-b87c-7373b85a8941",  # 岗位级别
    "1e8e7d6d-6f56-49fc-a7aa-215f3bb5361c",  # 子女情况
    "e6535432-0334-4090-bc86-aeec046c45b7",  # 籍贯
    "90300477-bcc9-4c70-a5ee-dbc256df20c5",  # 特长爱好
    "89474793-54fe-4cc8-bbb0-b21a834949dc",  # 资格证/职称证1
    "cba563d1-96cd-4739-89e3-18f912bb707e",  # 资格证/职称证2
    "c973eb37-4d74-47c3-b84a-c685e73b1e30",  # 开户行支行
    "6d119e8d-0cde-4d73-975d-85d15174d0d0",  # 五险一金起购日期
    "6ea63544-3d03-47aa-929d-8995277029c4",  # 社保公积金购买地
    "fd1cc8aa-8af7-4574-bba4-1986d5acff03",  # 商业保险类型
]


def get_roster_by_user_ids(user_ids: list[str]) -> list[dict]:
    """
    根据 userId 列表获取花名册信息。
    返回: [{"userId": "xxx", "fieldCode": "sys00-name", "fieldName": "姓名", "value": "张三"}, ...]
    """
    token = _get_access_token()
    url = "https://api.dingtalk.com/v1.0/hrm/rosters/lists/query"
    headers = {
        "x-acs-dingtalk-access-token": token,
        "Content-Type": "application/json",
    }
    body = {
        "userIdList": user_ids,
        "fieldFilterList": ROSTER_FIELD_CODES,
        "appAgentId": int(DINGTALK_AGENT_ID) if DINGTALK_AGENT_ID else 0,
    }
    with httpx.Client(timeout=60) as client:
        resp = client.post(url, headers=headers, json=body)
        data = resp.json()
    
    # API 直接返回 result 列表，没有 success 字段
    result = data.get("result", [])
    if not result and "result" not in data:
        raise Exception(f"获取花名册失败: {data}")
    # 展平为列表，每条记录包含 userId + 字段信息
    # API 返回结构: [{userId, fieldDataList: [{fieldCode, fieldValueList: [{label, value}]}]}]
    flat = []
    for item in result:
        user_id = item.get("userId", "")
        for field in item.get("fieldDataList", []):
            field_code = field.get("fieldCode", "")
            fv_list = field.get("fieldValueList", [])
            # fieldValueList 可能有多条（如多部门），取第一条
            label = fv_list[0].get("label", "") if fv_list else ""
            value = fv_list[0].get("value", "") if fv_list else ""
            flat.append({
                "userId": user_id,
                "fieldCode": field_code,
                "fieldName": ALL_FIELD_MAP.get(field_code, field_code),
                "value": value,
                "label": label,
            })
    return flat


# ========== 部门树 ==========

def get_dept_tree() -> dict[int, dict]:
    """
    获取企业完整部门树。
    返回: {dept_id: {"name": str, "parent_id": int, "sub_ids": [int]}, ...}
    """
    token = _get_access_token()
    dept_map: dict[int, dict] = {}

    def _fetch_sub(dept_id: int):
        url = "https://oapi.dingtalk.com/topapi/v2/department/listsub"
        params = {"access_token": token}
        with httpx.Client(timeout=30) as client:
            resp = client.post(url, params=params, json={"dept_id": dept_id})
            data = resp.json()
        if data.get("errcode") != 0:
            return
        for d in data.get("result", []):
            did = d.get("dept_id", 0)
            dept_map[did] = {
                "name": d.get("name", ""),
                "parent_id": d.get("parent_id", 0),
            }
            _fetch_sub(did)  # 递归获取子部门

    # 从根部门(1)开始递归
    dept_map[1] = {"name": "根部门", "parent_id": 0}
    _fetch_sub(1)
    return dept_map


def get_dept_name_to_root_map() -> dict[str, str]:
    """
    构建部门名称 → 根部门（一级部门）名称的映射。
    花名册返回的是员工实际所在子部门（如"工艺组"），需要追溯到根部门（如"物资供应部"）。
    返回: {"工艺组": "物资供应部", "总经室": "总经室", ...}
    """
    dept_map = get_dept_tree()
    # name → dept_id 映射
    name_to_id: dict[str, int] = {}
    for did, info in dept_map.items():
        name_to_id[info["name"]] = did

    # 对每个部门，追溯根部门
    name_to_root: dict[str, str] = {}
    for dept_name, dept_id in name_to_id.items():
        current = dept_id
        root_name = dept_name
        while current in dept_map:
            parent_id = dept_map[current]["parent_id"]
            if parent_id == 0 or parent_id == 1:
                # 到达根部门(1)或顶层
                if parent_id == 1 and current != 1:
                    root_name = dept_map[current]["name"]
                break
            current = parent_id
            root_name = dept_map[current]["name"]
        name_to_root[dept_name] = root_name

    return name_to_root


def get_root_departments() -> list[dict]:
    """
    获取钉钉一级部门（根部门）列表。
    返回: [{"dept_id": int, "name": str}, ...]
    """
    dept_map = get_dept_tree()
    roots = []
    for did, info in dept_map.items():
        if info["parent_id"] == 1 and did != 1:
            roots.append({"dept_id": did, "name": info["name"]})
    return sorted(roots, key=lambda x: x["name"])


def sync_root_depts_to_db(db_session) -> dict:
    """
    从钉钉获取所有部门（含子部门），同步到 sys_dict_base（category=department）。
    用钉钉 deptId 作为 code，新增不存在的部门。
    如果名称相同但 code 不同的已有部门，则更新其 code 和 parent_id 避免重复。
    同时更新 parent_id 以支持层级展示。
    返回: {"created": 0, "updated": 0, "skipped": 0}
    """
    from app.models.models import SysDictBase

    dept_map = get_dept_tree()
    all_db_depts = db_session.query(SysDictBase).filter(SysDictBase.category == "department").all()

    # 建立索引：code -> record, name.strip() -> record
    existing_by_code = {d.code: d for d in all_db_depts}
    existing_by_name = {}
    for d in all_db_depts:
        key = d.name.strip()
        if key not in existing_by_name:
            existing_by_name[key] = d

    created = 0
    updated = 0
    skipped = 0

    # 第一步：创建或更新部门
    for did, info in dept_map.items():
        if did == 1:  # 跳过钉钉根节点
            continue
        code = str(did)
        dept_name = info["name"].strip()

        if code in existing_by_code:
            # 已存在相同 code 的部门，检查是否需要更新名称
            existing = existing_by_code[code]
            if existing.name != dept_name:
                existing.name = dept_name
                updated += 1
            else:
                skipped += 1
        elif dept_name in existing_by_name:
            # code 不同但名称已存在 → 更新 code 避免重复
            existing = existing_by_name[dept_name]
            existing.code = code
            updated += 1
            # 更新索引
            existing_by_code[code] = existing
        else:
            # 全新部门
            db_session.add(SysDictBase(
                category="department",
                code=code,
                name=dept_name,
                sort_order=0,
                is_enabled=True,
            ))
            created += 1

    db_session.flush()  # 刷新以获取新创建的 ID

    # 第二步：重新加载所有部门，构建 code -> id 映射
    all_depts = db_session.query(SysDictBase).filter(SysDictBase.category == "department").all()
    code_to_id = {d.code: d.id for d in all_depts}

    # 第三步：更新 parent_id
    for d in all_depts:
        try:
            dingtalk_dept_id = int(d.code)
        except (ValueError, TypeError):
            continue
        info = dept_map.get(dingtalk_dept_id)
        if not info:
            continue
        parent_dingtalk_id = info.get("parent_id", 0)
        if parent_dingtalk_id and parent_dingtalk_id != 1:
            parent_code = str(parent_dingtalk_id)
            parent_db_id = code_to_id.get(parent_code)
            if parent_db_id and d.parent_id != parent_db_id:
                d.parent_id = parent_db_id

    db_session.commit()
    return {"created": created, "updated": updated, "skipped": skipped, "total": len(dept_map) - 1}


def get_target_dept_ids(db_session=None) -> list[int]:
    """
    从数据库读取已启用的部门，通过 code 或 name 匹配钉钉部门树，获取需要同步的部门ID列表。
    优先用数字 code（钉钉 deptId）匹配，其次用部门名称匹配。
    """
    from app.models.models import SysDictBase

    dept_map = get_dept_tree()

    # 从数据库读取所有已启用的部门
    if db_session:
        enabled_depts = db_session.query(SysDictBase).filter(
            SysDictBase.category == "department",
            SysDictBase.is_enabled == True,
        ).all()
    else:
        from app.core.database import SessionLocal
        db = SessionLocal()
        try:
            enabled_depts = db.query(SysDictBase).filter(
                SysDictBase.category == "department",
                SysDictBase.is_enabled == True,
            ).all()
        finally:
            db.close()

    # 构建钉钉部门 name→id 映射（用于按名称匹配）
    dept_name_to_id = {info["name"]: did for did, info in dept_map.items() if did != 1}

    target_ids: set[int] = set()
    matched_by_code = 0
    matched_by_name = 0
    for d in enabled_depts:
        # 方式1：code 是数字 → 直接作为钉钉 deptId 匹配
        if d.code and d.code.isdigit():
            dept_id = int(d.code)
            if dept_id in dept_map:
                target_ids.add(dept_id)
                matched_by_code += 1
                continue
        # 方式2：用部门名称去钉钉部门树中查找对应 deptId
        if d.name:
            dept_id = dept_name_to_id.get(d.name.strip())
            if dept_id:
                target_ids.add(dept_id)
                matched_by_name += 1

    if not target_ids:
        logger.warning("没有已启用的部门能匹配到钉钉部门树（code匹配%d个，名称匹配%d个），同步将跳过所有部门",
                      matched_by_code, matched_by_name)
        return []

    logger.info("目标部门匹配完成：code匹配%d个，名称匹配%d个，共%d个钉钉部门",
                matched_by_code, matched_by_name, len(target_ids))
    return list(target_ids)


def get_all_user_ids(db_session=None) -> list[str]:
    """
    获取需要同步部门的员工 userId 列表。
    从数据库读取已启用部门过滤，只同步指定部门的员工。
    """
    token = _get_access_token()
    all_users = []

    # 获取目标部门ID列表（根据数据库已启用部门过滤）
    target_dept_ids = get_target_dept_ids(db_session)
    if not target_dept_ids:
        logger.warning("未找到需要同步的部门，请在数据字典中启用部门")
        return []

    logger.info("钉钉同步目标部门ID: %s", target_dept_ids)

    # 通过部门遍历获取用户列表
    url = "https://oapi.dingtalk.com/topapi/user/listsimple"
    headers = {"Content-Type": "application/json"}
    with httpx.Client(timeout=30) as client:
        for dept_id in target_dept_ids:
            body = {"dept_id": dept_id, "cursor": 0, "size": 100}
            params = {"access_token": token}
            while True:
                resp = client.post(url, params=params, json=body, headers=headers)
                data = resp.json()
                if data.get("errcode") != 0:
                    break  # 某个部门无权限，跳过
                result = data.get("result", {})
                users = result.get("list", [])
                all_users.extend(u.get("userid", "") for u in users)
                if not result.get("has_more"):
                    break
                body["cursor"] = result.get("next_cursor", 0)

    return list(set(all_users))  # 去重


def get_all_dingtalk_user_ids_from_all_depts() -> list[str]:
    """
    直接从钉钉获取所有部门的所有员工 userId（不经过数据库部门过滤）。
    用于原始数据导出等需要完整数据的场景。
    """
    token = _get_access_token()
    all_users = []
    dept_map = get_dept_tree()
    headers = {"Content-Type": "application/json"}

    for dept_id in dept_map:
        if dept_id == 1:  # 根部门跳过
            continue
        url = "https://oapi.dingtalk.com/topapi/user/listsimple"
        params = {"access_token": token}
        body = {"dept_id": dept_id, "cursor": 0, "size": 100}
        try:
            with httpx.Client(timeout=30) as client:
                resp = client.post(url, params=params, json=body, headers=headers)
                data = resp.json()
            if data.get("errcode") == 0:
                result = data.get("result", {})
                users = result.get("list", [])
                all_users.extend(u.get("userid", "") for u in users)
        except Exception:
            pass

    return list(set(all_users))  # 去重


# ========== 考勤相关 ==========

def get_attendance_columns() -> list[dict]:
    """获取考勤报表列定义。返回: [{"id": 123, "name": "应出勤天数", "type": 1}, ...]"""
    token = _get_access_token()
    url = "https://oapi.dingtalk.com/topapi/attendance/getattcolumns"
    params = {"access_token": token}
    with httpx.Client(timeout=30) as client:
        resp = client.post(url, params=params)
        data = resp.json()
    if data.get("errcode") != 0:
        raise Exception(f"获取考勤报表列定义失败: {data.get('errmsg')}")

    result = data.get("result", {})
    columns = result.get("columns", [])
    logger.info(f"钉钉返回考勤列定义: {[c.get('name') for c in columns]}")
    return [{"id": c.get("id"), "name": c.get("name"), "type": c.get("type")} for c in columns]


def get_attendance_groups() -> list[dict]:
    """批量获取所有考勤组。返回: [{"group_id": 123, "group_name": "考勤组名", "member_count": 10}, ...]"""
    token = _get_access_token()
    url = "https://oapi.dingtalk.com/topapi/attendance/getsimplegroups"
    params = {"access_token": token}
    groups = []
    offset = 0
    size = 10

    with httpx.Client(timeout=30) as client:
        while True:
            body = {"offset": offset, "size": size}
            resp = client.post(url, params=params, json=body)
            data = resp.json()
            if data.get("errcode") != 0:
                raise Exception(f"获取考勤组列表失败: {data.get('errmsg')}")

            result = data.get("result", {})
            batch = result.get("groups", [])
            groups.extend({
                "group_id": g.get("group_id"),
                "group_name": g.get("group_name"),
                "member_count": g.get("member_count", 0),
                "type": g.get("type"),
            } for g in batch)

            if not result.get("has_more"):
                break
            offset += size

    logger.info(f"钉钉返回考勤组: {[(g['group_name'], g['member_count']) for g in groups]}")
    return groups


def get_attendance_group_members(group_id: int) -> list[str]:
    """获取指定考勤组的参与考勤人员 userId 列表（仅返回 type=0 的员工，不含 type=1 的部门）"""
    token = _get_access_token()
    url = "https://oapi.dingtalk.com/topapi/attendance/group/member/list"
    params = {"access_token": token}
    user_ids = []
    cursor = 0

    with httpx.Client(timeout=30) as client:
        while True:
            body = {
                "group_id": group_id,
                "op_user_id": DINGTALK_AGENT_ID or "manager4220",
                "cursor": cursor,
            }
            resp = client.post(url, params=params, json=body)
            data = resp.json()
            if data.get("errcode") != 0:
                raise Exception(f"获取考勤组成员失败(group_id={group_id}): {data.get('errmsg')}")

            result = data.get("result", {})
            members = result.get("result", [])
            for m in members:
                # type=0 是员工，type=1 是部门（跳过部门）
                if m.get("type") == "0" and m.get("atc_flag") == "0":
                    user_ids.append(m.get("member_id"))

            if not result.get("has_more"):
                break
            cursor = result.get("cursor", 0)

    return user_ids


def get_all_attendance_user_ids() -> list[str]:
    """获取所有参与考勤的员工 userId（遍历所有考勤组成员并去重）"""
    groups = get_attendance_groups()
    all_ids = set()
    errors = []

    for group in groups:
        gid = group["group_id"]
        if group.get("member_count", 0) == 0:
            continue
        try:
            members = get_attendance_group_members(gid)
            all_ids.update(members)
            logger.info(f"考勤组 [{group['group_name']}]({gid}): 获取到 {len(members)} 人")
        except Exception as e:
            errors.append(str(e))
            logger.warning(f"获取考勤组成员失败: {e}")

    if errors:
        logger.warning(f"考勤组成员获取中有 {len(errors)} 个错误: {errors[:3]}")

    logger.info(f"所有考勤组去重后共 {len(all_ids)} 人参与考勤")
    return list(all_ids)


# 考勤列名 → 系统字段映射（根据钉钉实际返回的列名）
ATTENDANCE_COLUMN_MAP = {
    # === 基础考勤 ===
    "应出勤天数": "total_work_days",
    "出勤天数": "actual_work_days",
    "休息天数": "rest_days",
    "工作时长": "work_hours",

    # === 补卡 ===
    "补卡次数": "resupplement_count",

    # === 迟到 ===
    "迟到次数": "late_count",
    "迟到时长": "late_duration",
    "严重迟到次数": "severe_late_count",
    "严重迟到时长": "severe_late_duration",
    "旷工迟到次数": "absenteeism_late_count",
    "旷工迟到天数": "absenteeism_late_days",
    "迟到10分钟以上次数": "late_over_10min_count",
    "迟到30分钟以上次数": "late_over_30min_count",

    # === 早退 ===
    "早退次数": "early_count",
    "早退时长": "early_duration",

    # === 缺卡 ===
    "上班缺卡次数": "missed_clock_in_count",
    "下班缺卡次数": "missed_clock_out_count",
    "半天缺卡次数合计": "half_day_missed_punch",

    # === 旷工 ===
    "旷工天数": "absenteeism_days",

    # === 出差/外出 ===
    "出差时长": "business_travel_duration",
    "外出时长": "out_duration",

    # === 加班 ===
    "加班-审批单统计": "overtime_approval_count",
    "工作日加班": "workday_overtime",
    "休息日加班": "weekend_overtime",
    "节假日加班": "holiday_overtime",
    "加班总时长": "total_overtime",
    "工作日（转加班费）": "workday_overtime_pay",
    "休息日（转加班费）": "weekend_overtime_pay",
    "节假日（转加班费）": "holiday_overtime_pay",
    "工作日（转调休）": "workday_overtime_leave",
    "休息日（转调休）": "weekend_overtime_leave",
    "节假日（转调休）": "holiday_overtime_leave",

    # === 晚下班 ===
    "下班晚于7点次数": "clock_out_after_7pm_count",
    "下班晚于8点次数": "clock_out_after_8pm_count",
    "下班晚于9点次数": "clock_out_after_9pm_count",

    # === 打卡 ===
    "打卡次数": "punch_count",

    # === 请假类型（来自钉钉独立列，如有） ===
    "事假": "personal_leave_days",
    "事假(小时)": "personal_leave_days",
    "全薪病假": "full_pay_sick_days",
    "全薪病假(小时)": "full_pay_sick_days",
    "法定病假": "statutory_sick_days",
    "法定病假(天)": "statutory_sick_days",
    "减薪病假": "reduced_pay_sick_days",
    "减薪病假(小时)": "reduced_pay_sick_days",
    "年假": "annual_leave_days",
    "年假(天)": "annual_leave_days",
    "调休": "compensatory_leave_days",
    "调休(小时)": "compensatory_leave_days",
    "调休假天数": "compensatory_leave_days",
    "调休（综合工时）": "compensatory_leave_days",
    "调休-工程交付": "engineering_compensatory_days",
    "调休-工程交付（天）": "engineering_compensatory_days",
    "调休（工程交付）(天)": "engineering_compensatory_days",
    "产检假": "prenatal_checkup_days",
    "产检假(天)": "prenatal_checkup_days",
    "产假": "maternity_leave_days",
    "产假(天)": "maternity_leave_days",
    "陪产假": "paternity_leave_days",
    "陪产假(天)": "paternity_leave_days",
    "婚假": "marriage_leave_days",
    "婚假(天)": "marriage_leave_days",
    "丧假": "funeral_leave_days",
    "丧假(天)": "funeral_leave_days",
    # 带空格或全角括号的列名
    "旷工 （天数）": "absenteeism_days",
}


# 请假类型关键词 → 系统字段（用于从'考勤结果'文本解析）
LEAVE_KEYWORD_MAP = {
    "事假": "personal_leave_days",
    "全薪病假": "full_pay_sick_days",
    "减薪病假": "reduced_pay_sick_days",
    "法定病假": "statutory_sick_days",
    "病假": "sick_leave_days",
    "年假": "annual_leave_days",
    "调休-工程交付": "engineering_compensatory_days",
    "调休": "compensatory_leave_days",
    "产检假": "prenatal_checkup_days",
    "产假": "maternity_leave_days",
    "陪产假": "paternity_leave_days",
    "婚假": "marriage_leave_days",
    "丧假": "funeral_leave_days",
}


def parse_leave_from_result(attendance_result_text: str) -> list[dict]:
    """
    从钉钉'考勤结果'列文本解析请假信息。
    格式示例: "事假06-03 09:00到06-03 12:00 3小时"
    返回: [{"type": "事假", "field": "personal_leave_days", "hours": 3.0, "start": "06-03", "end": "06-03"}, ...]
    """
    if not attendance_result_text or attendance_result_text in ("正常", "休息", ""):
        return []

    import re
    results = []
    # 匹配: {请假类型}(可选具体内容) {月-日} {时:分}到{月-日} {时:分} {N}小时
    pattern = r'(事假|全薪病假|减薪病假|法定病假|病假|年假|调休-工程交付|调休|产检假|产假|陪产假|婚假|丧假)\S*\s*(\d{2}-\d{2})\s*(\d{2}:\d{2})到(\d{2}-\d{2})\s*(\d{2}:\d{2})\s*(\d+(?:\.\d+)?)小时'

    for match in re.finditer(pattern, attendance_result_text):
        leave_name = match.group(1)
        start_date = match.group(2)
        end_date = match.group(4)
        hours = float(match.group(6))

        # 匹配最长的关键词（如"调休-工程交付"优先于"调休"）
        field = None
        for keyword, field_name in sorted(LEAVE_KEYWORD_MAP.items(), key=lambda x: -len(x[0])):
            if leave_name == keyword or leave_name.startswith(keyword):
                field = field_name
                break

        if field:
            results.append({
                "type": leave_name,
                "field": field,
                "hours": hours,
                "start": start_date,
                "end": end_date,
            })

    return results


def get_attendance_column_values(
    user_id: str,
    column_ids: list[int],
    from_date: date,
    to_date: date,
) -> list[dict]:
    """
    按天获取员工考勤报表列值。
    返回: [{"date": "2024-06-01", "column_id": 123, "column_name": "应出勤天数", "value": "1.0"}, ...]
    """
    token = _get_access_token()
    url = "https://oapi.dingtalk.com/topapi/attendance/getcolumnval"
    params = {"access_token": token}
    body = {
        "userid": user_id,
        "column_id_list": ",".join(str(c) for c in column_ids),
        "from_date": datetime.combine(from_date, datetime.min.time()).strftime("%Y-%m-%d %H:%M:%S"),
        "to_date": datetime.combine(to_date, datetime.min.time()).strftime("%Y-%m-%d %H:%M:%S"),
    }
    with httpx.Client(timeout=60) as client:
        resp = client.post(url, params=params, json=body)
        data = resp.json()
    if data.get("errcode") != 0:
        raise Exception(f"获取考勤列值失败(userId={user_id}): {data.get('errmsg')}")

    result = data.get("result", {})
    column_vals = result.get("column_vals", [])
    flat = []
    for col_group in column_vals:
        col_info = col_group.get("column_vo", {})
        col_id = col_info.get("id")
        col_name = col_info.get("name", "")
        for val in col_group.get("column_vals", []):
            flat.append({
                "date": val.get("date", ""),
                "column_id": col_id,
                "column_name": col_name,
                "value": val.get("value", "0"),
            })
    return flat


# ========== 用户详情 ==========

def get_user_detail(user_id: str) -> dict:
    """根据 userId 获取用户详情"""
    token = _get_access_token()
    url = "https://oapi.dingtalk.com/topapi/v2/user/get"
    params = {"access_token": token}
    body = {"userid": user_id, "language": "zh_CN"}
    headers = {"Content-Type": "application/json"}
    with httpx.Client(timeout=30) as client:
        resp = client.post(url, params=params, json=body, headers=headers)
        data = resp.json()
    if data.get("errcode") != 0:
        raise Exception(f"获取用户详情失败(userId={user_id}): {data.get('errmsg')}")

    return data.get("result", {})


# ========== 同步逻辑 ==========

def sync_roster_to_db(db_session, mode: str = "full", auto_sync_depts: bool = True) -> dict:
    """
    将钉钉花名册同步到系统 Employee 表。
    mode: "full" 全量同步 / "incremental" 增量同步（基于数据更新时间戳）
    auto_sync_depts: 是否自动同步部门（默认True，简化首次使用流程）
    匹配逻辑：优先按 dingtalk_user_id 匹配，其次按手机号。
    冲突处理：本地优先，已存在的员工非空字段不会被钉钉覆盖。
    返回: {"created": 0, "updated": 0, "errors": [], "depts_synced": {...}}
    """
    from app.models.models import Employee, SysDictBase

    started_at = datetime.now()
    sync_type = f"roster_{mode}"
    stats = {"created": 0, "updated": 0, "errors": [], "depts_synced": None}

    # 0. 自动同步部门（简化首次使用流程，用户无需手动先同步部门）
    if auto_sync_depts:
        try:
            dept_stats = sync_root_depts_to_db(db_session)
            stats["depts_synced"] = dept_stats
            logger.info("员工同步前自动同步部门：新增%d，更新%d", dept_stats["created"], dept_stats["updated"])
        except Exception as e:
            logger.warning("自动同步部门失败（非致命错误）: %s", str(e))
            stats["errors"].append(f"自动同步部门失败: {str(e)}")

    # 1. 获取所有员工 userId
    try:
        user_ids = get_all_user_ids(db_session)
    except Exception as e:
        stats["errors"].append(f"获取员工列表失败: {str(e)}")
        _write_sync_log(db_session, sync_type, "failed", error_detail=stats["errors"],
                        started_at=started_at, finished_at=datetime.now())
        return stats

    if not user_ids:
        stats["errors"].append("未获取到任何员工 userId")
        _write_sync_log(db_session, sync_type, "failed", error_detail=stats["errors"],
                        started_at=started_at, finished_at=datetime.now())
        return stats

    # 2. 分批获取花名册（每批最多100人）
    batch_size = 100
    all_roster_data = []
    for i in range(0, len(user_ids), batch_size):
        batch = user_ids[i:i + batch_size]
        try:
            roster = get_roster_by_user_ids(batch)
            all_roster_data.extend(roster)
        except Exception as e:
            stats["errors"].append(f"获取花名册批次 {i // batch_size + 1} 失败: {str(e)}")

    if not all_roster_data:
        stats["errors"].append("未获取到花名册数据")
        _write_sync_log(db_session, sync_type, "failed", error_detail=stats["errors"],
                        started_at=started_at, finished_at=datetime.now())
        return stats

    # 3. 按 userId 分组花名册数据
    user_roster_map: dict[str, dict] = {}
    for item in all_roster_data:
        uid = item["userId"]
        if uid not in user_roster_map:
            user_roster_map[uid] = {}
        user_roster_map[uid][item["fieldCode"]] = item["label"] or item["value"]

    # 4. 获取字典映射（部门、岗位、状态等）
    dict_items = db_session.query(SysDictBase).all()
    dept_map_by_code = {d.code: d.id for d in dict_items if d.category == "department" and d.code}
    dept_map_by_name = {d.name: d.id for d in dict_items if d.category == "department" and d.name}
    position_map = {d.name: d.id for d in dict_items if d.category == "position"}
    status_map = {d.name: d.id for d in dict_items if d.category == "employee_status"}
    company_map = {d.name: d.id for d in dict_items if d.category == "contract_company"}

    # 构建钉钉部门树映射：dept_id → root_dept_id
    dept_tree = get_dept_tree()
    dept_id_to_root_id: dict[int, int] = {}
    for did, info in dept_tree.items():
        current = did
        root_id = did
        while current in dept_tree:
            parent_id = dept_tree[current]["parent_id"]
            if parent_id == 1 and current != 1:
                root_id = current
                break
            current = parent_id
            root_id = current
        dept_id_to_root_id[did] = root_id

    # 钉钉 dept_name → dept_id 映射（规范化为strip后的名称）
    dept_name_to_id = {info["name"].strip(): did for did, info in dept_tree.items()}
    logger.info(f"部门映射样本: {dict(list(dept_name_to_id.items())[:5])}")

    # 获取所有已有员工（按 dingtalk_user_id 索引）
    existing_employees = db_session.query(Employee).all()
    emp_by_dingtalk = {e.dingtalk_user_id: e for e in existing_employees if e.dingtalk_user_id}
    emp_by_phone = {e.phone: e for e in existing_employees if e.phone}

    for user_id, fields in user_roster_map.items():
        try:
            # ---- 提取所有字段（统一截断保护，防止超长值导致数据库写入失败） ----
            name = _safe_str(fields.get("sys00-name", ""), 50)
            phone = _safe_str(fields.get("sys00-mobile", ""), 30)
            email = _safe_str(fields.get("sys00-email", ""), 100)
            work_place = _safe_str(fields.get("sys00-workPlace", ""), 100)
            job_number = _safe_str(fields.get("sys00-jobNumber", ""), 64)
            dept_name = _safe_str(fields.get("sys00-dept", ""), 500)
            main_dept_name = _safe_str(fields.get("sys00-mainDept", dept_name), 100)
            position_name = _safe_str(fields.get("sys00-position", ""), 50)
            report_manager = _safe_str(fields.get("sys00-reportManager", ""), 50)
            remark = _safe_str(fields.get("sys00-remark", ""), 500)
            hired_date_str = fields.get("sys00-confirmJoinTime", "") or fields.get("sys00-hiredDate", "")
            # sys01 - 工作信息
            employee_type = _safe_str(fields.get("sys01-employeeType", ""), 50)
            status_name = _safe_str(fields.get("sys01-employeeStatus", "") or fields.get("sys00-staffStatus", ""), 50)
            position_level = _safe_str(fields.get("sys01-positionLevel", ""), 50)
            plan_regular_date_str = fields.get("sys01-planRegularTime", "")
            regular_date_str = fields.get("sys01-regularTime", "") or fields.get("sys00-regularDate", "")
            resign_date_str = fields.get("sys00-resignDate", "")
            # sys02 - 个人信息
            id_card = _safe_str(fields.get("sys02-certNo", "") or fields.get("sys00-idCard", ""), 18)
            gender_raw = fields.get("sys02-sexType", "") or fields.get("sys00-gender", "")
            birth_date_str = fields.get("sys02-birthTime", "")
            nation = _safe_str(fields.get("sys02-nationType", ""), 50)
            marital_status = _safe_str(fields.get("sys02-marriage", ""), 20)
            children_status = _safe_str(fields.get("1e8e7d6d-6f56-49fc-a7aa-215f3bb5361c", ""), 50)
            political_status = _safe_str(fields.get("sys02-politicalStatus", ""), 50)
            native_place = _safe_str(fields.get("e6535432-0334-4090-bc86-aeec046c45b7", ""), 100)
            residence_type = _safe_str(fields.get("sys02-residenceType", ""), 50)
            census_address = _safe_str(fields.get("sys02-certAddress", ""), 200)
            home_address = _safe_str(fields.get("sys02-address", ""), 200)
            first_work_date_str = fields.get("sys02-joinWorkingTime", "")
            # sys03 - 学历
            education = _safe_str(fields.get("sys03-highestEdu", ""), 50)
            graduate_school = _safe_str(fields.get("sys03-graduateSchool", ""), 100)
            graduate_date_str = fields.get("sys03-graduationTime", "")
            major = _safe_str(fields.get("sys03-major", ""), 100)
            # sys04 - 银行卡
            bank_card = _safe_str(fields.get("sys04-bankAccountNo", ""), 30)
            bank_branch = _safe_str(fields.get("sys04-accountBank", ""), 100)
            bank_branch_detail = _safe_str(fields.get("c973eb37-4d74-47c3-b84a-c685e73b1e30", ""), 100)
            # sys05 - 合同
            contract_company_name = _safe_str(fields.get("sys05-contractCompanyName", ""), 100)
            contract_type = _safe_str(fields.get("sys05-contractType", ""), 50)
            contract_start_date_str = fields.get("sys05-nowContractStartTime", "")
            contract_end_date_str = fields.get("sys05-nowContractEndTime", "")
            # sys06 - 紧急联系人
            emergency_contact_name = _safe_str(fields.get("sys06-urgentContactsName", ""), 100)
            emergency_contact_relation = _safe_str(fields.get("sys06-urgentContactsRelation", ""), 100)
            emergency_contact_phone = _safe_str(fields.get("sys06-urgentContactsPhone", ""), 50)
            # 自定义字段
            job_level = _safe_str(fields.get("81922c26-7b0a-40fe-b87c-7373b85a8941", ""), 50)
            recruitment_channel = _safe_str(fields.get("9e199205-1337-44e2-94e8-624a92adca9f", ""), 100)
            hobby = _safe_str(fields.get("90300477-bcc9-4c70-a5ee-dbc256df20c5", ""), 200)
            cert1 = _safe_str(fields.get("89474793-54fe-4cc8-bbb0-b21a834949dc", ""), 100)
            cert2 = _safe_str(fields.get("cba563d1-96cd-4739-89e3-18f912bb707e", ""), 100)
            insurance_start_date_str = fields.get("6d119e8d-0cde-4d73-975d-85d15174d0d0", "")
            insurance_location = _safe_str(fields.get("6ea63544-3d03-47aa-929d-8995277029c4", ""), 100)
            commercial_insurance_type = _safe_str(fields.get("fd1cc8aa-8af7-4574-bba4-1986d5acff03", ""), 50)

            # ---- 部门层级解析 ----
            # 部门路径格式: "总经室/物资供应部/工艺组" 或 "物资供应部,总经室"（多部门）
            dept_path = dept_name
            dept_levels = dept_name.split("/") if "/" in dept_name else dept_name.split(",")
            dept_level1 = dept_levels[0].strip() if len(dept_levels) >= 1 else ""
            dept_level2 = dept_levels[1].strip() if len(dept_levels) >= 2 else ""
            dept_level3 = dept_levels[2].strip() if len(dept_levels) >= 3 else ""
            dept_level4 = dept_levels[3].strip() if len(dept_levels) >= 4 else ""
            dept_level5 = dept_levels[4].strip() if len(dept_levels) >= 5 else ""

            # 子部门 → 根部门转换（取第一个部门名）
            first_dept = dept_name.split(",")[0].strip() if dept_name else ""
            first_dept = first_dept.split("/")[0].strip() if "/" in first_dept else first_dept
            sub_dept_id = dept_name_to_id.get(first_dept)
            root_dept_id = dept_id_to_root_id.get(sub_dept_id) if sub_dept_id else None
            
            # 查找部门ID：优先用钉钉部门名匹配数据库字典
            dept_id = 1  # 默认值
            if root_dept_id:
                # 用钉钉根部门名称去数据库字典中查找
                root_dept_name = dept_tree.get(root_dept_id, {}).get("name", "")
                if root_dept_name:
                    dept_id = dept_map_by_name.get(root_dept_name.strip())
                # 降级：用数字code匹配
                if not dept_id or dept_id == 1:
                    dept_id = dept_map_by_code.get(str(root_dept_id), 1)
            # 如果根部门没匹配到，尝试直接用子部门名匹配
            if (not dept_id or dept_id == 1) and first_dept:
                dept_id = dept_map_by_name.get(first_dept, 1)
            # 再降级：用 dept_level1 匹配
            if (not dept_id or dept_id == 1) and dept_level1 and dept_level1 != first_dept:
                dept_id = dept_map_by_name.get(dept_level1.strip(), 1)

            # 合同公司映射（自动创建不存在的公司）
            contract_company_id = _get_or_create_contract_company(db_session, contract_company_name, company_map)

            # 匹配已有员工
            emp = None
            if user_id in emp_by_dingtalk:
                emp = emp_by_dingtalk[user_id]
            elif phone and phone in emp_by_phone:
                emp = emp_by_phone[phone]

            if emp:
                # ---- 更新已有员工（本地优先：非空字段不被覆盖） ----
                emp.dingtalk_user_id = user_id
                if not emp.name and name:
                    emp.name = name
                if phone and not emp.phone:
                    emp.phone = phone
                if email and not emp.email:
                    emp.email = email
                if work_place and not emp.work_place:
                    emp.work_place = work_place
                if gender_raw:
                    emp.gender = _parse_gender(gender_raw)
                if id_card and not emp.id_card:
                    emp.id_card = id_card
                # 日期字段：钉钉返回了可解析的日期就覆盖（钉钉是数据源头）
                parsed_entry = _parse_date(hired_date_str)
                if parsed_entry:
                    emp.entry_date = parsed_entry
                parsed_regular = _parse_date(regular_date_str) or _parse_date(plan_regular_date_str)
                if parsed_regular:
                    emp.regular_date = parsed_regular
                parsed_resign = _parse_date(resign_date_str)
                if parsed_resign:
                    emp.resign_date = parsed_resign
                parsed_birth = _parse_date(birth_date_str)
                if parsed_birth:
                    emp.birth_date = parsed_birth
                if contract_company_name:
                    emp.contract_company_id = _get_or_create_contract_company(db_session, contract_company_name, company_map)
                if dept_id != 1:
                    emp.department_id = dept_id
                if position_name:
                    emp.position_id = _get_or_create_dict_item(db_session, position_name, "position", position_map)
                if status_name:
                    emp.status_id = _get_or_create_dict_item(db_session, status_name, "employee_status", status_map)
                # 更新新字段（钉钉每次覆盖，因为这些字段用户不会手动修改）
                if position_level:
                    emp.position_level = position_level
                if employee_type:
                    emp.employee_type = employee_type
                if job_level:
                    emp.job_level = job_level
                if report_manager:
                    emp.report_manager = report_manager
                if nation:
                    emp.nation = nation
                if marital_status:
                    emp.marital_status = marital_status
                if children_status:
                    emp.children_status = children_status
                if political_status:
                    emp.political_status = political_status
                if native_place:
                    emp.native_place = native_place
                if residence_type:
                    emp.residence_type = residence_type
                if census_address:
                    emp.census_address = census_address
                if first_work_date_str:
                    parsed_fwd = _parse_date(first_work_date_str)
                    if parsed_fwd:
                        emp.first_work_date = parsed_fwd
                if education:
                    emp.education = education
                if graduate_school:
                    emp.graduate_school = graduate_school
                if graduate_date_str:
                    parsed_gd = _parse_date(graduate_date_str)
                    if parsed_gd:
                        emp.graduate_date = parsed_gd
                if major:
                    emp.major = major
                if cert1:
                    emp.cert1 = cert1
                if cert2:
                    emp.cert2 = cert2
                if emergency_contact_name:
                    emp.emergency_contact_name = emergency_contact_name
                if emergency_contact_relation:
                    emp.emergency_contact_relation = emergency_contact_relation
                if emergency_contact_phone:
                    emp.emergency_contact_phone = emergency_contact_phone
                if contract_start_date_str:
                    parsed_csd = _parse_date(contract_start_date_str)
                    if parsed_csd:
                        emp.contract_start_date = parsed_csd
                if contract_end_date_str:
                    parsed_ced = _parse_date(contract_end_date_str)
                    if parsed_ced:
                        emp.contract_end_date = parsed_ced
                if contract_type:
                    emp.contract_type = contract_type
                if insurance_start_date_str:
                    parsed_isd = _parse_date(insurance_start_date_str)
                    if parsed_isd:
                        emp.insurance_start_date = parsed_isd
                if insurance_location:
                    emp.insurance_location = insurance_location
                if recruitment_channel:
                    emp.recruitment_channel = recruitment_channel
                if hobby:
                    emp.hobby = hobby
                if commercial_insurance_type:
                    emp.commercial_insurance_type = commercial_insurance_type
                if remark:
                    emp.remark = remark
                if bank_card:
                    emp.bank_card = bank_card
                if bank_branch:
                    emp.bank_branch = bank_branch
                if bank_branch_detail:
                    emp.bank_branch_detail = bank_branch_detail
                if home_address:
                    emp.home_address = home_address
                if dept_path:
                    emp.dept_path = dept_path
                if dept_level1:
                    emp.dept_level1 = dept_level1
                if dept_level2:
                    emp.dept_level2 = dept_level2
                if dept_level3:
                    emp.dept_level3 = dept_level3
                if dept_level4:
                    emp.dept_level4 = dept_level4
                if dept_level5:
                    emp.dept_level5 = dept_level5
                stats["updated"] += 1
            else:
                # ---- 新建员工 ----
                if not name:
                    continue
                new_emp = Employee(
                    employee_no=user_id,
                    dingtalk_user_id=user_id,
                    name=name,
                    gender=_parse_gender(gender_raw),
                    id_card=id_card or None,
                    phone=phone or None,
                    email=email or None,
                    work_place=work_place or None,
                    contract_company_id=contract_company_id,
                    department_id=dept_id,
                    position_id=_get_or_create_dict_item(db_session, position_name, "position", position_map),
                    status_id=_get_or_create_dict_item(db_session, status_name, "employee_status", status_map),
                    position_level=position_level or None,
                    employee_type=employee_type or None,
                    job_level=job_level or None,
                    report_manager=report_manager or None,
                    entry_date=_parse_date(hired_date_str) or date.today(),  # 如果钉钉无日期则用今天（新员工不应出现此情况）
                    regular_date=_parse_date(regular_date_str) or _parse_date(plan_regular_date_str),
                    resign_date=_parse_date(resign_date_str),
                    birth_date=_parse_date(birth_date_str),
                    nation=nation or None,
                    marital_status=marital_status or None,
                    children_status=children_status or None,
                    political_status=political_status or None,
                    native_place=native_place or None,
                    residence_type=residence_type or None,
                    census_address=census_address or None,
                    first_work_date=_parse_date(first_work_date_str),
                    education=education or None,
                    graduate_school=graduate_school or None,
                    graduate_date=_parse_date(graduate_date_str),
                    major=major or None,
                    cert1=cert1 or None,
                    cert2=cert2 or None,
                    emergency_contact_name=emergency_contact_name or None,
                    emergency_contact_relation=emergency_contact_relation or None,
                    emergency_contact_phone=emergency_contact_phone or None,
                    contract_start_date=_parse_date(contract_start_date_str),
                    contract_end_date=_parse_date(contract_end_date_str),
                    contract_type=contract_type or None,
                    insurance_start_date=_parse_date(insurance_start_date_str),
                    insurance_location=insurance_location or None,
                    recruitment_channel=recruitment_channel or None,
                    hobby=hobby or None,
                    commercial_insurance_type=commercial_insurance_type or None,
                    remark=remark or None,
                    bank_card=bank_card or None,
                    bank_branch=bank_branch or None,
                    bank_branch_detail=bank_branch_detail or None,
                    home_address=home_address or None,
                    dept_path=dept_path or None,
                    dept_level1=dept_level1 or None,
                    dept_level2=dept_level2 or None,
                    dept_level3=dept_level3 or None,
                    dept_level4=dept_level4 or None,
                    dept_level5=dept_level5 or None,
                )
                db_session.add(new_emp)
                stats["created"] += 1

        except Exception as e:
            stats["errors"].append(f"同步员工 {user_id} 失败: {str(e)}")

    db_session.commit()

    # 5. 数据校验：比对同步前后数量
    after_count = db_session.query(Employee).filter(Employee.dingtalk_user_id.isnot(None)).count()
    total = stats["created"] + stats["updated"]
    status = "success" if len(stats["errors"]) == 0 else "partial"

    _write_sync_log(
        db_session, sync_type, status,
        total_count=total, success_count=total - len(stats["errors"]),
        failed_count=len(stats["errors"]),
        created_count=stats["created"], updated_count=stats["updated"],
        error_detail=stats["errors"],
        started_at=started_at, finished_at=datetime.now(),
    )

    logger.info("花名册同步(%s)完成：新增%d 更新%d 错误%d 系统已有钉钉员工%d",
                mode, stats["created"], stats["updated"], len(stats["errors"]), after_count)
    return stats


def sync_attendance_to_db(db_session, period: str) -> dict:
    """
    将钉钉考勤数据同步到系统 AttendanceRecord 表（月度汇总）。
    period: 格式 YYYYMM，如 "202406"
    返回: {"synced": 0, "errors": []}
    """
    from app.models.models import Employee, AttendanceRecord

    started_at = datetime.now()
    stats = {"synced": 0, "errors": []}

    # 1. 获取考勤列定义，建立列名→列ID映射
    try:
        columns = get_attendance_columns()
    except Exception as e:
        stats["errors"].append(f"获取考勤列定义失败: {str(e)}")
        _write_sync_log(db_session, "attendance_monthly", "failed", period=period,
                        error_detail=stats["errors"], started_at=started_at, finished_at=datetime.now())
        return stats

    # 建立列名→列ID映射
    col_name_to_id = {}
    for col in columns:
        col_name_to_id[col["name"]] = col["id"]

    # 获取所有可用的列ID（包括文本列如考勤结果、班次、出勤班次）
    target_col_ids = [cid for cid in col_name_to_id.values() if cid is not None]

    # 钉钉 getcolumnval 接口单次最多支持 20 列，超限需分批获取
    COL_BATCH_SIZE = 20

    if not target_col_ids:
        stats["errors"].append("未找到有效的考勤列，请检查钉钉考勤报表列定义")
        _write_sync_log(db_session, "attendance_monthly", "failed", period=period,
                        error_detail=stats["errors"], started_at=started_at, finished_at=datetime.now())
        return stats

    # 2. 计算月份日期范围
    year = int(period[:4])
    month = int(period[4:6])
    from_date = date(year, month, 1)
    if month == 12:
        to_date = date(year, month, 31)
    else:
        to_date = date(year, month + 1, 1) - timedelta(days=1)

    # 3. 获取需要同步考勤的员工 userId（通过部门）
    try:
        dept_user_ids = get_all_user_ids(db_session)
    except Exception as e:
        stats["errors"].append(f"获取部门员工失败: {str(e)}")
        _write_sync_log(db_session, "attendance_monthly", "failed", period=period,
                        error_detail=stats["errors"], started_at=started_at, finished_at=datetime.now())
        return stats

    if not dept_user_ids:
        stats["errors"].append("未获取到任何需要同步考勤的员工，请检查部门配置")
        _write_sync_log(db_session, "attendance_monthly", "failed", period=period,
                        error_detail=stats["errors"], started_at=started_at, finished_at=datetime.now())
        return stats

    # 查询部门员工中已关联钉钉的员工
    employees = db_session.query(Employee).filter(
        Employee.dingtalk_user_id.in_(dept_user_ids)
    ).all()

    logger.info(f"部门员工({len(dept_user_ids)}人)，数据库中匹配到 {len(employees)} 人")
    if not employees:
        stats["errors"].append("没有已关联钉钉的员工，请先同步花名册")
        _write_sync_log(db_session, "attendance_monthly", "failed", period=period,
                        error_detail=stats["errors"], started_at=started_at, finished_at=datetime.now())
        return stats

    # 4. 逐员工获取考勤数据并汇总
    for emp in employees:
        try:
            # 分批获取考勤列值（钉钉单次最多20列）
            all_vals = []
            for i in range(0, len(target_col_ids), COL_BATCH_SIZE):
                batch_ids = target_col_ids[i:i + COL_BATCH_SIZE]
                batch_vals = get_attendance_column_values(
                    emp.dingtalk_user_id, batch_ids, from_date, to_date
                )
                all_vals.extend(batch_vals)
            summary = _aggregate_attendance(all_vals, col_name_to_id)
            if not summary or not summary.get("numerical"):
                continue

            num = summary["numerical"]
            leave = summary.get("leave_days", {})
            txt = summary.get("text_fields", {})

            total = num.get("total_work_days", 0)
            # 从"考勤结果"文本解析出的小时级请假天数（钉钉按天计出勤时不会自动扣减）
            text_leave_total = sum(leave.values())
            actual = num.get("actual_work_days", 0) - text_leave_total
            actual = max(actual, 0)  # 防止出现负数
            rate = round(actual / total, 4) if total > 0 else 0

            # 请假天数合并：数值列优先，文本解析兜底（两者为同源数据，不可叠加）
            personal_leave = round(num.get("personal_leave_days", 0) or leave.get("personal_leave_days", 0), 2)
            full_pay_sick = round(num.get("full_pay_sick_days", 0) or leave.get("full_pay_sick_days", 0), 2)
            reduced_pay_sick = round(num.get("reduced_pay_sick_days", 0) or leave.get("reduced_pay_sick_days", 0), 2)
            statutory_sick = round(num.get("statutory_sick_days", 0) or leave.get("statutory_sick_days", 0), 2)
            sick_total = round(full_pay_sick + reduced_pay_sick + statutory_sick + leave.get("sick_leave_days", 0), 2)
            annual_leave = round(num.get("annual_leave_days", 0) or leave.get("annual_leave_days", 0), 2)
            compensatory = round(num.get("compensatory_leave_days", 0) or leave.get("compensatory_leave_days", 0), 2)
            prenatal = round(num.get("prenatal_checkup_days", 0) or leave.get("prenatal_checkup_days", 0), 2)
            maternity = round(num.get("maternity_leave_days", 0) or leave.get("maternity_leave_days", 0), 2)
            paternity = round(num.get("paternity_leave_days", 0) or leave.get("paternity_leave_days", 0), 2)
            marriage = round(num.get("marriage_leave_days", 0) or leave.get("marriage_leave_days", 0), 2)
            funeral = round(num.get("funeral_leave_days", 0) or leave.get("funeral_leave_days", 0), 2)
            engineering = round(num.get("engineering_compensatory_days", 0) or leave.get("engineering_compensatory_days", 0), 2)
            other_leave = round(personal_leave + sick_total + annual_leave + compensatory +
                               prenatal + maternity + paternity + marriage + funeral + engineering, 2)

            # 缺卡总数 = 上班 + 下班
            missed_total = int(num.get("missed_clock_in_count", 0)) + int(num.get("missed_clock_out_count", 0))

            # === 加工字段计算 ===
            # 计薪日期
            first_day = date(int(period[:4]), int(period[4:6]), 1)
            last_day = date(int(period[:4]), int(period[4:6]), calendar.monthrange(int(period[:4]), int(period[4:6]))[1])

            # 迟到转事假：迟到次数>3次时，累计迟到时长(分钟)换算为天数(每天7小时)
            late_count_val = int(num.get("late_count", 0))
            late_duration_val = int(num.get("late_duration", 0))
            late_to_leave = 0.0
            if late_count_val > 3 and late_duration_val > 0:
                late_to_leave = round(late_duration_val / 60 / 7, 2)

            # 扣薪请假合计（全薪病假、年假、调休为带薪假，不计入扣减）
            leave_total = round(
                late_to_leave + personal_leave + reduced_pay_sick +
                statutory_sick + prenatal +
                maternity + paternity + marriage + funeral + engineering, 2
            )

            # 应计薪天数 = 从年度工作日历计算（而非直接使用钉钉的应出勤天数）
            # total_work_days 保留钉钉原始值（当月总计薪天数）用于参考
            adjusted = work_cal.get_month_salary_days(db_session, period)

            # 计薪天数 = 应计薪 - 请假合计
            actual_salary = max(round(adjusted - leave_total, 2), 0)

            # 出勤率 = 计薪天数 / 应计薪天数
            att_rate = round(actual_salary / adjusted, 4) if adjusted > 0 else 0

            record_data = dict(
                period=period, employee_id=emp.id,
                total_work_days=total, actual_work_days=actual_salary, attendance_rate=att_rate,
                # 计薪加工字段
                salary_start_date=first_day, salary_end_date=last_day,
                adjusted_salary_days=adjusted,
                actual_salary_days=actual_salary,
                late_to_personal_leave_days=late_to_leave,
                leave_total_days=leave_total,
                rest_days=num.get("rest_days", 0),
                work_hours=num.get("work_hours", 0),
                resupplement_count=int(num.get("resupplement_count", 0)),
                late_count=int(num.get("late_count", 0)),
                late_duration=int(num.get("late_duration", 0)),
                severe_late_count=int(num.get("severe_late_count", 0)),
                severe_late_duration=int(num.get("severe_late_duration", 0)),
                absenteeism_late_count=int(num.get("absenteeism_late_count", 0)),
                absenteeism_late_days=num.get("absenteeism_late_days", 0),
                late_over_10min_count=int(num.get("late_over_10min_count", 0)),
                late_over_30min_count=int(num.get("late_over_30min_count", 0)),
                early_count=int(num.get("early_count", 0)),
                early_duration=int(num.get("early_duration", 0)),
                missed_clock_in_count=int(num.get("missed_clock_in_count", 0)),
                missed_clock_out_count=int(num.get("missed_clock_out_count", 0)),
                missed_punch_count=missed_total,
                half_day_missed_punch=int(num.get("half_day_missed_punch", 0)),
                absenteeism_days=num.get("absenteeism_days", 0),
                business_travel_duration=num.get("business_travel_duration", 0),
                out_duration=num.get("out_duration", 0),
                overtime_approval_count=num.get("overtime_approval_count", 0),
                workday_overtime=num.get("workday_overtime", 0),
                weekend_overtime=num.get("weekend_overtime", 0),
                holiday_overtime=num.get("holiday_overtime", 0),
                total_overtime=num.get("total_overtime", 0),
                workday_overtime_pay=num.get("workday_overtime_pay", 0),
                weekend_overtime_pay=num.get("weekend_overtime_pay", 0),
                holiday_overtime_pay=num.get("holiday_overtime_pay", 0),
                workday_overtime_leave=num.get("workday_overtime_leave", 0),
                weekend_overtime_leave=num.get("weekend_overtime_leave", 0),
                holiday_overtime_leave=num.get("holiday_overtime_leave", 0),
                clock_out_after_7pm_count=int(num.get("clock_out_after_7pm_count", 0)),
                clock_out_after_8pm_count=int(num.get("clock_out_after_8pm_count", 0)),
                clock_out_after_9pm_count=int(num.get("clock_out_after_9pm_count", 0)),
                punch_count=int(num.get("punch_count", 0)),
                shift_type=txt.get("出勤班次"),
                shift_name=txt.get("班次"),
                personal_leave_days=personal_leave,
                full_pay_sick_days=full_pay_sick,
                reduced_pay_sick_days=reduced_pay_sick,
                statutory_sick_days=statutory_sick,
                sick_leave_days=sick_total,
                annual_leave_days=annual_leave,
                compensatory_leave_days=compensatory,
                prenatal_checkup_days=prenatal,
                maternity_leave_days=maternity,
                paternity_leave_days=paternity,
                marriage_leave_days=marriage,
                funeral_leave_days=funeral,
                engineering_compensatory_days=engineering,
                other_leave_days=other_leave,
            )

            # upsert（注意：跳过已锁定的字段和整行锁定的记录）
            # 先查询是否有重复记录，清理旧记录只保留最新的
            existing_records = db_session.query(AttendanceRecord).filter(
                AttendanceRecord.period == period,
                AttendanceRecord.employee_id == emp.id,
            ).order_by(AttendanceRecord.id.desc()).all()

            existing = existing_records[0] if existing_records else None
            
            # 如果有重复记录，删除旧的（保留最新的一条）
            if len(existing_records) > 1:
                for old_rec in existing_records[1:]:
                    db_session.delete(old_rec)

            if existing:
                row_locked = existing.is_row_locked or False
                locked_fields = existing.locked_fields or {}
                for k, v in record_data.items():
                    if k not in ("period", "employee_id"):
                        if row_locked:
                            continue
                        if locked_fields.get(k):
                            continue
                        setattr(existing, k, v)
            else:
                db_session.add(AttendanceRecord(**record_data))

            stats["synced"] += 1

        except Exception as e:
            stats["errors"].append(f"同步 {emp.name}({emp.dingtalk_user_id}) 考勤失败: {str(e)}")

    db_session.commit()

    # 5. 数据校验
    synced_count = db_session.query(AttendanceRecord).filter(
        AttendanceRecord.period == period
    ).count()
    status = "success" if len(stats["errors"]) == 0 else "partial"

    _write_sync_log(
        db_session, "attendance_monthly", status, period=period,
        total_count=len(employees), success_count=stats["synced"],
        failed_count=len(stats["errors"]),
        error_detail=stats["errors"],
        started_at=started_at, finished_at=datetime.now(),
    )

    logger.info("考勤同步(%s)完成：应同步%d人 实际成功%d 错误%d 数据库记录%d",
                period, len(employees), stats["synced"], len(stats["errors"]), synced_count)
    return stats


def _aggregate_attendance(vals: list[dict], col_name_to_id: dict) -> dict:
    """
    将每天的考勤列值汇总为月度值。
    数值列：累加求和（月度汇总列API只返回一次，直接使用即可）
    文本列（考勤结果）：收集后解析请假类型（跨天假期自动去重）
    班次列：记录第一个非空值
    返回: {"numerical": {field: value}, "text_fields": {field: text}, "leave_days": {field: days}}
    """
    id_to_name = {v: k for k, v in col_name_to_id.items()}
    numerical = {}
    # 记录每个字段对应的原始列名，用于判断单位（小时/天）
    field_source_col = {}
    text_fields = {}
    leave_texts = []

    # 需要特殊处理的文本列
    text_col_names = {"考勤结果", "班次", "出勤班次"}

    for item in vals:
        col_name = item.get("column_name") or id_to_name.get(item.get("column_id"), "")
        raw_value = str(item.get("value", "")).strip() if item.get("value") else ""

        # 文本列特殊处理
        if col_name in text_col_names:
            if col_name == "考勤结果" and raw_value not in ("", "正常", "休息", "旷工"):
                leave_texts.append(raw_value)
            elif col_name in ("班次", "出勤班次"):
                if raw_value and col_name not in text_fields:
                    text_fields[col_name] = raw_value
            continue

        # 数值列：按ATTENDANCE_COLUMN_MAP映射后累加
        field = ATTENDANCE_COLUMN_MAP.get(col_name)
        if not field:
            continue
        try:
            val = float(item.get("value", 0))
        except (ValueError, TypeError):
            val = 0
        if val != 0:
            numerical[field] = numerical.get(field, 0) + val
            # 记录第一个非零值的来源列名（用于判断单位）
            if field not in field_source_col:
                field_source_col[field] = col_name

    # 单位转换：带"(小时)"后缀的列是小时单位，除以7转为天；其他默认是天单位
    for fld in list(numerical.keys()):
        source_col = field_source_col.get(fld, "")
        # 小时单位：事假(小时)、全薪病假(小时)、减薪病假(小时)、调休(小时) 等
        if "(小时)" in source_col or "时长" in source_col:
            # 注意：加班时长（workday_overtime等）是小时单位但不需要转天，保持原值
            # 只有请假类型的小时列需要转天
            leave_fields = {"personal_leave_days", "full_pay_sick_days", "reduced_pay_sick_days", 
                           "compensatory_leave_days", "sick_leave_days"}
            if fld in leave_fields:
                numerical[fld] = round(numerical[fld] / 7.0, 2)

    # 解析请假文本 → 请假天数（跨天假期自动去重）
    leave_days = {}
    # 用于去重：(field, start_date, end_date, hours) 作为唯一键
    seen_leaves = set()
    for text in leave_texts:
        parsed = parse_leave_from_result(text)
        for p in parsed:
            # 去重：同一段跨天假期在多天的考勤结果中重复出现，只算一次
            leave_key = (p["field"], p["start"], p["end"], p["hours"])
            if leave_key in seen_leaves:
                continue
            seen_leaves.add(leave_key)
            days = p["hours"] / 7.0  # 7小时/天
            leave_days[p["field"]] = round(leave_days.get(p["field"], 0) + days, 2)

    return {
        "numerical": numerical,
        "text_fields": text_fields,
        "leave_days": leave_days,
    }


def get_raw_attendance_by_employee(
    db_session, period: str
) -> dict:
    """
    获取钉钉原始考勤数据（所有列，不做映射筛选）。
    返回: {
        "columns": [{"id": 123, "name": "应出勤天数", "type": 1}, ...],
        "employees": [
            {
                "employee_no": "E001",
                "employee_name": "张三",
                "dingtalk_user_id": "...",
                "values": {"应出勤天数": 22.0, "出勤天数": 25.0, ...}
            },
            ...
        ]
    }
    """
    from app.models.models import Employee

    # 1. 获取所有考勤列定义（排除id为null的列，这些是计算/派生列，钉钉API不接受）
    columns = get_attendance_columns()
    valid_columns = [c for c in columns if c["id"] is not None]
    # 去重（钉钉返回的列中可能存在重复id）
    seen_ids = set()
    unique_columns = []
    for c in valid_columns:
        if c["id"] not in seen_ids:
            seen_ids.add(c["id"])
            unique_columns.append(c)
    all_col_ids = [c["id"] for c in unique_columns]
    col_name_map = {c["id"]: c["name"] for c in unique_columns}

    # 2. 计算月份日期范围
    year = int(period[:4])
    month = int(period[4:6])
    from_date = date(year, month, 1)
    if month == 12:
        to_date = date(year, month, 31)
    else:
        to_date = date(year, month + 1, 1) - timedelta(days=1)

    # 3. 从钉钉获取所有用户ID（遍历所有部门，不受数据库配置限制）
    all_dingtalk_user_ids = get_all_dingtalk_user_ids_from_all_depts()
    # 同时获取本地员工表中已关联的钉钉ID→员工信息映射
    local_emp_map = {}
    for emp in db_session.query(Employee).filter(Employee.dingtalk_user_id.isnot(None)).all():
        local_emp_map[emp.dingtalk_user_id] = emp

    emp_data = []

    # 4. 分批获取考勤数据（钉钉API可能限制每次查询的列数）
    batch_size = 20

    for user_id in all_dingtalk_user_ids:
        emp = local_emp_map.get(user_id)
        emp_name = emp.name if emp else user_id
        emp_no = emp.employee_no if emp else ""
        try:
            monthly = {}
            # 分批查询，避免单次请求列数过多被钉钉API拒绝
            for i in range(0, len(all_col_ids), batch_size):
                batch_ids = all_col_ids[i:i + batch_size]
                vals = get_attendance_column_values(
                    user_id, batch_ids, from_date, to_date
                )
                # 按列名聚合月度值
                for item in vals:
                    col_name = item.get("column_name") or col_name_map.get(item.get("column_id"), "")
                    if not col_name:
                        continue
                    try:
                        val = float(item.get("value", 0))
                    except (ValueError, TypeError):
                        val = 0
                    monthly[col_name] = monthly.get(col_name, 0) + val

            emp_data.append({
                "employee_no": emp_no,
                "employee_name": emp_name,
                "dingtalk_user_id": user_id,
                "values": monthly,
            })
        except Exception as e:
            logger.warning("获取 %s(%s) 原始考勤失败: %s", emp_name, user_id, str(e))
            emp_data.append({
                "employee_no": emp_no,
                "employee_name": emp_name,
                "dingtalk_user_id": user_id,
                "values": {},
                "error": str(e),
            })

    return {
        "columns": columns,
        "employees": emp_data,
    }


def _parse_gender(gender_raw: str) -> str:
    """解析钉钉性别字段"""
    if not gender_raw:
        return "未知"
    if "男" in gender_raw:
        return "男"
    if "女" in gender_raw:
        return "女"
    return "未知"


def _get_or_create_contract_company(db_session, company_name: str, company_map: dict) -> int:
    """获取合同公司ID，如果不存在则自动创建。
    优先从 company_map 缓存中查找，未命中则查询数据库（按名称去重）。"""
    if not company_name:
        return 1
    key = company_name.strip()
    if key in company_map:
        return company_map[key]
    # 检查数据库是否有同名记录（避免不同 code 造成重复）
    existing = db_session.query(SysDictBase).filter(
        SysDictBase.category == "contract_company",
        SysDictBase.name == key,
    ).first()
    if existing:
        company_map[key] = existing.id
        return existing.id
    # 自动创建合同公司
    new_company = SysDictBase(
        category="contract_company",
        code=f"dingtalk_{key}",
        name=key,
    )
    db_session.add(new_company)
    db_session.flush()
    company_map[key] = new_company.id
    return new_company.id


def _get_or_create_dict_item(db_session, name: str, category: str, name_map: dict) -> int:
    """获取字典项ID，如果不存在则自动创建。name为空时创建"未设置"条目。
    优先从 name_map 缓存中查找，未命中则查询数据库（按名称去重）。"""
    if not name:
        name = "未设置"
    key = name.strip()
    if key in name_map:
        return name_map[key]
    # 检查数据库是否有同名记录（避免不同 code 造成重复）
    existing = db_session.query(SysDictBase).filter(
        SysDictBase.category == category,
        SysDictBase.name == key,
    ).first()
    if existing:
        name_map[key] = existing.id
        return existing.id
    # 自动创建字典项
    new_item = SysDictBase(
        category=category,
        code=f"dingtalk_{key}",
        name=key,
    )
    db_session.add(new_item)
    db_session.flush()
    name_map[key] = new_item.id
    logger.info("自动创建字典项: category=%s name=%s id=%s", category, key, new_item.id)
    return new_item.id


def _parse_date(date_str: str) -> Optional[date]:
    """解析日期字符串"""
    if not date_str:
        return None
    try:
        # 钉钉日期格式可能是 "2024-06-15" 或时间戳
        if "T" in date_str:
            date_str = date_str.split("T")[0]
        if date_str and len(date_str) >= 10:
            return datetime.strptime(date_str[:10], "%Y-%m-%d").date()
    except ValueError:
        pass
    try:
        ts = int(date_str)
        return datetime.fromtimestamp(ts / 1000).date()
    except (ValueError, TypeError):
        pass
    return None


def cleanup_old_daily_records(db_session, keep_days: int = 60) -> int:
    """清理超过指定天数的每日考勤记录，返回删除条数"""
    from app.models.models import AttendanceDaily
    cutoff = date.today() - timedelta(days=keep_days)
    count = db_session.query(AttendanceDaily).filter(
        AttendanceDaily.record_date < cutoff
    ).delete()
    db_session.commit()
    logger.info("清理了 %d 条超过 %d 天的每日考勤记录（截止 %s）", count, keep_days, cutoff)
    return count


def get_sync_logs(db_session, sync_type: str = None, limit: int = 20) -> list:
    """查询同步日志，返回最近N条"""
    from app.models.models import DingtalkSyncLog
    q = db_session.query(DingtalkSyncLog).order_by(DingtalkSyncLog.started_at.desc())
    if sync_type:
        q = q.filter(DingtalkSyncLog.sync_type == sync_type)
    return q.limit(limit).all()


# ========== 审批相关（旧版API，无需额外权限） ==========

def get_process_template_list() -> list[dict]:
    """获取用户可见的审批模板列表（旧版API）"""
    token = _get_access_token()
    url = "https://oapi.dingtalk.com/topapi/process/listbyuserid"
    params = {"access_token": token}
    body = {
        "offset": 0,
        "size": 100,
    }
    with httpx.Client(timeout=30) as client:
        resp = client.post(url, params=params, json=body)
        data = resp.json()
    if data.get("errcode") != 0:
        raise Exception(f"获取审批模板列表失败: {data.get('errmsg')}")
    return data.get("result", {}).get("process_list", [])


def get_process_code_by_name(template_name: str) -> str:
    """根据审批模板名称获取processCode（旧版API，遍历模板列表）"""
    templates = get_process_template_list()
    for tpl in templates:
        name = tpl.get("name", "")
        if template_name in name or name in template_name:
            return tpl.get("process_code", "")
    # 如果没找到，打印所有可用模板名称方便调试
    all_names = [t.get("name", "") for t in templates]
    raise Exception(f"未找到名为「{template_name}」的审批模板，可用模板: {all_names}")


def get_approval_instance_ids(process_code: str, start_time: int, end_time: int,
                              statuses: list = None, user_ids: list = None) -> list[str]:
    """
    获取审批实例ID列表（旧版API）
    start_time/end_time: Unix时间戳，单位毫秒
    statuses: ["RUNNING", "TERMINATED", "COMPLETED"]
    """
    token = _get_access_token()
    url = "https://oapi.dingtalk.com/topapi/processinstance/listids"
    params = {"access_token": token}
    all_instance_ids = []
    cursor = 0
    size = 20

    while True:
        body = {
            "process_code": process_code,
            "start_time": start_time,
            "end_time": end_time,
            "cursor": cursor,
            "size": size,
        }
        if user_ids:
            body["userid_list"] = ",".join(user_ids)

        with httpx.Client(timeout=30) as client:
            resp = client.post(url, params=params, json=body)
            data = resp.json()
        if data.get("errcode") != 0:
            raise Exception(f"获取审批实例ID列表失败: {data.get('errmsg')}")
        result = data.get("result", {})
        instance_ids = result.get("list", [])
        all_instance_ids.extend(instance_ids)
        next_cursor = result.get("next_cursor")
        if not next_cursor or len(instance_ids) < size:
            break
        cursor = next_cursor

    return all_instance_ids


def get_approval_instance_detail(process_instance_id: str) -> dict:
    """获取单个审批实例详情（旧版API）"""
    token = _get_access_token()
    url = "https://oapi.dingtalk.com/topapi/processinstance/get"
    params = {"access_token": token}
    body = {"process_instance_id": process_instance_id}
    with httpx.Client(timeout=30) as client:
        resp = client.post(url, params=params, json=body)
        data = resp.json()
    if data.get("errcode") != 0:
        raise Exception(f"获取审批实例详情失败: {data.get('errmsg')}")
    return data.get("process_instance", {})


def parse_special_apply_for_attendance(instance_detail: dict) -> dict:
    """
    解析特殊申请审批单中的考勤相关内容（兼容新旧版API返回格式）
    返回: {
        "instance_id": "...",
        "originator_user_id": "...",
        "status": "COMPLETED",
        "result": "agree",
        "apply_type": "考勤",  # 申请类型
        "attendance_items": [  # 考勤调整项
            {
                "field": "missed_clock_in_count",  # 要调整的字段
                "adjustment": -1,  # 调整量（负数表示减少）
                "date": "2026-07-10",  # 日期
                "reason": "缺卡补卡申请通过"
            }
        ],
        "raw_form": {}  # 原始表单数据
    }
    """
    # 兼容新旧版API的字段命名
    instance_id = instance_detail.get("processInstanceId") or instance_detail.get("process_instance_id", "")
    originator = instance_detail.get("originatorUserId") or instance_detail.get("originator_userid", "")
    status = instance_detail.get("status", "")
    # 旧版API中，审批结果在result字段，值为"agree"/"refuse"等；新版也是result
    result_val = instance_detail.get("result", "")
    title = instance_detail.get("title", "")
    
    result = {
        "instance_id": instance_id,
        "originator_user_id": originator,
        "status": status,
        "result": result_val,
        "title": title,
        "apply_type": "",
        "attendance_items": [],
        "raw_form": {},
    }

    # 解析表单组件（兼容新旧版命名：formComponentValues/form_component_values）
    form_values = instance_detail.get("formComponentValues") or instance_detail.get("form_component_values", [])
    form_map = {}
    for item in form_values:
        name = item.get("name", "")
        value = item.get("value", "")
        # 旧版API中，明细组件（如明细表）的值是JSON字符串，需要解析
        if isinstance(value, str) and value.startswith("[") and value.endswith("]"):
            try:
                import json
                value = json.loads(value)
            except:
                pass
        form_map[name] = value
    result["raw_form"] = form_map

    # 查找申请类型
    apply_type = ""
    for key in ["申请类型", "类型", "审批类型"]:
        if key in form_map:
            apply_type = form_map[key]
            break
    result["apply_type"] = apply_type

    # 只处理审批通过且是考勤相关的申请
    if result["status"] != "COMPLETED" or result["result"] != "agree":
        return result
    if not apply_type or "考勤" not in apply_type and "缺卡" not in apply_type and "打卡" not in apply_type:
        return result

    # 解析考勤调整项
    # 需要根据实际"特殊申请"模板的字段来解析，这里先做通用解析
    # 常见字段：申请日期、调整类型（缺卡/迟到/早退等）、调整次数、原因
    attendance_items = []
    
    # 尝试解析日期
    apply_date = ""
    for key in ["申请日期", "日期", "缺卡日期", "异常日期"]:
        if key in form_map and form_map[key]:
            date_val = str(form_map[key]).strip()
            if len(date_val) >= 10:
                apply_date = date_val[:10]
            break

    # 尝试解析调整类型
    adjust_type = ""
    for key in ["调整类型", "异常类型", "申请事项"]:
        if key in form_map:
            adjust_type = str(form_map[key]).strip()
            break

    # 尝试解析调整次数/天数
    adjust_count = 0
    for key in ["次数", "天数", "数量", "缺卡次数"]:
        if key in form_map:
            try:
                adjust_count = int(float(str(form_map[key]).strip()))
            except (ValueError, TypeError):
                pass
            break

    # 获取原因
    reason = ""
    for key in ["申请原因", "原因", "说明", "备注"]:
        if key in form_map:
            reason = str(form_map[key]).strip()
            break

    # 映射调整类型到数据库字段
    field_mapping = {
        "缺卡": "missed_punch_count",
        "上班缺卡": "missed_clock_in_count",
        "下班缺卡": "missed_clock_out_count",
        "迟到": "late_count",
        "早退": "early_count",
        "旷工": "absenteeism_days",
        "事假": "personal_leave_days",
    }

    # 确定要调整的字段
    target_field = None
    for keyword, field in field_mapping.items():
        if keyword in adjust_type:
            target_field = field
            break

    if target_field and adjust_count > 0:
        # 特殊申请通过后，异常次数应该减少（补卡成功）
        attendance_items.append({
            "field": target_field,
            "adjustment": -adjust_count if "天数" not in target_field else -round(adjust_count / 7.0, 2),
            "date": apply_date,
            "reason": reason or f"特殊申请审批通过（{adjust_type}）",
        })

    result["attendance_items"] = attendance_items
    return result


def get_month_special_applies(period: str, template_name: str = "特殊申请") -> list[dict]:
    """
    获取指定月份的特殊申请审批单（已审批通过的）
    period: YYYYMM格式
    返回: 解析后的考勤调整项列表
    """
    import time as time_mod
    year = int(period[:4])
    month = int(period[4:6])
    
    # 计算月份时间范围（Unix时间戳，毫秒）
    start_dt = datetime(year, month, 1)
    if month == 12:
        end_dt = datetime(year + 1, 1, 1) - timedelta(seconds=1)
    else:
        end_dt = datetime(year, month + 1, 1) - timedelta(seconds=1)
    
    start_ts = int(start_dt.timestamp() * 1000)
    end_ts = int(end_dt.timestamp() * 1000)

    # 1. 获取processCode
    process_code = get_process_code_by_name(template_name)
    logger.info(f"获取到审批模板「{template_name}」的processCode: {process_code}")

    # 2. 获取审批实例ID列表（只查已完成的）
    instance_ids = get_approval_instance_ids(
        process_code=process_code,
        start_time=start_ts,
        end_time=end_ts,
        statuses=["COMPLETED"],
    )
    logger.info(f"获取到{len(instance_ids)}个审批实例")

    # 3. 逐个获取详情并解析
    results = []
    for instance_id in instance_ids:
        try:
            detail = get_approval_instance_detail(instance_id)
            parsed = parse_special_apply_for_attendance(detail)
            if parsed["attendance_items"]:
                results.append(parsed)
        except Exception as e:
            logger.warning(f"获取审批实例{instance_id}详情失败: {e}")
            continue

    logger.info(f"解析到{len(results)}个有效的考勤特殊申请")
    return results


def apply_special_applies_to_attendance(db_session, period: str, applies: list[dict]) -> dict:
    """
    将特殊申请的考勤调整应用到考勤记录
    返回: {"applied": 应用数量, "updated": 更新员工数, "errors": 错误列表}
    """
    from app.models.models import Employee, AttendanceRecord
    
    stats = {"applied": 0, "updated": 0, "errors": []}
    updated_emp_ids = set()

    # 建立钉钉userId -> 员工映射
    emp_by_dingtalk = {}
    for emp in db_session.query(Employee).filter(Employee.dingtalk_user_id.isnot(None)).all():
        emp_by_dingtalk[emp.dingtalk_user_id] = emp

    for apply in applies:
        try:
            user_id = apply["originator_user_id"]
            emp = emp_by_dingtalk.get(user_id)
            if not emp:
                stats["errors"].append(f"申请人userId {user_id} 未在员工表中找到")
                continue

            # 查找该员工当月考勤记录
            att = db_session.query(AttendanceRecord).filter(
                AttendanceRecord.period == period,
                AttendanceRecord.employee_id == emp.id,
            ).first()
            if not att:
                stats["errors"].append(f"员工 {emp.name}({user_id}) 在{period}没有考勤记录")
                continue

            # 检查是否已经应用过该申请单
            existing_ids = att.special_apply_ids or []
            if apply["instance_id"] in existing_ids:
                continue  # 已应用，跳过

            # 应用调整项
            locked_fields = att.locked_fields or {}
            row_locked = att.is_row_locked or False
            for item in apply["attendance_items"]:
                field = item["field"]
                adjustment = item["adjustment"]
                reason = item["reason"]

                if row_locked:
                    stats["errors"].append(f"员工 {emp.name} 的考勤记录已整行锁定，跳过调整")
                    continue
                if locked_fields.get(field):
                    stats["errors"].append(f"员工 {emp.name} 的字段 {field} 已锁定，跳过调整")
                    continue

                current_val = getattr(att, field, 0) or 0
                if "days" in field:
                    new_val = round(float(current_val) + adjustment, 2)
                else:
                    new_val = int(current_val) + adjustment
                new_val = max(new_val, 0)  # 不能为负数
                setattr(att, field, new_val)
                
                # 更新备注
                existing_remark = att.remark or ""
                if reason and reason not in existing_remark:
                    att.remark = (existing_remark + f"；" if existing_remark else "") + f"特殊申请：{reason}"

            # 记录已应用的申请单ID
            existing_ids.append(apply["instance_id"])
            att.special_apply_ids = existing_ids
            
            # 重新计算考勤相关字段
            _recalculate_attendance_for_record(db_session, att)
            
            updated_emp_ids.add(emp.id)
            stats["applied"] += 1

        except Exception as e:
            stats["errors"].append(f"处理申请单 {apply.get('instance_id')} 失败: {str(e)}")

    db_session.commit()
    stats["updated"] = len(updated_emp_ids)
    return stats


def _recalculate_attendance_for_record(db_session, att) -> None:
    """根据当前字段重新计算考勤的计薪天数等（与attendance.py中的逻辑保持一致）"""
    from app.services import work_calendar as work_cal
    
    adjusted = work_cal.get_month_salary_days(db_session, att.period)
    
    late_count_val = att.late_count or 0
    late_duration_val = att.late_duration or 0
    late_to_leave = 0.0
    if late_count_val > 3 and late_duration_val > 0:
        late_to_leave = round(late_duration_val / 60 / 7.0, 2)
    
    leave_total = round(
        late_to_leave + 
        float(att.personal_leave_days or 0) + 
        float(att.reduced_pay_sick_days or 0) +
        float(att.statutory_sick_days or 0) + 
        float(att.prenatal_checkup_days or 0) +
        float(att.maternity_leave_days or 0) + 
        float(att.paternity_leave_days or 0) +
        float(att.marriage_leave_days or 0) + 
        float(att.funeral_leave_days or 0) +
        float(att.engineering_compensatory_days or 0), 2
    )
    
    actual_salary = max(round(adjusted - leave_total, 2), 0)
    att_rate = round(actual_salary / adjusted, 4) if adjusted > 0 else 0
    
    att.adjusted_salary_days = adjusted
    att.actual_salary_days = actual_salary
    att.actual_work_days = actual_salary
    att.late_to_personal_leave_days = late_to_leave
    att.leave_total_days = leave_total
    att.attendance_rate = att_rate


# ========== 新版 Workflow API (v1.0) ==========

def _get_new_api_headers() -> dict:
    """获取新版API请求头（使用x-acs-dingtalk-access-token）"""
    token = _get_access_token()
    return {
        "x-acs-dingtalk-access-token": token,
        "Content-Type": "application/json",
    }


def list_workflow_templates_v2(user_id: str = None, max_results: int = 100) -> list[dict]:
    """
    新版API：获取用户可见的审批表单列表
    GET /v1.0/workflow/processes/userVisibilities/templates
    权限要求：工作流模板读权限(Workflow.Form.Read)
    """
    url = "https://api.dingtalk.com/v1.0/workflow/processes/userVisibilities/templates"
    headers = _get_new_api_headers()
    all_templates = []
    next_token = 0

    while True:
        params = {"maxResults": min(max_results, 100), "nextToken": next_token}
        if user_id:
            params["userId"] = user_id
        with httpx.Client(timeout=30) as client:
            resp = client.get(url, headers=headers, params=params)
            data = resp.json()
        if "result" not in data:
            if "code" in data or "message" in data:
                raise Exception(f"获取审批模板列表失败(新版API): {data}")
            break
        result = data.get("result", {})
        process_list = result.get("processList", [])
        all_templates.extend(process_list)
        next_token = result.get("nextToken")
        if not next_token or not process_list:
            break

    return all_templates


def get_workflow_process_code_v2(template_name: str, user_id: str = None) -> str:
    """新版API：根据模板名称查找processCode"""
    templates = list_workflow_templates_v2(user_id=user_id)
    for tpl in templates:
        name = tpl.get("name", "") or tpl.get("flowTitle", "")
        if template_name in name or name in template_name:
            return tpl.get("processCode", "")
    all_names = [t.get("name", "") or t.get("flowTitle", "") for t in templates]
    raise Exception(f"新版API未找到名为「{template_name}」的模板，可用模板: {all_names}")


def get_workflow_instance_ids_v2(
    process_code: str,
    start_time: int,
    end_time: int,
    user_ids: list[str] = None,
    statuses: list[str] = None,
) -> list[str]:
    """
    新版API：获取审批实例ID列表
    POST /v1.0/workflow/processes/instanceIds/query
    权限要求：工作流实例读权限(Workflow.Instance.Read)
    start_time/end_time: Unix时间戳（毫秒）
    statuses: "RUNNING" | "TERMINATED" | "COMPLETED"
    """
    url = "https://api.dingtalk.com/v1.0/workflow/processes/instanceIds/query"
    headers = _get_new_api_headers()
    all_instance_ids = []
    next_token = 0

    while True:
        body = {
            "processCode": process_code,
            "startTime": start_time,
            "endTime": end_time,
            "nextToken": next_token,
            "maxResults": 20,
        }
        if user_ids:
            body["userIds"] = user_ids
        if statuses:
            body["statuses"] = statuses

        with httpx.Client(timeout=30) as client:
            resp = client.post(url, headers=headers, json=body)
            data = resp.json()
        if "result" not in data:
            if "code" in data or "message" in data:
                raise Exception(f"获取审批实例ID列表失败(新版API): {data}")
            break
        result = data.get("result", {})
        instance_ids = result.get("list", [])
        all_instance_ids.extend(instance_ids)
        next_token = result.get("nextToken")
        if not next_token or not instance_ids:
            break

    return all_instance_ids


def get_workflow_instance_detail_v2(process_instance_id: str) -> dict:
    """
    新版API：获取单个审批实例详情
    GET /v1.0/workflow/processInstances?processInstanceId=xxx
    权限要求：工作流实例读权限(Workflow.Instance.Read)
    """
    url = "https://api.dingtalk.com/v1.0/workflow/processInstances"
    headers = _get_new_api_headers()
    params = {"processInstanceId": process_instance_id}
    with httpx.Client(timeout=30) as client:
        resp = client.get(url, headers=headers, params=params)
        data = resp.json()
    # 新版API返回在result字段中
    if "result" not in data and ("code" in data or "message" in data):
        raise Exception(f"获取审批实例详情失败(新版API): {data}")
    return data.get("result", data)


def list_workflow_templates_manageable_v2(user_id: str) -> list[dict]:
    """
    新版API：获取当前企业所有可管理的表单（需要OA审批管理员权限）
    GET /v1.0/workflow/processes/managements/templates
    """
    url = "https://api.dingtalk.com/v1.0/workflow/processes/managements/templates"
    headers = _get_new_api_headers()
    params = {"userId": user_id}
    with httpx.Client(timeout=30) as client:
        resp = client.get(url, headers=headers, params=params)
        data = resp.json()
    if "result" not in data and ("code" in data or "message" in data):
        raise Exception(f"获取可管理表单列表失败(新版API): {data}")
    return data.get("result", [])


# ========== 缺卡自动核销功能 ==========


def _parse_apply_description_for_month(desc: str, target_year: int, target_month: int) -> dict:
    """
    解析特殊申请说明中指定月份的缺卡次数
    返回: {"total_count": int, "daily_counts": dict, "target_month_mentioned": bool, "has_other": bool}
    """
    if not desc:
        return {"total_count": 0, "daily_counts": {}, "target_month_mentioned": False, "has_other": False}
    
    total = 0
    daily = {}
    date_pattern = rf'{target_month}[月/\-](\d{{1,2}})[日号]?\s*(\d+)\s*次'
    matches = re.findall(date_pattern, desc)
    for m in matches:
        day = int(m[0])
        count = int(m[1])
        daily[day] = count
        total += count
    
    has_other = "调休" in desc or "请假" in desc
    
    if daily:
        return {"total_count": total, "daily_counts": daily, "target_month_mentioned": True, "has_other": has_other}
    return {"total_count": 0, "daily_counts": {}, "target_month_mentioned": False, "has_other": has_other}


def _get_special_process_code_v2(template_name: str = "特殊申请") -> str:
    """获取特殊申请模板的processCode（使用新版API）"""
    templates = list_workflow_templates_v2(max_results=100)
    for tpl in templates:
        name = tpl.get('name', '') or tpl.get('flowTitle', '')
        if template_name in name:
            return tpl.get('processCode')
    raise Exception(f"未找到名为「{template_name}」的审批模板")


def check_missed_punch_applies(
    db_session,
    period: str,
    apply_start_day: int = 1,
    apply_end_day: int = 15
) -> dict:
    """
    检查指定月份有缺卡记录的员工是否有审批通过的考勤特殊申请
    period: YYYYMM格式，要检查的考勤月份
    apply_start_day/apply_end_day: 查询申请的日期范围（次月的几号到几号）
    
    返回比对结果，包含匹配、不匹配、无申请的员工列表
    """
    from app.models.models import Employee, AttendanceRecord
    from datetime import datetime as _dt
    
    target_year = int(period[:4])
    target_month = int(period[4:6])
    
    # 计算申请查询时间范围（次月1号到次月15号，或当前日期）
    if target_month == 12:
        apply_year = target_year + 1
        apply_month = 1
    else:
        apply_year = target_year
        apply_month = target_month + 1
    
    now = _dt.now()
    current_end_day = min(apply_end_day, now.day) if (now.year == apply_year and now.month == apply_month) else apply_end_day
    
    start_dt = _dt(apply_year, apply_month, apply_start_day)
    end_dt = _dt(apply_year, apply_month, current_end_day, 23, 59, 59)
    start_ts = int(start_dt.timestamp() * 1000)
    end_ts = int(end_dt.timestamp() * 1000)
    
    # 1. 查询该月份有缺卡记录的员工（每个员工只取最新的一条记录）
    from sqlalchemy import func
    # 先找到每个员工在该周期的最大ID记录
    latest_ids = (
        db_session.query(
            AttendanceRecord.employee_id,
            func.max(AttendanceRecord.id).label('max_id')
        )
        .filter(AttendanceRecord.period == period)
        .group_by(AttendanceRecord.employee_id)
        .subquery()
    )
    
    records = (
        db_session.query(AttendanceRecord, Employee)
        .join(Employee, AttendanceRecord.employee_id == Employee.id)
        .join(latest_ids, (AttendanceRecord.employee_id == latest_ids.c.employee_id) & 
              (AttendanceRecord.id == latest_ids.c.max_id))
        .filter(AttendanceRecord.period == period)
        .all()
    )
    
    employees_with_miss = []
    for att, emp in records:
        half_day = att.half_day_missed_punch or 0
        absenteeism_days = float(att.absenteeism_days or 0)
        total_missed = half_day + int(absenteeism_days * 2)
        
        if total_missed <= 0 or absenteeism_days >= 21:
            continue
        
        employees_with_miss.append({
            "employee_id": emp.id,
            "employee_no": emp.employee_no,
            "employee_name": emp.name,
            "dingtalk_user_id": emp.dingtalk_user_id,
            "attendance_id": att.id,
            "half_day_missed_punch": half_day,
            "absenteeism_days": absenteeism_days,
            "total_missed": total_missed,
            "att_record": att,
        })
    
    if not employees_with_miss:
        return {
            "period": period,
            "apply_range": f"{apply_year}-{apply_month:02d}-{apply_start_day:02d} ~ {apply_year}-{apply_month:02d}-{current_end_day:02d}",
            "employees_with_miss": [],
            "matched": [],
            "mismatched": [],
            "no_apply": [],
            "summary": {"total_miss_employees": 0, "matched": 0, "mismatched": 0, "no_apply": 0}
        }
    
    # 2. 获取特殊申请模板
    special_process_code = _get_special_process_code_v2()
    
    # 3. 查询所有相关员工的审批实例（只查COMPLETED状态）
    all_user_ids = [e["dingtalk_user_id"] for e in employees_with_miss if e["dingtalk_user_id"]]
    instance_dict = {}
    
    batch_size = 10
    for i in range(0, len(all_user_ids), batch_size):
        batch_ids = all_user_ids[i:i+batch_size]
        try:
            ids = get_workflow_instance_ids_v2(
                process_code=special_process_code,
                start_time=start_ts,
                end_time=end_ts,
                user_ids=batch_ids,
                statuses=["COMPLETED"],
            )
            for iid in ids:
                instance_dict[iid] = "COMPLETED"
        except Exception as e:
            logger.warning(f"查询审批实例失败(批次{i//batch_size}): {e}")
    
    # 4. 筛选审批通过(result=agree)的考勤申请
    june_attendance_applies = []
    for iid in instance_dict.keys():
        try:
            detail = get_workflow_instance_detail_v2(iid)
            actual_status = detail.get("status", "")
            actual_result = detail.get("result", "")
            
            if actual_status != "COMPLETED" or actual_result != "agree":
                continue
            
            form_values = detail.get("formComponentValues", [])
            form_data = {}
            for item in form_values:
                name = item.get("name", "")
                value = item.get("value", "")
                form_data[name] = value
            
            apply_type = ""
            for key in ["申请类型", "类型"]:
                if key in form_data:
                    apply_type = str(form_data[key])
                    break
            if "考勤" not in apply_type:
                continue
            
            description = ""
            for key in ["申请说明", "审批详情", "说明"]:
                if key in form_data:
                    description = str(form_data[key])
                    break
            
            count_field = ""
            for key in ["超标准金额/次数/天数/里程数", "次数"]:
                if key in form_data:
                    count_field = str(form_data[key])
                    break
            
            create_time_str = detail.get("createTime", "")
            originator = detail.get("originatorUserId", "")
            title = detail.get("title", "")
            finish_time = detail.get("finishTime", "")
            
            parsed = _parse_apply_description_for_month(description, target_year, target_month)
            
            apply_count = 0
            if parsed["target_month_mentioned"]:
                apply_count = parsed["total_count"]
            else:
                if any(kw in description for kw in ["忘记打卡", "缺卡", "没打卡"]):
                    try:
                        apply_count = int(count_field) if count_field else 0
                    except:
                        pass
                elif "调休" not in description and "请假" not in description:
                    try:
                        apply_count = int(count_field) if count_field else 0
                    except:
                        pass
            
            june_attendance_applies.append({
                "instance_id": iid,
                "user_id": originator,
                "title": title,
                "description": description,
                "count_field": count_field,
                "parsed": parsed,
                "apply_count": apply_count,
                "has_other": parsed["has_other"],
                "status": actual_status,
                "result": actual_result,
                "create_time": create_time_str,
                "finish_time": finish_time,
            })
            
        except Exception as e:
            logger.warning(f"获取实例{iid}详情失败: {e}")
    
    # 5. 按员工分组比对
    matched = []
    mismatched = []
    no_apply = []
    
    for emp_info in employees_with_miss:
        user_id = emp_info["dingtalk_user_id"]
        emp_applies = [a for a in june_attendance_applies if a["user_id"] == user_id]
        
        if emp_applies:
            total_apply = sum(a["apply_count"] for a in emp_applies)
            emp_result = {
                **emp_info,
                "applies": emp_applies,
                "total_apply_count": total_apply,
            }
            if total_apply == emp_info["total_missed"]:
                matched.append(emp_result)
            else:
                mismatched.append(emp_result)
        else:
            no_apply.append(emp_info)
    
    return {
        "period": period,
        "apply_range": f"{apply_year}-{apply_month:02d}-{apply_start_day:02d} ~ {apply_year}-{apply_month:02d}-{current_end_day:02d}",
        "employees_with_miss": employees_with_miss,
        "matched": matched,
        "mismatched": mismatched,
        "no_apply": no_apply,
        "all_applies": june_attendance_applies,
        "summary": {
            "total_miss_employees": len(employees_with_miss),
            "matched": len(matched),
            "mismatched": len(mismatched),
            "no_apply": len(no_apply),
            "total_applies_found": len(june_attendance_applies),
        }
    }


def apply_missed_punch_write_off(
    db_session,
    period: str,
    employee_ids: list[int] = None,
    apply_all_matched: bool = False
) -> dict:
    """
    执行缺卡核销：将匹配员工的半天缺卡和全天缺卡清零
    employee_ids: 指定要核销的员工ID列表，为空时如果apply_all_matched=True则核销所有匹配的
    apply_all_matched: 是否自动核销所有匹配的员工
    
    返回核销结果统计
    """
    from app.models.models import AttendanceRecord
    from app.api.attendance import _recalculate_attendance_fields
    
    check_result = check_missed_punch_applies(db_session, period)
    
    to_write_off = []
    if apply_all_matched:
        to_write_off = check_result["matched"]
    elif employee_ids:
        id_set = set(employee_ids)
        to_write_off = [e for e in check_result["matched"] if e["employee_id"] in id_set]
    
    updated_count = 0
    updated_employees = []
    for emp_info in to_write_off:
        emp_id = emp_info["employee_id"]
        
        # 重新查询该员工该周期的所有考勤记录（处理可能的重复记录情况）
        att_records = (
            db_session.query(AttendanceRecord)
            .filter(
                AttendanceRecord.period == period,
                AttendanceRecord.employee_id == emp_id
            )
            .all()
        )
        
        if not att_records:
            continue
        
        for att in att_records:
            if att.is_row_locked:
                continue
            
            locked_fields = att.locked_fields or {}
            if locked_fields.get("half_day_missed_punch") or locked_fields.get("absenteeism_days"):
                continue
            
            # 记录申请单ID
            existing_ids = att.special_apply_ids or []
            for apply in emp_info["applies"]:
                if apply["instance_id"] not in existing_ids:
                    existing_ids.append(apply["instance_id"])
            
            # 清零缺卡
            att.half_day_missed_punch = 0
            att.absenteeism_days = 0
            att.special_apply_ids = existing_ids
            
            # 添加备注
            existing_remark = att.remark or ""
            remark_add = "缺卡已核销（特殊申请审批通过）"
            if remark_add not in existing_remark:
                att.remark = (existing_remark + "；" if existing_remark else "") + remark_add
            
            # 重新计算考勤相关字段
            _recalculate_attendance_fields(db_session, att)
        
        updated_count += 1
        updated_employees.append({
            "employee_id": emp_id,
            "employee_name": emp_info["employee_name"],
            "previous_half_day": emp_info["half_day_missed_punch"],
            "previous_absenteeism": emp_info["absenteeism_days"],
            "apply_count": emp_info["total_apply_count"],
        })
    
    if updated_count > 0:
        db_session.commit()
    
    return {
        "period": period,
        "updated_count": updated_count,
        "updated_employees": updated_employees,
        "check_summary": check_result["summary"]
    }
