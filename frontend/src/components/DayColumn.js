import TaskCard from './TaskCard';

/**
 * Column wrapper for a weekday in the week view grid.
 * @param {Object} props Component props.
 * @param {string} props.label Display name for the day header.
 * @param {string} [props.headerClassName='bg-blue-600'] Additional classes applied to the header background.
 * @param {Array<Object>} [props.tasks=[]] Tasks scheduled for the day.
 */
export default function DayColumn({ label, headerClassName = 'bg-blue-600', tasks = [] }) {
    const safeTasks = Array.isArray(tasks) ? tasks : [];

    return (
        <div className="bg-white rounded-lg shadow overflow-hidden">
            <div className={`day-header ${headerClassName} text-white px-4 py-3`.trim()}>
                <h2 className="font-bold text-lg flex items-center">
                    <i className="fas fa-calendar-day mr-2" />
                    {label}
                </h2>
            </div>
            <div className="p-4 space-y-3">
                {safeTasks.map((task, index) => (
                    <TaskCard key={task.id || `${label}-${index}`} task={task} />
                ))}
            </div>
        </div>
    );
}
