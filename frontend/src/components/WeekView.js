import DayColumn from './DayColumn';

/**
 * Week-based grid layout highlighting Monday through Friday columns.
 * @param {Object} props Component props.
 * @param {Array<Object>} props.days Ordered collection of week day descriptors.
 */
export default function WeekView({ days }) {
    if (!Array.isArray(days) || days.length === 0) {
        return null;
    }

    return (
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-8">
            {days.slice(0, 5).map((day, index) => (
                <DayColumn
                    key={day.id || day.label || index}
                    label={day.label}
                    headerClassName={day.headerClassName}
                    tasks={day.tasks}
                />
            ))}
        </div>
    );
}
