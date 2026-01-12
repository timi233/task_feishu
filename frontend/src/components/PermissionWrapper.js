/**
 * 权限控制组件
 *
 * 提供基于权限的组件渲染控制。
 *
 * 使用方式:
 *   // 条件渲染组件
 *   <PermissionWrapper permission="task:create">
 *     <Button>新建派工</Button>
 *   </PermissionWrapper>
 *
 *   // 多权限条件
 *   <PermissionWrapper permissions={["task:update", "task:delete"]} mode="any">
 *     <DropdownMenu>
 *       <MenuItem>修改</MenuItem>
 *       <MenuItem>删除</MenuItem>
 *     </DropdownMenu>
 *   </PermissionWrapper>
 *
 *   // 基于角色的渲染
 *   <PermissionWrapper role="系统管理员">
 *     <AdminPanel />
 *   </PermissionWrapper>
 *
 * 日期: 2025-10-31
 * 阶段: Phase 4.5 - 权限体系集成
 */

import React from 'react';
import {
  hasPermission,
  hasAnyPermission,
  hasAllPermissions,
  hasRole,
  isAuthenticated
} from '../utils/permission';

/**
 * 权限包装组件
 * @param {Object} props
 * @param {string|Array<string>} props.permission - 单个权限或权限列表
 * @param {string} props.mode - 权限模式: 'any' | 'all'，默认 'any'
 * @param {string} props.role - 角色名称（与权限互斥）
 * @param {boolean} props.fallback - 是否显示fallback内容，默认 true
 * @param {React.ReactNode} props.children - 子组件
 * @param {React.ReactNode} props.fallbackComponent - 自定义fallback组件
 * @param {string} props.fallbackMessage - 自定义fallback消息
 */
export function PermissionWrapper({
  permission = null,
  permissions = null,
  mode = 'any',
  role = null,
  fallback = true,
  children,
  fallbackComponent = null,
  fallbackMessage = '权限不足'
}) {
  // 检查是否已登录
  if (!isAuthenticated()) {
    if (!fallback) return null;
    return fallbackComponent || (
      <div style={{
        padding: '8px',
        textAlign: 'center',
        color: '#666',
        border: '1px dashed #ddd',
        borderRadius: '4px',
        backgroundColor: '#f9f9f9'
      }}>
        请先登录
      </div>
    );
  }

  // 检查权限
  let hasRequiredPermission = false;

  if (role) {
    // 基于角色的检查
    hasRequiredPermission = hasRole(role);
  } else if (permission || permissions) {
    // 基于权限的检查
    const permList = permission || permissions;

    if (typeof permList === 'string') {
      hasRequiredPermission = hasPermission(permList);
    } else if (Array.isArray(permList)) {
      hasRequiredPermission = mode === 'all'
        ? hasAllPermissions(permList)
        : hasAnyPermission(permList);
    }
  } else {
    // 没有权限要求，直接显示
    hasRequiredPermission = true;
  }

  // 权限验证通过，显示子组件
  if (hasRequiredPermission) {
    return <>{children}</>;
  }

  // 权限不足，显示fallback
  if (!fallback) return null;

  if (fallbackComponent) {
    return <>{fallbackComponent}</>;
  }

  // 默认fallback样式
  return (
    <div style={{
      padding: '8px',
      textAlign: 'center',
      color: '#666',
      border: '1px dashed #ddd',
      borderRadius: '4px',
      backgroundColor: '#f9f9f9',
      fontSize: '14px'
    }}>
      {fallbackMessage}
    </div>
  );
}

/**
 * 条件渲染Hook
 * @param {string|Array<string>} permission - 权限要求
 * @param {string} mode - 权限模式
 * @returns {Object} 渲染控制对象
 */
export function usePermissionRender(permission, mode = 'any') {
  const show = typeof permission === 'string'
    ? hasPermission(permission)
    : Array.isArray(permission)
      ? mode === 'all'
        ? hasAllPermissions(permission)
        : hasAnyPermission(permission)
      : true;

  return {
    show,
    render: (content, fallback = null) => show ? content : fallback,
    className: show ? '' : 'permission-hidden'
  };
}

