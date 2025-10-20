import { useState, useCallback } from 'react';
import { fetchTasks as fetchTasksApi } from '../utils/api';

/**
 * Manage task data retrieval state for the dashboard views.
 */
export default function useTasks() {
    const [tasks, setTasks] = useState({});
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const fetchTasks = useCallback(async (startDate, endDate) => {
        setLoading(true);
        setError(null);

        try {
            const data = await fetchTasksApi(startDate, endDate);
            setTasks(data);
            return data;
        } catch (err) {
            setError(err);
            throw err;
        } finally {
            setLoading(false);
        }
    }, []);

    return { tasks, loading, error, fetchTasks };
}
