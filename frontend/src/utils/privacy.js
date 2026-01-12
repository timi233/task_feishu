import { getCurrentUser, hasAnyPermission, isSystemAdmin } from './permission';

const DETAIL_PERMISSIONS = [
    'tasks:view_details',
    'tasks:view_all_details',
    'dispatch:admin'
];

function getCurrentUserName() {
    const user = getCurrentUser();
    return user?.name || user?.user_name || null;
}

export function canViewTaskDetails(task) {
    if (isSystemAdmin()) return true;
    if (hasAnyPermission(DETAIL_PERMISSIONS)) return true;

    const currentUserName = getCurrentUserName();
    if (!currentUserName) {
        return false;
    }

    if (task?.assignee && task.assignee.includes(currentUserName)) {
        return true;
    }

    if (task?.creator_name && task.creator_name.includes(currentUserName)) {
        return true;
    }

    return false;
}

function sanitizeTask(task) {
    const isFieldDispatch = task?.source_table === 'field_dispatch';
    let engineerName = task?.assignee || task?.creator_name || '已占用';
    if (isFieldDispatch && task?.creator_name) {
        engineerName = task.creator_name;
    }
    const dispatchLabel = task?.status || task?.dispatch_category || '已分派';

    return {
        ...task,
        restricted: true,
        assignee: engineerName,
        task_name: engineerName,
        creator_label: '工程师',
        creator_name: engineerName,
        priority: null,
        approval_status: undefined,
        status: dispatchLabel,
    };
}

export function applyTaskPrivacy(tasksByDay) {
    const sanitized = {};
    const dayKeys = Object.keys(tasksByDay || {});

    dayKeys.forEach((dayKey) => {
        const dayTasks = Array.isArray(tasksByDay[dayKey]) ? tasksByDay[dayKey] : [];
        sanitized[dayKey] = dayTasks.map((task) => (
            canViewTaskDetails(task)
                ? { ...task, restricted: false }
                : sanitizeTask(task)
        ));
    });

    return sanitized;
}
