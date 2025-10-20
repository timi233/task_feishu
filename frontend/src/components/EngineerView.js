import TaskCard from './TaskCard';

/**
 * Engineer-centric week view displaying tasks in a table layout.
 * Rows represent engineers, columns represent weekdays (Monday through Friday).
 * @param {Object} props Component props.
 * @param {Object} props.engineerData Map of engineer names to their weekly tasks.
 */
export default function EngineerView({ engineerData }) {
    if (!engineerData || typeof engineerData !== 'object') {
        return null;
    }

    const engineers = Object.keys(engineerData).sort();
    const weekdays = [
        { key: 'monday', label: '周一', headerClassName: 'bg-blue-600' },
        { key: 'tuesday', label: '周二', headerClassName: 'bg-blue-700' },
        { key: 'wednesday', label: '周三', headerClassName: 'bg-blue-800' },
        { key: 'thursday', label: '周四', headerClassName: 'bg-blue-900' },
        { key: 'friday', label: '周五', headerClassName: 'bg-indigo-900' },
    ];

    if (engineers.length === 0) {
        return (
            <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
                当前时间段内没有任务数据
            </div>
        );
    }

    return (
        <div className="overflow-x-auto mb-8">
            <table className="min-w-full bg-white rounded-lg shadow">
                <thead>
                    <tr>
                        <th className="bg-gray-700 text-white px-4 py-3 text-left sticky left-0 z-10">
                            <i className="fas fa-user mr-2" />
                            工程师
                        </th>
                        {weekdays.map((day) => (
                            <th
                                key={day.key}
                                className={`${day.headerClassName} text-white px-4 py-3 text-center min-w-[200px]`}
                            >
                                <i className="fas fa-calendar-day mr-2" />
                                {day.label}
                            </th>
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {engineers.map((engineer, engineerIndex) => (
                        <tr
                            key={engineer}
                            className={engineerIndex % 2 === 0 ? 'bg-gray-50' : 'bg-white'}
                        >
                            <td className="px-4 py-3 font-medium text-gray-800 border-r sticky left-0 z-10 bg-inherit">
                                {engineer}
                            </td>
                            {weekdays.map((day) => {
                                const dayTasks = Array.isArray(engineerData[engineer]?.[day.key])
                                    ? engineerData[engineer][day.key]
                                    : [];

                                return (
                                    <td
                                        key={day.key}
                                        className="px-4 py-3 align-top border-l"
                                    >
                                        {dayTasks.length > 0 ? (
                                            <div className="space-y-2">
                                                {dayTasks.map((task, taskIndex) => (
                                                    <TaskCard
                                                        key={task.record_id || `${engineer}-${day.key}-${taskIndex}`}
                                                        task={task}
                                                    />
                                                ))}
                                            </div>
                                        ) : (
                                            <div className="text-center text-gray-400 text-sm">-</div>
                                        )}
                                    </td>
                                );
                            })}
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
