import { useState, useEffect, useCallback } from 'react';
import { API_BASE_URL } from '../utils/api';

/**
 * useEngineers Hook
 *
 * 从后端API获取工程师列表并缓存到state
 *
 * 返回:
 * - engineers: 工程师列表 [{user_id, name}]
 * - loading: 加载状态
 * - error: 错误信息
 * - reload: 重新加载函数
 */
export default function useEngineers() {
    const [engineers, setEngineers] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const loadEngineers = useCallback(async () => {
        setLoading(true);
        setError(null);

        try {
            const response = await fetch(`${API_BASE_URL}/api/engineers`, {
                headers: {
                    'Content-Type': 'application/json',
                },
            });

            if (!response.ok) {
                throw new Error(`Failed to fetch engineers: ${response.statusText}`);
            }

            const data = await response.json();
            setEngineers(data.engineers || []);
        } catch (err) {
            setError(err.message || 'Failed to load engineers');
            console.error('Error loading engineers:', err);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        loadEngineers();
    }, [loadEngineers]);

    return {
        engineers,
        loading,
        error,
        reload: loadEngineers,
    };
}
