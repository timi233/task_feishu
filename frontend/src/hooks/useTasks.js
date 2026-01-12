import { useState, useCallback } from 'react';
import { fetchDispatchOrdersByDateRange } from '../utils/api';
import { groupDispatchOrdersByWeekday } from '../utils/taskUtils';
import { applyTaskPrivacy } from '../utils/privacy';

/**
 * Manage task data retrieval state for the dashboard views.
 * 只获取新派工单数据源。
 */
export default function useTasks() {
    const [tasks, setTasks] = useState({});
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const fetchTasks = useCallback(async (startDate, endDate) => {
        setLoading(true);
        setError(null);

        try {
            // 只获取新派工单数据
            const dispatchResponse = await fetchDispatchOrdersByDateRange(startDate, endDate);

            // 提取派工单列表
            const dispatchOrders = dispatchResponse?.data || [];

            // 将派工单转换为任务格式并按星期分组，并根据权限脱敏
            const groupedTasks = groupDispatchOrdersByWeekday(dispatchOrders);
            const sanitizedTasks = applyTaskPrivacy(groupedTasks);

            setTasks(sanitizedTasks);
            return sanitizedTasks;
        } catch (err) {
            setError(err);
            throw err;
        } finally {
            setLoading(false);
        }
    }, []);

    return { tasks, loading, error, fetchTasks };
}
