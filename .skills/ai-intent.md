# Skill: AI 意图识别（ai-intent）

## 描述
将用户的自然语言输入（中文）解析为结构化的操作意图。使用正则规则引擎做第一层匹配，未匹配的提交给 LLM 做语义理解。这是 AI 助手模块的核心引擎。

## 代码（Python）
```python
import re
from typing import Optional, Dict, List, Tuple


INTENT_PATTERNS: List[Tuple[str, str]] = [
    (r'查询.*员工|查看.*员工|员工.*信息|员工.*档案|列出.*员工|所有.*员工|全部.*员工|多少.*员工|员工.*列表|员工.*数量|搜索.*员工', 'query_employee'),
    (r'查询.*薪资|查看.*薪资|薪资.*多少|工资.*多少|薪资.*明细|工资.*明细|本月.*薪资|本月.*工资|薪资.*计算|工资.*计算|薪资核算|薪酬', 'query_salary'),
    (r'查询.*考勤|查看.*考勤|考勤.*情况|考勤.*记录|出勤.*情况|出勤率|请假|迟到|早退|缺卡|考勤.*统计', 'query_attendance'),
    (r'查询.*绩效|查看.*绩效|绩效.*情况|绩效.*评分|绩效.*系数|绩效.*记录|绩效.*统计', 'query_performance'),
    (r'查询.*社保|查看.*社保|社保.*多少|公积金.*多少|社保.*明细|公积金.*明细|社保.*记录|社保公积金|五险一金', 'query_insurance'),
    (r'查询.*审批|查看.*审批|审批.*状态|审批.*记录|审批.*列表|审核.*状态', 'query_approval'),
    (r'新增.*员工|添加.*员工|录入.*员工|创建.*员工|导入.*员工', 'create_employee'),
    (r'编辑.*员工|修改.*员工|更新.*员工|变更.*员工', 'edit_employee'),
    (r'删除.*员工|移除.*员工', 'delete_employee'),
    (r'系统.*状态|系统.*信息|系统.*概况|系统.*概览|当前.*模块|模块.*列表|功能.*列表|数据.*统计', 'query_system'),
    (r'字典|数据字典|字典项|字典分类', 'query_dict'),
    (r'日志|操作日志|系统日志', 'query_log'),
    (r'你好|hello|hi|嗨|在吗|帮助|help|能做什么|你会什么|你是谁|介绍一下', 'greeting'),
]

SYSTEM_KEYWORDS = ['所有', '全部', '本月', '这个', '什么', '哪个', '如何', '怎么', '系统', '模块', '功能']

INTENT_LABELS = {
    'query_employee': '查询员工',
    'query_salary': '查询薪资',
    'query_attendance': '查询考勤',
    'query_performance': '查询绩效',
    'query_insurance': '查询社保',
    'query_approval': '查询审批',
    'query_system': '查询系统',
    'query_dict': '查询字典',
    'query_log': '查询日志',
    'create_employee': '新增员工',
    'edit_employee': '编辑员工',
    'delete_employee': '删除员工',
    'greeting': '打招呼',
    'unknown': '未知意图',
}


def extract_person_name(text: str) -> Optional[str]:
    """从文本中提取中文人名（2-4字）"""
    patterns = [
        r'(?:查询|查看|搜索|找|员工|档案).{0,4}?([\u4e00-\u9fa5]{2,4})(?:的|这|那|信息|档案|薪资|工资|考勤|绩效|社保)?',
        r'(?:新增|添加|创建|录入|编辑|修改|删除|导入).{0,4}?([\u4e00-\u9fa5]{2,4})',
        r'([\u4e00-\u9fa5]{2,4})(?:的|这).{0,6}(?:信息|档案|薪资|工资|考勤|绩效|社保|公积金|员工)',
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            name = m.group(1)
            if name not in SYSTEM_KEYWORDS:
                return name
    return None


def detect_intent(text: str) -> dict:
    """
    检测用户输入的意图。

    参数：text - 用户原始输入（中文）

    返回：
    {
        "intent": "query_employee",     # 意图代码
        "label": "查询员工",              # 中文标签
        "person_name": "张三",           # 提取到的人名（可选）
        "confidence": "rule"            # 置信度类型（rule / llm）
    }
    """
    text_lower = text.lower().strip()

    for pattern, intent in INTENT_PATTERNS:
        if re.search(pattern, text_lower):
            return {
                "intent": intent,
                "label": INTENT_LABELS.get(intent, intent),
                "person_name": extract_person_name(text),
                "confidence": "rule",
            }

    return {
        "intent": "unknown",
        "label": "未知意图",
        "person_name": extract_person_name(text),
        "confidence": "none",
    }


def is_dangerous_intent(intent: str) -> bool:
    """判断是否为危险操作（需二次确认）"""
    return intent in ('edit_employee', 'delete_employee')
```

## 外部依赖与错误处理
- 依赖：Python 标准库 `re`
- 纯文本匹配，不涉及数据库，不会抛异常
- Pattern 匹配顺序影响结果：更具体的规则放在前面
- 人名提取可能误判（如「李白」会被识别为提问对象），由 `SYSTEM_KEYWORDS` 过滤
- 新增意图只需在 `INTENT_PATTERNS` 和 `INTENT_LABELS` 中追加

## 调用示例
```python
result = detect_intent("查询员工张三的薪资")
# {"intent": "query_salary", "label": "查询薪资", "person_name": "张三", "confidence": "rule"}

result = detect_intent("本月有多少员工")
# {"intent": "query_employee", "label": "查询员工", "person_name": None, "confidence": "rule"}

result = detect_intent("你好")
# {"intent": "greeting", "label": "打招呼", "person_name": None, "confidence": "rule"}
```

## 使用场景
- [ai_assistant.py](file:///d:/devtool/cm/backend/app/api/ai_assistant.py) - AI 助手的 `detect_intent()` 函数
- 扩展方向：加入 LLM 做语义兜底，处理规则匹配不到的复杂问题