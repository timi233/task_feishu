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
    '公司外勤派单': 'bg-blue-50 text-blue-700 border border-blue-200',
    '厂家外勤派单': 'bg-purple-50 text-purple-700 border border-purple-200',
};

/**
 * Resolve the CSS class for a given priority; falls back to `default` when unknown.
 */
export const getPriorityStyle = (priority) => PRIORITY_STYLES[priority] || PRIORITY_STYLES.default;

/**
 * Resolve the CSS class for a given status; falls back to `default` when unknown.
 */
export const getStatusStyle = (status) => STATUS_STYLES[status] || STATUS_STYLES.default;
