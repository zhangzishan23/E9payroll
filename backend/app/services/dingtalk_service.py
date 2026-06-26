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
from datetime import datetime, date, timedelta
from typing import Optional
import httpx

from app.core.config import DINGTALK_CLIENT_ID, DINGTALK_CLIENT_SECRET, DINGTALK_AGENT_ID, DINGTALK_SYNC_DEPT_NAMES
from app.models.models import SysDictBase

logger = logging.getLogger(__name__)

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
    用钉钉 deptId 作为 code，新增不存在的部门，已有部门不修改名称和启用状态。
    同时更新 parent_id 以支持层级展示。
    返回: {"created": 0, "skipped": 0}
    """
    from app.models.models import SysDictBase

    dept_map = get_dept_tree()
    existing = {d.code: d for d in db_session.query(SysDictBase).filter(SysDictBase.category == "department").all()}

    created = 0
    skipped = 0
    # 第一步：创建不存在的部门
    for did, info in dept_map.items():
        if did == 1:  # 跳过钉钉根节点
            continue
        code = str(did)
        if code in existing:
            skipped += 1
        else:
            db_session.add(SysDictBase(
                category="department",
                code=code,
                name=info["name"],
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
    return {"created": created, "skipped": skipped, "total": len(dept_map) - 1}


def get_target_dept_ids(db_session=None) -> list[int]:
    """
    从数据库读取已启用的部门，通过 code（钉钉 deptId）匹配，获取需要同步的部门ID列表。
    支持子部门独立禁用：只返回数据库中 is_enabled=True 的部门。
    """
    from app.models.models import SysDictBase

    dept_map = get_dept_tree()

    # 从数据库读取所有已启用的部门（不再限制 parent_id）
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

    # code 就是钉钉 deptId，转换为 int 匹配
    target_ids: set[int] = set()
    for d in enabled_depts:
        if d.code and d.code.isdigit():
            dept_id = int(d.code)
            if dept_id in dept_map:
                target_ids.add(dept_id)

    if not target_ids:
        logger.warning("没有已启用的部门（code 为空或不在钉钉部门树中），数据同步将跳过所有部门")
        return []

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


# 考勤列名 → 系统字段映射（根据钉钉实际返回的列名）
ATTENDANCE_COLUMN_MAP = {
    "应出勤天数": "total_work_days",
    "出勤天数": "actual_work_days",  # 钉钉实际列名
    "迟到次数": "late_count",
    "早退次数": "early_count",
    "上班缺卡次数": "missed_punch_count",  # 钉钉分上班/下班缺卡
    "下班缺卡次数": "missed_punch_count",  # 会累加
    "全薪病假": "sick_leave_days",  # 钉钉实际列名
    "法定病假": "sick_leave_days",  # 备用
    "事假": "personal_leave_days",  # 钉钉实际列名
    "年假": "annual_leave_days",  # 钉钉实际列名
    "调休": "other_leave_days",  # 钉钉实际列名
    "调休假天数": "other_leave_days",  # 备用
    "婚假": "other_leave_days",
    "产假": "other_leave_days",
    "陪产假": "other_leave_days",
    "丧假": "other_leave_days",
}


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

def sync_roster_to_db(db_session, mode: str = "full") -> dict:
    """
    将钉钉花名册同步到系统 Employee 表。
    mode: "full" 全量同步 / "incremental" 增量同步（基于数据更新时间戳）
    匹配逻辑：优先按 dingtalk_user_id 匹配，其次按手机号。
    冲突处理：本地优先，已存在的员工非空字段不会被钉钉覆盖。
    返回: {"created": 0, "updated": 0, "errors": []}
    """
    from app.models.models import Employee, SysDictBase

    started_at = datetime.now()
    sync_type = f"roster_{mode}"
    stats = {"created": 0, "updated": 0, "errors": []}

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
    dept_map = {d.code: d.id for d in dict_items if d.category == "department" and d.code}
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

    # 钉钉 dept_name → dept_id 映射
    dept_name_to_id = {info["name"]: did for did, info in dept_tree.items()}
    logger.info(f"部门映射样本: {dict(list(dept_name_to_id.items())[:5])}")

    # 获取所有已有员工（按 dingtalk_user_id 索引）
    existing_employees = db_session.query(Employee).all()
    emp_by_dingtalk = {e.dingtalk_user_id: e for e in existing_employees if e.dingtalk_user_id}
    emp_by_phone = {e.phone: e for e in existing_employees if e.phone}

    for user_id, fields in user_roster_map.items():
        try:
            # ---- 提取所有字段 ----
            name = fields.get("sys00-name", "")
            phone = fields.get("sys00-mobile", "")
            email = fields.get("sys00-email", "")
            work_place = fields.get("sys00-workPlace", "")
            job_number = fields.get("sys00-jobNumber", "")
            dept_name = fields.get("sys00-dept", "")
            main_dept_name = fields.get("sys00-mainDept", dept_name)
            position_name = fields.get("sys00-position", "")
            report_manager = fields.get("sys00-reportManager", "")
            remark = fields.get("sys00-remark", "")
            hired_date_str = fields.get("sys00-confirmJoinTime", "") or fields.get("sys00-hiredDate", "")
            # sys01 - 工作信息
            employee_type = fields.get("sys01-employeeType", "")
            status_name = fields.get("sys01-employeeStatus", "") or fields.get("sys00-staffStatus", "")
            position_level = fields.get("sys01-positionLevel", "")
            plan_regular_date_str = fields.get("sys01-planRegularTime", "")
            regular_date_str = fields.get("sys01-regularTime", "") or fields.get("sys00-regularDate", "")
            resign_date_str = fields.get("sys00-resignDate", "")
            # sys02 - 个人信息
            id_card = fields.get("sys02-certNo", "") or fields.get("sys00-idCard", "")
            gender_raw = fields.get("sys02-sexType", "") or fields.get("sys00-gender", "")
            birth_date_str = fields.get("sys02-birthTime", "")
            nation = fields.get("sys02-nationType", "")
            marital_status = fields.get("sys02-marriage", "")
            children_status = fields.get("1e8e7d6d-6f56-49fc-a7aa-215f3bb5361c", "")
            political_status = fields.get("sys02-politicalStatus", "")
            native_place = fields.get("e6535432-0334-4090-bc86-aeec046c45b7", "")
            residence_type = fields.get("sys02-residenceType", "")
            census_address = fields.get("sys02-certAddress", "")
            home_address = fields.get("sys02-address", "")
            first_work_date_str = fields.get("sys02-joinWorkingTime", "")
            # sys03 - 学历
            education = fields.get("sys03-highestEdu", "")
            graduate_school = fields.get("sys03-graduateSchool", "")
            graduate_date_str = fields.get("sys03-graduationTime", "")
            major = fields.get("sys03-major", "")
            # sys04 - 银行卡
            bank_card = fields.get("sys04-bankAccountNo", "")
            bank_branch = fields.get("sys04-accountBank", "")
            bank_branch_detail = fields.get("c973eb37-4d74-47c3-b84a-c685e73b1e30", "")
            # sys05 - 合同
            contract_company_name = fields.get("sys05-contractCompanyName", "")
            contract_type = fields.get("sys05-contractType", "")
            contract_start_date_str = fields.get("sys05-nowContractStartTime", "")
            contract_end_date_str = fields.get("sys05-nowContractEndTime", "")
            # sys06 - 紧急联系人
            emergency_contact_name = fields.get("sys06-urgentContactsName", "")
            emergency_contact_relation = fields.get("sys06-urgentContactsRelation", "")
            emergency_contact_phone = fields.get("sys06-urgentContactsPhone", "")
            # 自定义字段
            job_level = fields.get("81922c26-7b0a-40fe-b87c-7373b85a8941", "")
            recruitment_channel = fields.get("9e199205-1337-44e2-94e8-624a92adca9f", "")
            hobby = fields.get("90300477-bcc9-4c70-a5ee-dbc256df20c5", "")
            cert1 = fields.get("89474793-54fe-4cc8-bbb0-b21a834949dc", "")
            cert2 = fields.get("cba563d1-96cd-4739-89e3-18f912bb707e", "")
            insurance_start_date_str = fields.get("6d119e8d-0cde-4d73-975d-85d15174d0d0", "")
            insurance_location = fields.get("6ea63544-3d03-47aa-929d-8995277029c4", "")
            commercial_insurance_type = fields.get("fd1cc8aa-8af7-4574-bba4-1986d5acff03", "")

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
            dept_id = dept_map.get(str(root_dept_id), 1) if root_dept_id else 1

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
                if position_name and position_name in position_map:
                    emp.position_id = position_map[position_name]
                if status_name and not _get_status_id(status_name, status_map) == 1:
                    if "离职" in status_name:
                        emp.status_id = status_map.get("离职", emp.status_id)
                    elif "试用" in status_name:
                        emp.status_id = status_map.get("试用期", emp.status_id)
                    elif "正式" in status_name:
                        emp.status_id = status_map.get("正式", emp.status_id)
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
                    position_id=position_map.get(position_name, 1) if position_name in position_map else 1,
                    status_id=_get_status_id(status_name, status_map),
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

    # 建立列名→列ID映射（根据ATTENDANCE_COLUMN_MAP中的中文名匹配）
    col_name_to_id = {}
    for col in columns:
        col_name_to_id[col["name"]] = col["id"]

    # 找出我们关心的列ID（过滤掉None）
    target_col_ids = []
    for cn_name in ATTENDANCE_COLUMN_MAP:
        if cn_name in col_name_to_id and col_name_to_id[cn_name] is not None:
            target_col_ids.append(col_name_to_id[cn_name])

    if not target_col_ids:
        stats["errors"].append("未找到匹配的考勤列，请检查钉钉考勤报表列定义")
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

    # 3. 获取所有已关联钉钉的员工
    employees = db_session.query(Employee).filter(Employee.dingtalk_user_id.isnot(None)).all()
    if not employees:
        stats["errors"].append("没有已关联钉钉的员工，请先同步花名册")
        _write_sync_log(db_session, "attendance_monthly", "failed", period=period,
                        error_detail=stats["errors"], started_at=started_at, finished_at=datetime.now())
        return stats

    # 4. 逐员工获取考勤数据并汇总
    for emp in employees:
        try:
            vals = get_attendance_column_values(
                emp.dingtalk_user_id, target_col_ids, from_date, to_date
            )
            # 汇总：按列名聚合月内每天的值
            monthly = _aggregate_attendance(vals, col_name_to_id)
            if not monthly:
                continue

            # 计算出勤率
            total = monthly.get("total_work_days", 0)
            actual = monthly.get("actual_work_days", 0)
            rate = round(actual / total, 4) if total > 0 else 0

            # upsert
            record = db_session.query(AttendanceRecord).filter(
                AttendanceRecord.period == period,
                AttendanceRecord.employee_id == emp.id,
            ).first()

            if record:
                record.total_work_days = total
                record.actual_work_days = actual
                record.attendance_rate = rate
                record.late_count = int(monthly.get("late_count", 0))
                record.early_count = int(monthly.get("early_count", 0))
                record.missed_punch_count = int(monthly.get("missed_punch_count", 0))
                record.sick_leave_days = monthly.get("sick_leave_days", 0)
                record.personal_leave_days = monthly.get("personal_leave_days", 0)
                record.annual_leave_days = monthly.get("annual_leave_days", 0)
                record.other_leave_days = monthly.get("other_leave_days", 0)
            else:
                record = AttendanceRecord(
                    period=period,
                    employee_id=emp.id,
                    total_work_days=total,
                    actual_work_days=actual,
                    attendance_rate=rate,
                    late_count=int(monthly.get("late_count", 0)),
                    early_count=int(monthly.get("early_count", 0)),
                    missed_punch_count=int(monthly.get("missed_punch_count", 0)),
                    sick_leave_days=monthly.get("sick_leave_days", 0),
                    personal_leave_days=monthly.get("personal_leave_days", 0),
                    annual_leave_days=monthly.get("annual_leave_days", 0),
                    other_leave_days=monthly.get("other_leave_days", 0),
                )
                db_session.add(record)

            stats["synced"] += 1

        except Exception as e:
            stats["errors"].append(f"同步 {emp.name}({emp.dingtalk_user_id}) 考勤失败: {str(e)}")

    db_session.commit()

    # 5. 数据校验：确认同步数量
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
    列ID→中文名逆向映射，再映射到系统字段。
    """
    id_to_name = {v: k for k, v in col_name_to_id.items()}
    result = {}
    for item in vals:
        col_name = item.get("column_name") or id_to_name.get(item.get("column_id"), "")
        field = ATTENDANCE_COLUMN_MAP.get(col_name)
        if not field:
            continue
        try:
            val = float(item.get("value", 0))
        except (ValueError, TypeError):
            val = 0
        result[field] = result.get(field, 0) + val
    return result


def _parse_gender(gender_raw: str) -> str:
    """解析钉钉性别字段"""
    if not gender_raw:
        return "未知"
    if "男" in gender_raw:
        return "男"
    if "女" in gender_raw:
        return "女"
    return "未知"


def _get_status_id(status_name: str, status_map: dict) -> int:
    """根据钉钉状态名映射到系统状态ID"""
    if not status_name:
        return 1
    if "离职" in status_name:
        return status_map.get("离职", 1)
    if "试用" in status_name:
        return status_map.get("试用期", 1)
    if "正式" in status_name:
        return status_map.get("正式", 1)
    return 1


def _get_or_create_contract_company(db_session, company_name: str, company_map: dict) -> int:
    """获取合同公司ID，如果不存在则自动创建。"""
    if not company_name:
        return 1
    if company_name in company_map:
        return company_map[company_name]
    # 自动创建合同公司
    new_id = max(company_map.values(), default=0) + 1
    new_company = SysDictBase(
        category="contract_company",
        code=f"dingtalk_{company_name}",
        name=company_name,
    )
    db_session.add(new_company)
    db_session.flush()
    company_map[company_name] = new_company.id
    return new_company.id


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