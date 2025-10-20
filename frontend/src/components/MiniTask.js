import { getPriorityStyle } from '../utils/constants';

/**
 * Compact task pill rendered inside the month calendar cells.
 * @param {Object} props Component props.
 * @param {Object} props.task Task metadata for display.
 * @param {string} props.task.task_name Task title.
 * @param {string} props.task.assignee Responsible person.
 * @param {string} props.task.priority Task priority label.
 * @param {number} [props.maxLength=15] Maximum characters before truncating the title.
 */
export default function MiniTask({ task, maxLength = 15 }) {
    if (!task) {
        return null;
    }

    const { task_name, assignee, priority } = task;
    const truncatedName = task_name && task_name.length > maxLength
        ? `${task_name.substring(0, maxLength)}...`
        : task_name;
    const tooltip = `${task_name}\n负责人: ${assignee || '未分配'}\n优先级: ${priority || '普通'}`;
    const priorityClass = getPriorityStyle(priority);

    return (
        <div className={`mini-task ${priorityClass}`.trim()} title={tooltip}>
            {truncatedName}
        </div>
    );
}
