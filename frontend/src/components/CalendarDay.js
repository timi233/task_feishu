import MiniTask from './MiniTask';

/**
 * Single day cell within the month calendar grid.
 * @param {Object} props Component props.
 * @param {string|Date} props.date Date represented by the cell.
 * @param {boolean} props.isCurrentMonth Whether the date belongs to the active month.
 * @param {boolean} props.isToday Highlight flag for the current day.
 * @param {Array<Object>} [props.tasks=[]] Tasks falling on this date.
 */
export default function CalendarDay({ date, isCurrentMonth, isToday, tasks = [] }) {
    const containerClasses = ['calendar-day'];
    if (!isCurrentMonth) {
        containerClasses.push('other-month');
    }
    if (isToday) {
        containerClasses.push('today');
    }

    const dayDate = date ? new Date(date) : null;
    const dayNumber = dayDate ? dayDate.getDate() : '';
    const safeTasks = Array.isArray(tasks) ? tasks : [];
    const visibleTasks = safeTasks.slice(0, 3);
    const remaining = safeTasks.length - visibleTasks.length;

    const containerClassName = [...containerClasses, 'p-1 md:p-2 min-h-[80px] md:min-h-[120px]'].join(' ');

    return (
        <div className={containerClassName}>
            <div className="day-number text-xs md:text-sm">{dayNumber}</div>
            {visibleTasks.map((task, index) => (
                <MiniTask key={task.id || `${date}-${index}`} task={task} />
            ))}
            {remaining > 0 && (
                <div className="text-[10px] md:text-xs text-gray-500 mt-1">+{remaining} 更多</div>
            )}
        </div>
    );
}
