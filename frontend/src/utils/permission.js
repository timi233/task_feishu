/**
 * 权限工具函数
 *
 * 提供前端权限检查功能，支持：
 * - 从本地存储获取用户权限
 * - 检查单个权限
 * - 检查权限组合（AND/OR）
 * - 权限控制组件和路由
 *
 * 使用方式:
 *   import { hasPermission, hasAnyPermission, withPermission } from '../utils/permission';
 *
 *   // 条件渲染
 *   {hasPermission('task:create') && <button>新建派工</button>}
 *
 *   // 高阶组件
 *   const ProtectedButton = withPermission(Button, 'task:delete');
 *
 * 日期: 2025-10-31
 * 阶段: Phase 4.5 - 权限体系集成
 */

// ============================================
// 权限获取函数
// ============================================

/**
 * 从localStorage获取用户权限列表
 * @returns {Array<string>} 权限列表
 */
export function getUserPermissions() {
  try {
    const userInfo = JSON.parse(localStorage.getItem('userInfo') || '{}');
    return userInfo.permissions || [];
  } catch (error) {
    console.warn('Failed to get user permissions:', error);
    return [];
  }
}

/**
 * 从localStorage获取用户角色列表
 * @returns {Array<string>} 角色列表
 */
export function getUserRoles() {
  try {
    const userInfo = JSON.parse(localStorage.getItem('userInfo') || '{}');
    return userInfo.roles || [];
  } catch (error) {
    console.warn('Failed to get user roles:', error);
    return [];
  }
}

/**
 * 检查用户是否已登录
 * @returns {boolean} 是否已登录
 */
export function isAuthenticated() {
  try {
    const userInfo = JSON.parse(localStorage.getItem('userInfo') || '{}');
    return !!(userInfo && userInfo.user_id);
  } catch (error) {
    return false;
  }
}

/**
 * 获取当前用户信息
 * @returns {Object|null} 用户信息
 */
export function getCurrentUser() {
  try {
    return JSON.parse(localStorage.getItem('userInfo') || '{}');
  } catch (error) {
    console.warn('Failed to get current user:', error);
    return null;
  }
}

// ============================================
// 权限检查函数
// ============================================

/**
 * 检查是否有指定权限
 * @param {string} permission - 权限字符串，格式: "resource:action"
 * @returns {boolean} 是否有权限
 */
export function hasPermission(permission) {
  if (!permission) {
    console.warn('Permission is empty');
    return false;
  }

  const permissions = getUserPermissions();
  const hasPerm = permissions.includes(permission);

  // 开发环境日志
  if (process.env.NODE_ENV === 'development') {
    console.debug(`Permission check: ${permission} = ${hasPerm}`);
  }

  return hasPerm;
}

/**
 * 检查是否有任一权限
 * @param {Array<string>} permissionList - 权限列表
 * @returns {boolean} 是否有任一权限
 */
export function hasAnyPermission(permissionList) {
  if (!Array.isArray(permissionList) || permissionList.length === 0) {
    return false;
  }

  const permissions = getUserPermissions();
  const hasAny = permissionList.some(p => permissions.includes(p));

  if (process.env.NODE_ENV === 'development') {
    console.debug(`Any permission check: [${permissionList.join(', ')}] = ${hasAny}`);
  }

  return hasAny;
}

/**
 * 检查是否拥有所有权限
 * @param {Array<string>} permissionList - 权限列表
 * @returns {boolean} 是否拥有所有权限
 */
export function hasAllPermissions(permissionList) {
  if (!Array.isArray(permissionList) || permissionList.length === 0) {
    return false;
  }

  const permissions = getUserPermissions();
  const hasAll = permissionList.every(p => permissions.includes(p));

  if (process.env.NODE_ENV === 'development') {
    console.debug(`All permissions check: [${permissionList.join(', ')}] = ${hasAll}`);
  }

  return hasAll;
}

/**
 * 检查是否有指定角色
 * @param {string} role - 角色名称
 * @returns {boolean} 是否有角色
 */
export function hasRole(role) {
  if (!role) {
    return false;
  }

  const roles = getUserRoles();
  const hasRole = roles.some(r => {
    if (typeof r === 'string') {
      return r === role;
    } else if (typeof r === 'object' && r !== null) {
      return r.role_name === role || r.role_key === role;
    }
    return false;
  });

  if (process.env.NODE_ENV === 'development') {
    console.debug(`Role check: ${role} = ${hasRole}`);
  }

  return hasRole;
}

/**
 * 检查是否是系统管理员
 * @returns {boolean} 是否是系统管理员
 */
export function isSystemAdmin() {
  return hasRole('system_admin') || hasRole('系统管理员') || hasRole('admin');
}

// ============================================
// 权限控制高阶组件
// ============================================

/**
 * 权限控制高阶组件
 * @param {React.Component} Component - 要包装的组件
 * @param {string|Array<string>} requiredPermission - 需要的权限
 * @param {string} permissionType - 权限类型: 'any' | 'all'，默认 'any'
 * @returns {React.Component} 包装后的组件
 */
