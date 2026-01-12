const BACKEND_BASE_URL = (process.env.REACT_APP_BACKEND_BASE_URL || '').replace(/\/$/, '');

// 🔒 安全修复: 移除硬编码API Key
// 前端专用端点不需要API Key (如 /api/tasks, /api/engineers)
// 管理操作端点通过session认证 (如 /api/sync, /api/approvals)

// Export for use in hooks
export const API_BASE_URL = BACKEND_BASE_URL;

/**
 * Build API URL with base path handling
 */
function buildApiUrl(path) {
    const basePath = BACKEND_BASE_URL || '';
    if (!basePath) {
        return path;
    }
    return `${basePath}${path}`;
}

/**
 * Fetch tasks from the backend with an optional date range filter.
 */
export async function fetchTasks(startDate, endDate) {
    let url = buildApiUrl('/api/tasks');

    if (startDate && endDate) {
        url += `?start_date=${startDate}&end_date=${endDate}`;
    }

    const response = await fetch(url, {
        credentials: 'include',
    });

    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
}

/**
 * Trigger manual data sync from Feishu
 * 🔒 使用session认证，不需要API Key
 */
export async function syncFromFeishu() {
    const url = buildApiUrl('/api/sync');

    const response = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        credentials: 'include',  // 包含session cookie
    });

    if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Sync failed');
    }

    return response.json();
}

async function parseJsonResponse(response) {
    let data = null;
    const contentType = response.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
        data = await response.json();
    }

    if (!response.ok) {
        const fallbackMessage = `HTTP error! status: ${response.status}`;
        const detail = data && (data.detail || data.message);
        throw new Error(detail || fallbackMessage);
    }

    return data;
}

export async function fetchApprovalTypes() {
    const url = buildApiUrl('/api/approvals/types');
    const response = await fetch(url, {
        credentials: 'include',
    });

    const data = await parseJsonResponse(response);
    return data && Array.isArray(data.approval_types) ? data.approval_types : [];
}

export async function createDispatch(approvalType, formData) {
    const url = buildApiUrl('/api/approvals');
    const payload = {
        approval_type: approvalType,
        ...formData,
    };

    const response = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify(payload),
    });

    return parseJsonResponse(response);
}

export async function updateDispatch(instanceCode, formData) {
    const url = buildApiUrl(`/api/approvals/${encodeURIComponent(instanceCode)}`);

    const response = await fetch(url, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify(formData),
    });

    return parseJsonResponse(response);
}

export async function transferDispatch(instanceCode, newAssignee, reason) {
    const url = buildApiUrl(`/api/approvals/${encodeURIComponent(instanceCode)}/transfer`);
    const payload = {
        new_assignee: newAssignee,
    };
    if (reason) {
        payload.reason = reason;
    }

    const response = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify(payload),
    });

    return parseJsonResponse(response);
}

export async function closeDispatch(instanceCode, reason) {
    const url = buildApiUrl(`/api/approvals/${encodeURIComponent(instanceCode)}`);
    const payload = {};
    if (reason) {
        payload.reason = reason;
    }

    const response = await fetch(url, {
        method: 'DELETE',
        headers: {
            'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify(payload),
    });

    return parseJsonResponse(response);
}

export async function completeDispatch(instanceCode, completionNote) {
    const url = buildApiUrl(`/api/approvals/${encodeURIComponent(instanceCode)}/complete`);
    const payload = {};
    if (completionNote) {
        payload.completion_note = completionNote;
    }

    const response = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify(payload),
    });

    return parseJsonResponse(response);
}

export async function fetchApprovalDetail(instanceCode) {
    const url = buildApiUrl(`/api/approvals/${encodeURIComponent(instanceCode)}`);
    const response = await fetch(url, {
        credentials: 'include',
    });

    return parseJsonResponse(response);
}

// ==============================
// Dispatch order related APIs
// ==============================

function buildQueryString(params = {}) {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
        if (value === undefined || value === null || value === '') {
            return;
        }
        query.append(key, value);
    });
    const queryString = query.toString();
    return queryString ? `?${queryString}` : '';
}

// 获取派工单列表
export async function fetchDispatchOrders(params = {}) {
    const queryString = buildQueryString(params);
    const url = buildApiUrl(`/api/dispatch/orders${queryString}`);

    const response = await fetch(url, {
        credentials: 'include',
    });

    return parseJsonResponse(response);
}

// 获取派工单详情
export async function fetchDispatchOrderDetail(sourceId) {
    if (!sourceId) {
        throw new Error('sourceId is required');
    }

    const url = buildApiUrl(`/api/dispatch/orders/${encodeURIComponent(sourceId)}`);
    const response = await fetch(url, {
        credentials: 'include',
    });

    return parseJsonResponse(response);
}

// 获取派工单统计
export async function fetchDispatchStats() {
    const url = buildApiUrl('/api/dispatch/stats');
    const response = await fetch(url, {
        credentials: 'include',
    });

    return parseJsonResponse(response);
}

// 同步派工单数据
export async function syncDispatchOrders() {
    const url = buildApiUrl('/api/sync/dispatch');
    const response = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        credentials: 'include',
    });

    return parseJsonResponse(response);
}

// 获取日期范围内的派工单（用于周视图）
export async function fetchDispatchOrdersByDateRange(startDate, endDate) {
    // 将日期字符串转换为毫秒时间戳
    // startDate: 当天 00:00:00, endDate: 当天 23:59:59.999
    const startTime = startDate ? new Date(`${startDate}T00:00:00`).getTime() : undefined;
    const endTime = endDate ? new Date(`${endDate}T23:59:59.999`).getTime() : undefined;

    const params = {
        start_time: startTime,
        end_time: endTime,
        page_size: 100, // API最大支持100条
    };
    const queryString = buildQueryString(params);
    const url = buildApiUrl(`/api/dispatch/orders${queryString}`);

    const response = await fetch(url, {
        credentials: 'include',
    });

    const result = await parseJsonResponse(response);

    // 调试日志
    return result;
}
