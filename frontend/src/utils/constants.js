/**
 * Shared UI style mappings for task priority and status badges.
 */
export const PRIORITY_STYLES = {
    default: 'priority-low',
    '紧急': 'priority-medium',
    '非常紧急': 'priority-high',
};

export const STATUS_STYLES = {
    default: 'bg-gray-100 text-gray-800',
    '进行中': 'bg-blue-100 text-blue-800',
    '已结束': 'bg-green-100 text-green-800',
    '已取消': 'bg-red-100 text-red-800',
    '已关闭': 'bg-gray-100 text-gray-800',
};

/**
 * Resolve the CSS class for a given priority; falls back to `default` when unknown.
 */
export const getPriorityStyle = (priority) => PRIORITY_STYLES[priority] || PRIORITY_STYLES.default;

/**
 * Resolve the CSS class for a given status; falls back to `default` when unknown.
 */
export const getStatusStyle = (status) => STATUS_STYLES[status] || STATUS_STYLES.default;
