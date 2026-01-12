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

    const { task_name, creator_name, creator_label, assignee, priority, status, restricted } = task;
    const priorityClass = getPriorityStyle(priority);
    const statusClass = getStatusStyle(status);
    const showPriorityBadge = !restricted && (priority === '紧急' || priority === '非常紧急');
    // 使用任务的 creator_label，如果没有则默认为"提交"
    const displayLabel = creator_label || '提交';

    if (restricted) {
        return (
            <div className="task-card bg-white border border-gray-200 rounded p-3 md:p-4 min-h-[72px] cursor-pointer hover:shadow transition-shadow">
                <h3 className="font-medium text-sm md:text-base text-gray-800 mb-1">{assignee || '工程师'}</h3>
                <p className="text-xs md:text-sm text-gray-500">{status || '已安排派工'}</p>
                <p className="text-xs text-gray-400 mt-1">详细信息需相关人员查看</p>
            </div>
        );
    }

    return (
        <div className="task-card bg-white border border-gray-200 rounded p-3 md:p-4 min-h-[88px] cursor-pointer hover:shadow-lg transition-shadow">
            <h3 className="font-medium text-sm md:text-base text-gray-800 line-clamp-2 mb-2">{task_name}</h3>
            <div className="mt-2 text-xs md:text-sm space-y-1">
                {/* 提交人/厂家对接人 */}
                <div className="text-gray-600 flex items-center">
                    <i className="fas fa-user-circle mr-1 text-xs md:text-sm flex-shrink-0" />
                    <span className="text-gray-500 flex-shrink-0">{displayLabel}:</span>
                    <span className="ml-1 text-gray-700 truncate">{creator_name || '未知'}</span>
                </div>
                {/* 执行人 */}
                <div className="text-gray-600 flex items-center">
                    <i className="fas fa-user-cog mr-1 text-xs md:text-sm flex-shrink-0" />
                    <span className="text-gray-500 flex-shrink-0">执行:</span>
                    <span className="ml-1 text-gray-700 truncate">{assignee || '未分配'}</span>
                </div>
                {/* 优先级和状态 */}
                <div className="flex flex-wrap items-center gap-1 mt-1">
                    {showPriorityBadge && (
                        <span className={`${priorityClass} px-2 py-1 rounded-full text-xs`}>
                            {priority}
                        </span>
                    )}
                    <span className={`${statusClass} px-2 py-1 rounded-full text-xs`}>
                        {status || '待处理'}
                    </span>
                </div>
            </div>
        </div>
    );
}
