import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { title: '登录' }
  },
  {
    path: '/',
    component: () => import('../views/Layout.vue'),
    redirect: '/employees',
    children: [
      {
        path: 'employees',
        name: 'Employees',
        component: () => import('../views/employees/EmployeeList.vue'),
        meta: { title: '档案管理' }
      },
      {
        path: 'attendance',
        name: 'Attendance',
        component: () => import('../views/attendance/AttendanceList.vue'),
        meta: { title: '考勤管理' }
      },
      {
        path: 'performance',
        name: 'Performance',
        component: () => import('../views/performance/PerformanceList.vue'),
        meta: { title: '绩效管理' }
      },
      {
        path: 'salary',
        name: 'Salary',
        component: () => import('../views/salary/SalaryCalc.vue'),
        meta: { title: '薪资核算' }
      },
      {
        path: 'approval',
        name: 'Approval',
        component: () => import('../views/approval/ApprovalList.vue'),
        meta: { title: '审批流程' }
      },
      {
        path: 'insurance',
        name: 'Insurance',
        component: () => import('../views/insurance/SocialInsuranceList.vue'),
        meta: { title: '社保公积金' }
      },
      {
        path: 'reports',
        name: 'Reports',
        component: () => import('../views/reports/ReportCenter.vue'),
        meta: { title: '报表导出' }
      },
      {
        path: 'profile',
        name: 'Profile',
        component: () => import('../views/Profile.vue'),
        meta: { title: '个人中心' }
      },
      {
        path: 'system/users',
        name: 'SystemUsers',
        component: () => import('../views/system/UserManagement.vue'),
        meta: { title: '用户管理' }
      },
      {
        path: 'system/roles',
        name: 'SystemRoles',
        component: () => import('../views/system/RoleManagement.vue'),
        meta: { title: '角色管理' }
      },
      {
        path: 'system/dict',
        name: 'SystemDict',
        component: () => import('../views/system/DictManagement.vue'),
        meta: { title: '数据字典' }
      },
      {
        path: 'system/logs',
        name: 'SystemLogs',
        component: () => import('../views/system/LogViewer.vue'),
        meta: { title: '操作日志' }
      },
      {
        path: 'system/backup',
        name: 'SystemBackup',
        component: () => import('../views/system/BackupManagement.vue'),
        meta: { title: '数据备份' }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  if (to.path !== '/login' && !token) {
    next('/login')
  } else {
    next()
  }
})

export default router