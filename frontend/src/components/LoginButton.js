/**
 * Login button component with Feishu and local fallback login.
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
  const [showLocalLogin, setShowLocalLogin] = useState(false);
  const [localUsername, setLocalUsername] = useState('admin');
  const [localPassword, setLocalPassword] = useState('');
  const [localLoginLoading, setLocalLoginLoading] = useState(false);
  const [localLoginError, setLocalLoginError] = useState('');

  const persistUserInfo = (data) => {
    if (data.authenticated && data.user_id) {
      localStorage.setItem('userInfo', JSON.stringify({
        user_id: data.user_id,
        name: data.user_name,
        email: data.user_email,
        permissions: data.permissions || [],
        roles: data.roles || []
      }));
    } else {
      localStorage.removeItem('userInfo');
    }
  };

  const checkAuthStatus = async () => {
    try {
      const response = await fetch('/auth/status', {
        credentials: 'include'
      });

      if (response.ok) {
        const data = await response.json();
        setAuthStatus(data);
        persistUserInfo(data);
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

  const handleLogin = () => {
    const returnUrl = encodeURIComponent(window.location.pathname);
    window.location.href = `/auth/login?return_url=${returnUrl}`;
  };

  const handleLocalLogin = async (event) => {
    event.preventDefault();
    setLocalLoginError('');
    setLocalLoginLoading(true);

    try {
      const response = await fetch('/auth/local-login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ username: localUsername, password: localPassword })
      });

      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.detail || 'Local login failed');
      }

      setAuthStatus(data);
      persistUserInfo(data);
      setShowLocalLogin(false);
      setLocalPassword('');
      window.location.reload();
    } catch (error) {
      setLocalLoginError(error.message || 'Local login failed');
    } finally {
      setLocalLoginLoading(false);
    }
  };

  const handleLogout = async () => {
    try {
      const response = await fetch('/auth/logout', {
        method: 'POST',
        credentials: 'include'
      });

      if (response.ok) {
        localStorage.removeItem('userInfo');

        setAuthStatus({
          authenticated: false,
          user_name: null,
          identity_hub_available: authStatus.identity_hub_available
        });

        window.location.reload();
      }
    } catch (error) {
      console.error('Logout failed:', error);
      alert('Logout failed, please try again');
    }
  };

  if (loading) {
    return (
      <div className="login-button-container">
        <span className="loading-text">Loading...</span>
      </div>
    );
  }

  if (authStatus.authenticated) {
    return (
      <div className="login-button-container">
        <span className="user-name">{authStatus.user_name}</span>
        <button onClick={handleLogout} className="logout-button">
          Logout
        </button>
      </div>
    );
  }

  return (
    <div className="login-button-container local-login-wrapper">
      {authStatus.identity_hub_available && (
        <button onClick={handleLogin} className="login-button">
          Feishu Login
        </button>
      )}
      <button
        type="button"
        onClick={() => setShowLocalLogin((value) => !value)}
        className="local-login-toggle"
      >
        Local Login
      </button>

      {showLocalLogin && (
        <form className="local-login-panel" onSubmit={handleLocalLogin}>
          <input
            type="text"
            value={localUsername}
            onChange={(event) => setLocalUsername(event.target.value)}
            placeholder="Username"
            autoComplete="username"
          />
          <input
            type="password"
            value={localPassword}
            onChange={(event) => setLocalPassword(event.target.value)}
            placeholder="Password"
            autoComplete="current-password"
          />
          {localLoginError && <div className="local-login-error">{localLoginError}</div>}
          <button type="submit" disabled={localLoginLoading} className="local-login-submit">
            {localLoginLoading ? 'Logging in...' : 'Login'}
          </button>
        </form>
      )}
    </div>
  );
};

export default LoginButton;
