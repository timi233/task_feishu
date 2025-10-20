const BACKEND_BASE_URL = (process.env.REACT_APP_BACKEND_BASE_URL || '').replace(/\/$/, '');

/**
 * Fetch tasks from the backend with an optional date range filter.
 */
export async function fetchTasks(startDate, endDate) {
    const basePath = BACKEND_BASE_URL || '';
    let url = `${basePath}/api/tasks`;

    if (!basePath) {
        url = '/api/tasks';
    }

    if (startDate && endDate) {
        url += `?start_date=${startDate}&end_date=${endDate}`;
    }

    const response = await fetch(url);

    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
}
