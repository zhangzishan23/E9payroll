export const SOCIAL_INSURANCE_COLUMNS = [
  { key: 'employee_no', label: '员工编号', width: 90, type: 'text' },
  { key: 'employee_name', label: '姓名', width: 70, type: 'text' },
  { key: 'contract_company', label: '合同公司', width: 120, type: 'text' },
  { key: 'department', label: '部门', width: 90, type: 'text' },
  { key: 'position', label: '职务', width: 90, type: 'text' },
  { key: 'pension_personal', label: '养老（个人）', width: 100, type: 'money' },
  { key: 'pension_company', label: '养老（公司）', width: 100, type: 'money' },
  { key: 'medical_personal', label: '医疗（个人）', width: 100, type: 'money' },
  { key: 'medical_company', label: '医疗（公司）', width: 100, type: 'money' },
  { key: 'unemployment_personal', label: '失业（个人）', width: 100, type: 'money' },
  { key: 'unemployment_company', label: '失业（公司）', width: 100, type: 'money' },
  { key: 'injury_company', label: '工伤（公司）', width: 100, type: 'money' },
  { key: 'maternity_company', label: '生育（公司）', width: 100, type: 'money' },
  { key: 'housing_fund_personal', label: '公积金（个人）', width: 110, type: 'money' },
  { key: 'housing_fund_company', label: '公积金（公司）', width: 110, type: 'money' },
  { key: 'personal_total', label: '个人合计', width: 90, type: 'money' },
  { key: 'company_total', label: '公司合计', width: 90, type: 'money' },
  { key: 'total_amount', label: '五险一金合计', width: 110, type: 'money' },
]

export function getSocialInsuranceFieldLabel(key) {
  const col = SOCIAL_INSURANCE_COLUMNS.find(c => c.key === key)
  return col ? col.label : key
}
