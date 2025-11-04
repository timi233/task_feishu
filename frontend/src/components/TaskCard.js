import { getPriorityStyle, getStatusStyle } from '../utils/constants';

/**
 * Detailed task card used in the week view.
 * @param {Object} props Component props.
 * @param {Object} props.task Task metadata for display.
 * @param {string} props.task.task_name Task title.
 * @param {string} props.task.creator_name Task creator/submitter.
 * @param {string} props.task.assignee Responsible person/engineer.
 * @param {string} props.task.priority Task priority label.
 * @param {string} props.task.status Task status label.
 */
export default function TaskCard({ task }) {
    if (!task) {
        return null;
    }

    const { task_name, creator_name, assignee, priority, status } = task;
    const priorityClass = getPriorityStyle(priority);
    const statusClass = getStatusStyle(status);

    return (
        <div className="task-card bg-white border border-gray-200 rounded p-3">
            <h3 className="font-medium text-gray-800">{task_name}</h3>
            <div className="mt-2 text-sm space-y-1">
                {/* 提交人 */}
                <div className="text-gray-600">
                    <i className="fas fa-user-circle mr-1" />
                    <span className="text-gray-500">提交人:</span>
                    <span className="ml-1 text-gray-700">{creator_name || '未知'}</span>
                </div>
                {/* 执行人 */}
                <div className="text-gray-600">
                    <i className="fas fa-user-cog mr-1" />
                    <span className="text-gray-500">执行人:</span>
                    <span className="ml-1 text-gray-700">{assignee || '未分配'}</span>
                </div>
                {/* 优先级和状态 */}
                <div className="flex items-center mt-1">
                    <span className={`${priorityClass} px-2 py-1 rounded-full text-xs mr-2`}>
                        {priority || '普通'}
                    </span>
                    <span className={`${statusClass} px-2 py-1 rounded-full text-xs`}>
                        {status || '待处理'}
                    </span>
                </div>
            </div>
        </div>
    );
}