export function withPermission(Component, requiredPermission, permissionType = 'any') {
  function PermissionWrapper({ ...props }) {
    let hasRequiredPermission = false;

    if (typeof requiredPermission === 'string') {
      hasRequiredPermission = hasPermission(requiredPermission);
    } else if (Array.isArray(requiredPermission)) {
      hasRequiredPermission = permissionType === 'all'
        ? hasAllPermissions(requiredPermission)
        : hasAnyPermission(requiredPermission);
    }

    if (!hasRequiredPermission) {
      return (
        <div style={{
          opacity: 0.5,
          padding: '8px',
          border: '1px dashed #ccc',
          borderRadius: '4px',
          textAlign: 'center',
          color: '#666'
        }}>
          权限不足
        </div>
      );
    }

    return <Component {...props} />;
  }

  PermissionWrapper.displayName = `withPermission(${Component.displayName || Component.name})`;

  return PermissionWrapper;
}

// ============================================
// 权限控制Hook
// ============================================

/**
 * 权限检查Hook
 * @returns {Object} 权限检查函数集合
 */
export function usePermission() {
  return {
    hasPermission,
    hasAnyPermission,
    hasAllPermissions,
    hasRole,
    isSystemAdmin,
    isAuthenticated,
    getCurrentUser,
    getUserPermissions,
    getUserRoles
  };
}

// ============================================
// 常用权限检查函数
// ============================================

/**
 * 检查是否有派工创建权限
 */
export function canCreateTask() {
  return hasPermission('task:create');
}

/**
 * 检查是否有派工读取权限
 */
export function canReadTask() {
  return hasAnyPermission(['task:read', 'task:create', 'task:update', 'task:delete']);
}

/**
 * 检查是否有派工更新权限
 */
export function canUpdateTask() {
  return hasPermission('task:update');
}

/**
 * 检查是否有派工删除权限
 */
export function canDeleteTask() {
  return hasPermission('task:delete');
}

/**
 * 检查是否有审批管理权限
 */
export function canManageApproval() {
  return hasAnyPermission(['approval:create', 'approval:read', 'approval:update', 'approval:delete']);
}

/**
 * 检查是否有用户管理权限
 */
export function canManageUser() {
  return hasAnyPermission(['user:create', 'user:read', 'user:update', 'user:delete']);
}

/**
 * 检查是否有角色分配权限（系统管理员）
 */
export function canAssignRole() {
  return hasPermission('role:assign');
}

// ============================================
// 权限相关常量
// ============================================

export const PERMISSIONS = {
  // 任务权限
  TASK_CREATE: 'task:create',
  TASK_READ: 'task:read',
  TASK_UPDATE: 'task:update',
  TASK_DELETE: 'task:delete',

  // 审批权限
  APPROVAL_CREATE: 'approval:create',
  APPROVAL_READ: 'approval:read',
  APPROVAL_UPDATE: 'approval:update',
  APPROVAL_DELETE: 'approval:delete',

  // 用户权限
  USER_CREATE: 'user:create',
  USER_READ: 'user:read',
  USER_UPDATE: 'user:update',
  USER_DELETE: 'user:delete',

  // 系统权限
  SYSTEM_ADMIN: 'system:admin',
  SYSTEM_CONFIG: 'system:config'
};

export const ROLES = {
  ADMIN: '系统管理员',
  MANAGER: '部门经理',
  ENGINEER: '工程师',
  VIEWER: '查看者'
};

// ============================================
// 开发工具函数
// ============================================

/**
 * 打印当前用户权限信息（仅开发环境）
 */
export function debugPermissions() {
  if (process.env.NODE_ENV === 'development') {
    const user = getCurrentUser();
    const permissions = getUserPermissions();
    const roles = getUserRoles();

    console.group('🔐 用户权限信息');
    console.log('用户:', user);
    console.log('权限:', permissions);
    console.log('角色:', roles);

    console.group('📋 权限检查结果');
    console.log('创建派工:', canCreateTask());
    console.log('读取派工:', canReadTask());
    console.log('更新派工:', canUpdateTask());
    console.log('删除派工:', canDeleteTask());
    console.log('系统管理员:', isSystemAdmin());
    console.groupEnd();

    console.groupEnd();
  }
}

/**
 * 模拟用户权限（仅开发环境测试用）
 * @param {Object} mockUser - 模拟用户信息
 */
export function setMockUser(mockUser) {
  if (process.env.NODE_ENV === 'development') {
    const defaultPermissions = [
      PERMISSIONS.TASK_READ,
      PERMISSIONS.TASK_CREATE,
      PERMISSIONS.TASK_UPDATE
    ];

    const user = {
      user_id: 'mock-user-id',
      name: mockUser.name || '测试用户',
      email: mockUser.email || 'test@example.com',
      permissions: mockUser.permissions || defaultPermissions,
      roles: mockUser.roles || [{ role_name: '测试角色' }]
    };

    localStorage.setItem('userInfo', JSON.stringify(user));
    console.log('🔧 设置模拟用户:', user);
  }
}

export default {
  // 权限获取
  getUserPermissions,
  getUserRoles,
  isAuthenticated,
  getCurrentUser,

  // 权限检查
  hasPermission,
  hasAnyPermission,
  hasAllPermissions,
  hasRole,
  isSystemAdmin,

  // 高阶组件
  withPermission,

  // Hook
  usePermission,

  // 常用函数
  canCreateTask,
  canReadTask,
  canUpdateTask,
  canDeleteTask,
  canManageApproval,
  canManageUser,

  // 常量
  PERMISSIONS,
  ROLES,

  // 开发工具
  debugPermissions,
  setMockUser
};