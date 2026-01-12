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

    const { task_name, assignee, priority, restricted } = task;
    const truncatedName = task_name && task_name.length > maxLength
        ? `${task_name.substring(0, maxLength)}...`
        : task_name;
    const tooltip = restricted
        ? `${assignee || '工程师'}\n已安排派工`
        : `${task_name}\n负责人: ${assignee || '未分配'}\n优先级: ${priority || '普通'}`;
    const priorityClass = restricted ? 'restricted' : getPriorityStyle(priority);

    return (
        <div
            className={`mini-task ${priorityClass} text-[10px] md:text-xs p-1 md:p-1.5`.trim()}
            title={tooltip}
        >
            {restricted ? (assignee || '工程师') : truncatedName}
        </div>
    );
}
