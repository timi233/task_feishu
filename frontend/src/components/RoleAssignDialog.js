/**
 * 角色分配对话框组件
 *
 * 功能：
 * - 显示用户当前角色
 * - 允许系统管理员分配新角色
 * - 允许系统管理员撤销已有角色
 *
 * 日期: 2025-11-03
 * 阶段: Phase 4.2 - 角色管理UI
 */

import React, { useState, useEffect } from 'react';
import './RoleAssignDialog.css';

const RoleAssignDialog = ({ user, onClose, onRoleChange }) => {
  const [availableRoles, setAvailableRoles] = useState([]);
  const [selectedRole, setSelectedRole] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState('');

  // 加载可用角色列表
  useEffect(() => {
    fetchRoles();
  }, []);

  const fetchRoles = async () => {
    try {
      const response = await fetch('/api/roles', {
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error('获取角色列表失败');
      }

      const data = await response.json();
      setAvailableRoles(data);
    } catch (err) {
      setError(err.message);
    }
  };

  // 分配角色
  const handleAssignRole = async () => {
    if (!selectedRole) {
      setError('请选择要分配的角色');
      return;
    }

    setLoading(true);
    setError(null);
    setSuccessMessage('');

    try {
      const response = await fetch(
        `/api/users/${user.user_id}/roles`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          credentials: 'include',
          body: JSON.stringify({
            role_id: parseInt(selectedRole),
          }),
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '分配角色失败');
      }

      const result = await response.json();
      setSuccessMessage(result.message);
      setSelectedRole('');

      // 通知父组件更新用户列表
      if (onRoleChange) {
        onRoleChange();
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // 撤销角色
  const handleRevokeRole = async (roleId) => {
    if (!window.confirm('确定要撤销该角色吗？')) {
      return;
    }

    setLoading(true);
    setError(null);
    setSuccessMessage('');

    try {
      const response = await fetch(
        `/api/users/${user.user_id}/roles/${roleId}`,
        {
          method: 'DELETE',
          credentials: 'include',
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '撤销角色失败');
      }

      const result = await response.json();
      setSuccessMessage(result.message);

      // 通知父组件更新用户列表
      if (onRoleChange) {
        onRoleChange();
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // 获取用户未拥有的角色
  const getUnassignedRoles = () => {
    if (!user || !user.roles) return availableRoles;

    const userRoleIds = user.roles.map(r => r.role_id);
    return availableRoles.filter(role => !userRoleIds.includes(role.id));
  };

  const unassignedRoles = getUnassignedRoles();

  return (
    <div className="role-assign-dialog-overlay">
      <div className="role-assign-dialog">
        <div className="dialog-header">
          <h2>角色管理 - {user.name || user.user_id}</h2>
          <button className="close-button" onClick={onClose}>×</button>
        </div>

        <div className="dialog-body">
          {/* 用户信息 */}
          <div className="user-info">
            <p><strong>用户ID:</strong> {user.user_id}</p>
            <p><strong>姓名:</strong> {user.name || '未知'}</p>
            <p><strong>邮箱:</strong> {user.email || '未知'}</p>
          </div>

          {/* 当前角色列表 */}
          <div className="current-roles">
            <h3>当前角色</h3>
            {user.roles && user.roles.length > 0 ? (
              <div className="role-list">
                {user.roles.map(role => (
                  <div key={role.role_id} className="role-item">
                    <div className="role-info">
                      <span className="role-name">{role.role_name}</span>
                      <span className="role-scope">({role.data_scope})</span>
                    </div>
                    <button
                      className="revoke-button"
                      onClick={() => handleRevokeRole(role.role_id)}
                      disabled={loading}
                    >
                      撤销
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <p className="no-roles">暂无角色</p>
            )}
          </div>

          {/* 分配新角色 */}
          <div className="assign-role">
            <h3>分配新角色</h3>
            {unassignedRoles.length > 0 ? (
              <div className="assign-form">
                <select
                  value={selectedRole}
                  onChange={(e) => setSelectedRole(e.target.value)}
                  disabled={loading}
                >
                  <option value="">-- 选择角色 --</option>
                  {unassignedRoles.map(role => (
                    <option key={role.id} value={role.id}>
                      {role.role_name} ({role.data_scope})
                    </option>
                  ))}
                </select>
                <button
                  className="assign-button"
                  onClick={handleAssignRole}
                  disabled={loading || !selectedRole}
                >
                  {loading ? '处理中...' : '分配角色'}
                </button>
              </div>
            ) : (
              <p className="no-roles">该用户已拥有所有可用角色</p>
            )}
          </div>

          {/* 消息提示 */}
          {error && (
            <div className="error-message">
              <span className="error-icon">⚠️</span>
              {error}
            </div>
          )}
          {successMessage && (
            <div className="success-message">
              <span className="success-icon">✓</span>
              {successMessage}
            </div>
          )}
        </div>

        <div className="dialog-footer">
          <button className="close-button-secondary" onClick={onClose}>
            关闭
          </button>
        </div>
      </div>
    </div>
  );
};

export default RoleAssignDialog;
