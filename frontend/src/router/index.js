import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { MENU_PERMISSION_MAP } from '../utils/permission'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { title: '登录', public: true }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('../views/Register.vue'),
    meta: { title: '注册', public: true }
  },
  {
    path: '/',
    component: () => import('../views/Layout.vue'),
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('../views/Dashboard.vue'),
        meta: { title: '工作台', perm: 'dashboard:view' }
      },
      {
        path: 'employees',
        name: 'Employees',
        component: () => import('../views/employees/EmployeeList.vue'),
        meta: { title: '档案管理', perm: 'employee:view' }
      },
      {
        path: 'attendance',
        name: 'Attendance',
        component: () => import('../views/attendance/AttendanceList.vue'),
        meta: { title: '考勤管理', perm: 'attendance:view' }
      },
      {
        path: 'performance',
        name: 'Performance',
        component: () => import('../views/performance/PerformanceList.vue'),
        meta: { title: '绩效评分', perm: 'performance:view' }
      },
      {
        path: 'insurance',
        name: 'Insurance',
        component: () => import('../views/insurance/SocialInsuranceList.vue'),
        meta: { title: '社保公积金', perm: 'insurance:view' }
      },
      {
        path: 'insurance-template',
        name: 'InsuranceTemplate',
        component: () => import('../views/insurance/TemplateConfig.vue'),
        meta: { title: '导入模板', perm: 'insurance:template' }
      },
      {
        path: 'salary',
        name: 'Salary',
        component: () => import('../views/salary/SalaryCalc.vue'),
        meta: { title: '薪资计算', perm: 'salary:view' }
      },
      {
        path: 'approval',
        name: 'Approval',
        component: () => import('../views/approval/ApprovalList.vue'),
        meta: { title: '审批流程', perm: 'approval:view' }
      },
      {
        path: 'reports',
        name: 'Reports',
        component: () => import('../views/reports/ReportCenter.vue'),
        meta: { title: '报表导出', perm: 'report:view' }
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
        meta: { title: '用户管理', perm: 'system:user' }
      },
      {
        path: 'system/roles',
        name: 'SystemRoles',
        component: () => import('../views/system/RoleManagement.vue'),
        meta: { title: '角色管理', perm: 'system:role' }
      },
      {
        path: 'system/dict',
        name: 'SystemDict',
        component: () => import('../views/system/DictManagement.vue'),
        meta: { title: '数据字典', perm: 'system:dict' }
      },
      {
        path: 'system/logs',
        name: 'SystemLogs',
        component: () => import('../views/system/LogViewer.vue'),
        meta: { title: '操作日志', perm: 'system:log' }
      },
      {
        path: 'system/backup',
        name: 'SystemBackup',
        component: () => import('../views/system/BackupManagement.vue'),
        meta: { title: '数据备份', perm: 'system:backup' }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory('/e9salary/'),
  routes
})

function findFirstAccessibleRoute(authStore) {
  if (authStore.hasPermission('dashboard:view')) {
    return '/dashboard'
  }
  return '/profile'
}

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')

  if (to.path === '/login' || to.path === '/register') {
    if (token) {
      const authStore = useAuthStore()
      next(findFirstAccessibleRoute(authStore))
    } else {
      next()
    }
    return
  }

  if (!token) {
    next('/login')
    return
  }

  const authStore = useAuthStore()
  const requiredPerm = to.meta?.perm

  if (to.path === '/' || to.path === '') {
    next(findFirstAccessibleRoute(authStore))
    return
  }

  if (requiredPerm && !authStore.hasPermission(requiredPerm)) {
    const targetPath = findFirstAccessibleRoute(authStore)
    if (to.path === targetPath) {
      next()
    } else {
      next(targetPath)
    }
    return
  }

  next()
})

export default router