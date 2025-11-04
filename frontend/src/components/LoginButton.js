/**
 * 登录按钮组件
 *
 * 根据用户登录状态显示"登录"或用户信息+登出按钮
 */

import React, { useState, useEffect } from 'react';
import './LoginButton.css';

const LoginButton = () => {
  const [authStatus, setAuthStatus] = useState({
    authenticated: false,
    user_name: null,
    identity_hub_available: false
  });
  const [loading, setLoading] = useState(true);

  // 检查认证状态
  const checkAuthStatus = async () => {
    try {
      const response = await fetch('/auth/status', {
        credentials: 'include'  // 包含cookie
      });

      if (response.ok) {
        const data = await response.json();
        setAuthStatus(data);

        // 如果已认证，保存用户信息到localStorage（供权限检查使用）
        if (data.authenticated && data.user_id) {
          localStorage.setItem('userInfo', JSON.stringify({
            user_id: data.user_id,
            name: data.user_name,
            email: data.user_email,
            permissions: data.permissions || [],
            roles: data.roles || []
          }));
        } else {
          // 未认证时清除localStorage
          localStorage.removeItem('userInfo');
        }
      }
    } catch (error) {
      console.error('Failed to check auth status:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkAuthStatus();
  }, []);

  // 登录处理
  const handleLogin = () => {
    // 跳转到后端登录端点（window.location.href不会被proxy拦截，需要使用完整URL）
    const returnUrl = encodeURIComponent(window.location.pathname);
    const backendUrl = process.env.REACT_APP_BACKEND_URL || 'http://10.242.94.9:8081';
    window.location.href = `${backendUrl}/auth/login?return_url=${returnUrl}`;
  };

  // 登出处理
  const handleLogout = async () => {
    try {
      const response = await fetch('/auth/logout', {
        method: 'POST',
        credentials: 'include'
      });

      if (response.ok) {
        // 清除localStorage中的用户信息
        localStorage.removeItem('userInfo');

        setAuthStatus({
          authenticated: false,
          user_name: null,
          identity_hub_available: authStatus.identity_hub_available
        });

        // 刷新页面以清除所有状态
        window.location.reload();
      }
    } catch (error) {
      console.error('Logout failed:', error);
      alert('登出失败，请重试');
    }
  };

  if (loading) {
    return (
      <div className="login-button-container">
        <span className="loading-text">加载中...</span>
      </div>
    );
  }

  if (!authStatus.identity_hub_available) {
    return null; // 如果Identity Hub不可用，不显示登录按钮
  }

  if (authStatus.authenticated) {
    return (
      <div className="login-button-container">
        <span className="user-name">👤 {authStatus.user_name}</span>
        <button onClick={handleLogout} className="logout-button">
          登出
        </button>
      </div>
    );
  }

  return (
    <div className="login-button-container">
      <button onClick={handleLogin} className="login-button">
        登录
      </button>
    </div>
  );
};

export default LoginButton;
