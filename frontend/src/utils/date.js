/**
 * 获取默认账期月份
 * 规则：当月15日前显示上个月，15日及之后显示当月
 */
export function getDefaultPeriod() {
  const now = new Date();
  const year = now.getFullYear();
  const month = now.getMonth() + 1;
  const day = now.getDate();

  if (day < 15) {
    if (month === 1) {
      return `${year - 1}12`;
    }
    return `${year}${String(month - 1).padStart(2, '0')}`;
  }
  return `${year}${String(month).padStart(2, '0')}`;
}

/**
 * 格式化月份显示 (YYYYMM -> YYYY年MM月)
 */
export function formatPeriodDisplay(period) {
  if (!period) return '';
  const year = period.substring(0, 4);
  const month = period.substring(4, 6);
  return `${year}年${month}月`;
}

/**
 * 获取上一个月份
 */
export function getPrevPeriod(period) {
  const year = parseInt(period.substring(0, 4));
  const month = parseInt(period.substring(4, 6));
  if (month === 1) {
    return `${year - 1}12`;
  }
  return `${year}${String(month - 1).padStart(2, '0')}`;
}

/**
 * 获取下一个月份
 */
export function getNextPeriod(period) {
  const year = parseInt(period.substring(0, 4));
  const month = parseInt(period.substring(4, 6));
  if (month === 12) {
    return `${year + 1}01`;
  }
  return `${year}${String(month + 1).padStart(2, '0')}`;
}