/**
 * 按钮权限控制组件
 */
export function PermissionButton({
  permission,
  permissions,
  mode = 'any',
  children,
  disabled = false,
  disabledMessage = '权限不足',
  fallback,
  ...props
}) {
  const hasPermission = permission || permissions
    ? typeof permission === 'string'
      ? hasPermission(permission)
      : Array.isArray(permission || permissions)
        ? mode === 'all'
          ? hasAllPermissions(permission || permissions)
          : hasAnyPermission(permission || permissions)
        : true
    : true;

  if (!hasPermission && !fallback) {
    return null;
  }

  if (!hasPermission && fallback) {
    return <>{fallback}</>;
  }

  return (
    <button
      {...props}
      disabled={disabled || !hasPermission}
      title={!hasPermission ? disabledMessage : props.title}
      style={{
        ...props.style,
        opacity: hasPermission ? (disabled ? 0.6 : 1) : 0.4,
        cursor: (disabled || !hasPermission) ? 'not-allowed' : 'pointer'
      }}
    >
      {children}
    </button>
  );
}

/**
 * 菜单项权限控制组件
 */
export function PermissionMenuItem({
  permission,
  permissions,
  mode = 'any',
  children,
  fallback,
  ...props
}) {
  const hasPermission = permission || permissions
    ? typeof permission === 'string'
      ? hasPermission(permission)
      : Array.isArray(permission || permissions)
        ? mode === 'all'
          ? hasAllPermissions(permission || permissions)
          : hasAnyPermission(permission || permissions)
        : true
    : true;

  if (!hasPermission && !fallback) {
    return null;
  }

  if (!hasPermission && fallback) {
    return <>{fallback}</>;
  }

  return <div {...props}>{children}</div>;
}

/**
 * 路由权限控制组件
 */
export function PermissionRoute({
  permission,
  permissions,
  mode = 'any',
  component: Component,
  fallbackComponent,
  ...props
}) {
  const hasRequiredPermission = permission || permissions
    ? typeof permission === 'string'
      ? hasPermission(permission)
      : Array.isArray(permission || permissions)
        ? mode === 'all'
          ? hasAllPermissions(permission || permissions)
          : hasAnyPermission(permission || permissions)
        : true
    : true;

  if (!hasRequiredPermission) {
    if (fallbackComponent) {
      return <fallbackComponent />;
    }

    return (
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '200px',
        padding: '20px',
        textAlign: 'center'
      }}>
        <h3 style={{ color: '#666', marginBottom: '16px' }}>访问受限</h3>
        <p style={{ color: '#999' }}>您没有访问此页面的权限</p>
      </div>
    );
  }

  return <Component {...props} />;
}

/**
 * 面包屑权限控制组件
 */
export function PermissionBreadcrumbItem({
  permission,
  permissions,
  mode = 'any',
  children,
  fallback,
  ...props
}) {
  const hasPermission = permission || permissions
    ? typeof permission === 'string'
      ? hasPermission(permission)
      : Array.isArray(permission || permissions)
        ? mode === 'all'
          ? hasAllPermissions(permission || permissions)
          : hasAnyPermission(permission || permissions)
        : true
    : true;

  if (!hasPermission && !fallback) {
    return null;
  }

  if (!hasPermission && fallback) {
    return <>{fallback}</>;
  }

  return <div {...props}>{children}</div>;
}

// 样式定义
export const styles = {
  permissionHidden: {
    display: 'none !important'
  },
  fallbackMessage: {
    padding: '8px 12px',
    backgroundColor: '#f5f5f5',
    border: '1px dashed #ddd',
    borderRadius: '4px',
    color: '#666',
    fontSize: '12px',
    textAlign: 'center'
  }
};

export default {
  PermissionWrapper,
  usePermissionRender,
  PermissionButton,
  PermissionMenuItem,
  PermissionRoute,
  PermissionBreadcrumbItem,
  styles
};