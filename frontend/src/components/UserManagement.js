/**
 * 用户管理页面
 *
 * 功能：
 * - 显示所有用户及其角色
 * - 允许系统管理员分配/撤销用户角色
 * - 搜索和筛选用户
 * - 权限控制：仅系统管理员可访问
 *
 * 日期: 2025-11-03
 * 阶段: Phase 4.3 - 用户管理页面
 */

import React, { useState, useEffect } from 'react';
import { canAssignRole } from '../utils/permission';
import RoleAssignDialog from './RoleAssignDialog';
import './UserManagement.css';

const UserManagement = () => {
  const [users, setUsers] = useState([]);
  const [filteredUsers, setFilteredUsers] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedUser, setSelectedUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showDialog, setShowDialog] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState(null);

  // 权限检查
  const hasPermission = canAssignRole();

  // 加载用户列表
  useEffect(() => {
    if (hasPermission) {
      fetchUsers();
    }
  }, [hasPermission]);

  // 搜索过滤
  useEffect(() => {
    if (!searchTerm.trim()) {
      setFilteredUsers(users);
      return;
    }

    const term = searchTerm.toLowerCase();
    const filtered = users.filter(user => {
      const nameMatch = user.name?.toLowerCase().includes(term);
      const emailMatch = user.email?.toLowerCase().includes(term);
      const userIdMatch = user.user_id?.toLowerCase().includes(term);
      const roleMatch = user.roles.some(role =>
        role.role_name.toLowerCase().includes(term)
      );

      return nameMatch || emailMatch || userIdMatch || roleMatch;
    });

    setFilteredUsers(filtered);
  }, [searchTerm, users]);

  const fetchUsers = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/users', {
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error('获取用户列表失败');
      }

      const data = await response.json();
      setUsers(data);
      setFilteredUsers(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleManageRoles = (user) => {
    setSelectedUser(user);
    setShowDialog(true);
  };

  const handleCloseDialog = () => {
    setShowDialog(false);
    setSelectedUser(null);
  };

  const handleRoleChange = () => {
    // 重新加载用户列表以反映更改
    fetchUsers();
  };

  const handleSyncUsers = async (source) => {
    setSyncing(true);
    setSyncMessage(null);

    try {
      const endpoint = source === 'identity-hub'
        ? '/api/users/sync/identity-hub'
        : '/api/users/sync/feishu';

      const response = await fetch(endpoint, {
        method: 'POST',
        credentials: 'include',
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '同步失败');
      }

      const result = await response.json();

      setSyncMessage({
        type: 'success',
        text: result.message,
      });

      // 重新加载用户列表
      fetchUsers();
    } catch (err) {
      setSyncMessage({
        type: 'error',
        text: err.message,
      });
    } finally {
      setSyncing(false);
      // 3秒后自动清除消息
      setTimeout(() => setSyncMessage(null), 3000);
    }
  };

  const handleCleanupDuplicates = async () => {
    if (!window.confirm('确定要清理重复用户吗？\n\n将删除所有临时用户和Identity Hub用户，只保留从飞书同步的用户。')) {
      return;
    }

    setSyncing(true);
    setSyncMessage(null);

    try {
      const response = await fetch('/api/users/sync/cleanup', {
        method: 'POST',
        credentials: 'include',
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '清理失败');
      }

      const result = await response.json();

      setSyncMessage({
        type: 'success',
        text: result.message,
      });

      // 重新加载用户列表
      fetchUsers();
    } catch (err) {
      setSyncMessage({
        type: 'error',
        text: err.message,
      });
    } finally {
      setSyncing(false);
      // 3秒后自动清除消息
      setTimeout(() => setSyncMessage(null), 3000);
    }
  };

  // 获取角色徽章的样式类
  const getRoleBadgeClass = (roleKey) => {
    switch (roleKey) {
      case 'system_admin':
        return 'role-badge admin';
      case 'manager':
        return 'role-badge manager';
      case 'regular':
        return 'role-badge regular';
      default:
        return 'role-badge';
    }
  };

  // 无权限访问
  if (!hasPermission) {
    return (
      <div className="user-management-container">
        <div className="permission-denied">
          <div className="permission-denied-icon">🔒</div>
          <h2>权限不足</h2>
          <p>您没有访问用户管理页面的权限</p>
          <p>仅系统管理员可以访问此页面</p>
        </div>
      </div>
    );
  }

  return (
    <div className="user-management-container">
      <div className="user-management-header">
        <div className="header-content">
          <h1>用户管理</h1>
          <p className="header-description">管理系统用户的角色和权限</p>
        </div>
        <div className="header-actions">
          <button
            className="sync-button"
            onClick={() => handleSyncUsers('feishu')}
            disabled={syncing}
            title="从飞书组织架构同步所有用户（遍历所有部门）"
          >
            {syncing ? '同步中...' : '同步飞书组织架构'}
          </button>
          <button
            className="sync-button"
            onClick={handleCleanupDuplicates}
            disabled={syncing}
            title="清理重复用户，只保留飞书同步的用户"
            style={{ backgroundColor: '#ff9800' }}
          >
            {syncing ? '清理中...' : '清理重复数据'}
          </button>
          <button className="refresh-button" onClick={fetchUsers} disabled={loading}>
            {loading ? '加载中...' : '刷新'}
          </button>
        </div>
      </div>

      <div className="search-section">
        <input
          type="text"
          placeholder="搜索用户（姓名、邮箱、ID或角色）"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="search-input"
        />
        <div className="search-stats">
          找到 {filteredUsers.length} 个用户 {searchTerm && `（共 ${users.length} 个）`}
        </div>
      </div>

      {syncMessage && (
        <div className={syncMessage.type === 'success' ? 'success-banner' : 'error-banner'}>
          <span className={syncMessage.type === 'success' ? 'success-icon' : 'error-icon'}>
            {syncMessage.type === 'success' ? '✓' : '⚠️'}
          </span>
          <span>{syncMessage.text}</span>
        </div>
      )}

      {error && (
        <div className="error-banner">
          <span className="error-icon">⚠️</span>
          <span>{error}</span>
          <button onClick={fetchUsers} className="retry-button">重试</button>
        </div>
      )}

      {loading ? (
        <div className="loading-state">
          <div className="loading-spinner"></div>
          <p>加载用户列表...</p>
        </div>
      ) : (
        <div className="users-table-container">
          <table className="users-table">
            <thead>
              <tr>
                <th>用户ID</th>
                <th>姓名</th>
                <th>邮箱</th>
                <th>角色</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {filteredUsers.length > 0 ? (
                filteredUsers.map(user => (
                  <tr key={user.user_id}>
                    <td className="user-id-cell">{user.user_id}</td>
                    <td className="user-name-cell">{user.name || '未知'}</td>
                    <td className="user-email-cell">{user.email || '未知'}</td>
                    <td className="user-roles-cell">
                      {user.roles && user.roles.length > 0 ? (
                        <div className="role-badges">
                          {user.roles.map(role => (
                            <span
                              key={role.role_id}
                              className={getRoleBadgeClass(role.role_key)}
                              title={`数据范围: ${role.data_scope}`}
                            >
                              {role.role_name}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span className="no-role">暂无角色</span>
                      )}
                    </td>
                    <td className="actions-cell">
                      <button
                        className="manage-button"
                        onClick={() => handleManageRoles(user)}
                      >
                        管理角色
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="5" className="no-data-cell">
                    {searchTerm ? '未找到匹配的用户' : '暂无用户数据'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {showDialog && selectedUser && (
        <RoleAssignDialog
          user={selectedUser}
          onClose={handleCloseDialog}
          onRoleChange={handleRoleChange}
        />
      )}
    </div>
  );
};

export default UserManagement;
