import { SALARY_COLUMNS, SALARY_EDITABLE_FIELDS, getSalaryFieldLabel } from './salaryColumns'
import { ATTENDANCE_COLUMNS, getAttendanceFieldLabel } from './attendanceColumns'
import { ROSTER_COLUMNS, getRosterFieldLabel } from './rosterColumns'
import { SOCIAL_INSURANCE_COLUMNS, getSocialInsuranceFieldLabel } from './socialInsuranceColumns'

export {
  SALARY_COLUMNS, SALARY_EDITABLE_FIELDS, getSalaryFieldLabel,
  ATTENDANCE_COLUMNS, getAttendanceFieldLabel,
  ROSTER_COLUMNS, getRosterFieldLabel,
  SOCIAL_INSURANCE_COLUMNS, getSocialInsuranceFieldLabel,
}

export const ALL_EXPORT_FIELDS = {
  salary: SALARY_COLUMNS,
  roster: ROSTER_COLUMNS,
  attendance: ATTENDANCE_COLUMNS,
  social_insurance: SOCIAL_INSURANCE_COLUMNS,
}
