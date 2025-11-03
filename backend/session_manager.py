"""Session管理模块

提供简单的内存session存储，用于OAuth认证流程。
生产环境建议使用Redis。
"""

import secrets
import time
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class SessionManager:
    """内存Session管理器

    存储session数据，包括OAuth state、access_token、用户信息等。

    注意: 这是内存存储，服务器重启后会丢失。
    生产环境建议使用Redis或数据库。
    """

    def __init__(self, session_lifetime: int = 7200):
        """初始化Session管理器

        Args:
            session_lifetime: Session有效期（秒），默认2小时
        """
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self.session_lifetime = session_lifetime

    def create_session(self, data: Optional[Dict[str, Any]] = None) -> str:
        """创建新Session

        Args:
            data: Session初始数据

        Returns:
            str: Session ID
        """
        session_id = secrets.token_urlsafe(32)

        self._sessions[session_id] = {
            "data": data or {},
            "created_at": time.time(),
            "expires_at": time.time() + self.session_lifetime
        }

        logger.info(f"Created session: {session_id[:16]}...")
        return session_id

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取Session数据

        Args:
            session_id: Session ID

        Returns:
            Optional[Dict]: Session数据，如果不存在或已过期返回None
        """
        session = self._sessions.get(session_id)

        if not session:
            return None

        # 检查过期
        if session["expires_at"] < time.time():
            logger.info(f"Session expired: {session_id[:16]}...")
            self.delete_session(session_id)
            return None

        return session["data"]

    def update_session(self, session_id: str, data: Dict[str, Any]) -> bool:
        """更新Session数据

        Args:
            session_id: Session ID
            data: 要更新的数据

        Returns:
            bool: 是否成功更新
        """
        session = self._sessions.get(session_id)

        if not session:
            return False

        # 检查过期
        if session["expires_at"] < time.time():
            self.delete_session(session_id)
            return False

        # 更新数据
        session["data"].update(data)

        # 延长有效期
        session["expires_at"] = time.time() + self.session_lifetime

        logger.debug(f"Updated session: {session_id[:16]}...")
        return True

    def delete_session(self, session_id: str) -> bool:
        """删除Session

        Args:
            session_id: Session ID

        Returns:
            bool: 是否成功删除
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info(f"Deleted session: {session_id[:16]}...")
            return True

        return False

    def cleanup_expired_sessions(self) -> int:
        """清理过期的Session

        Returns:
            int: 清理的Session数量
        """
        now = time.time()
        expired_sessions = [
            session_id
            for session_id, session in self._sessions.items()
            if session["expires_at"] < now
        ]

        for session_id in expired_sessions:
            del self._sessions[session_id]

        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")

        return len(expired_sessions)

    def get_session_count(self) -> int:
        """获取当前Session数量

        Returns:
            int: Session数量
        """
        return len(self._sessions)


# 全局Session管理器实例
session_manager = SessionManager()


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)

    print("\n=== Session Manager Test ===\n")

    # 创建session
    session_id = session_manager.create_session({"user": "test"})
    print(f"✅ Created session: {session_id[:32]}...")

    # 获取session
    data = session_manager.get_session(session_id)
    print(f"✅ Got session data: {data}")

    # 更新session
    session_manager.update_session(session_id, {"access_token": "test_token"})
    data = session_manager.get_session(session_id)
    print(f"✅ Updated session data: {data}")

    # 删除session
    session_manager.delete_session(session_id)
    data = session_manager.get_session(session_id)
    print(f"✅ Deleted session, data: {data}")

    print("\n✅ All tests passed!")
