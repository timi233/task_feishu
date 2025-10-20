import { getPriorityStyle, getStatusStyle } from '../utils/constants';

/**
 * Detailed task card used in the week view.
 * @param {Object} props Component props.
 * @param {Object} props.task Task metadata for display.
 * @param {string} props.task.task_name Task title.
 * @param {string} props.task.assignee Responsible person.
 * @param {string} props.task.priority Task priority label.
 * @param {string} props.task.status Task status label.
 */
export default function TaskCard({ task }) {
    if (!task) {
        return null;
    }

    const { task_name, assignee, priority, status } = task;
    const priorityClass = getPriorityStyle(priority);
    const statusClass = getStatusStyle(status);

    return (
        <div className="task-card bg-white border border-gray-200 rounded p-3">
            <h3 className="font-medium text-gray-800">{task_name}</h3>
            <div className="flex items-center mt-2 text-sm">
                <span className="text-gray-500 mr-3">
                    <i className="fas fa-user mr-1" />
                    {assignee || '未分配'}
                </span>
                <span className={`${priorityClass} px-2 py-1 rounded-full text-xs mr-2`}>
                    {priority || '普通'}
                </span>
                <span className={`${statusClass} px-2 py-1 rounded-full text-xs`}>
                    {status || '待处理'}
                </span>
            </div>
        </div>
    );
}
