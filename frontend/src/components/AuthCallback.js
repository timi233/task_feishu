/**
 * OAuth回调处理组件
 *
 * 处理Identity Hub的OAuth回调，显示加载状态
 */

import React, { useEffect, useState } from 'react';
import './AuthCallback.css';

const AuthCallback = () => {
  const [status, setStatus] = useState('processing');
  const [message, setMessage] = useState('正在处理登录...');

  useEffect(() => {
    // 检查URL参数
    const urlParams = new URLSearchParams(window.location.search);
    const error = urlParams.get('error');

    if (error) {
      setStatus('error');
      setMessage(`登录失败: ${error}`);

      // 3秒后跳转回首页
      setTimeout(() => {
        window.location.href = '/';
      }, 3000);
    } else {
      // OAuth回调会由后端处理并自动重定向
      // 如果3秒后还在这个页面，说明可能有问题
      setTimeout(() => {
        if (status === 'processing') {
          setStatus('error');
          setMessage('登录超时，正在重定向...');

          setTimeout(() => {
            window.location.href = '/';
          }, 2000);
        }
      }, 3000);
    }
  }, [status]);

  return (
    <div className="auth-callback-container">
      <div className="auth-callback-card">
        {status === 'processing' && (
          <>
            <div className="spinner"></div>
            <p className="message">{message}</p>
          </>
        )}

        {status === 'error' && (
          <>
            <div className="error-icon">❌</div>
            <p className="message error">{message}</p>
          </>
        )}
      </div>
    </div>
  );
};

export default AuthCallback;
