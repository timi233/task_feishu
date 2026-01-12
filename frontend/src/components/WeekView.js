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
        <>
            <div className="hidden md:grid md:grid-cols-5 gap-4 mb-8">
                {days.slice(0, 5).map((day, index) => (
                    <DayColumn
                        key={day.id || day.label || index}
                        label={day.label}
                        headerClassName={day.headerClassName}
                        tasks={day.tasks}
                    />
                ))}
            </div>
            <div className="md:hidden mb-8 -mx-4 px-4">
                <div className="flex overflow-x-auto gap-3 pb-3 snap-x snap-mandatory" style={{ scrollSnapType: 'x mandatory' }}>
                    {days.slice(0, 5).map((day, index) => (
                        <div key={day.id || day.label || index} className="flex-shrink-0 w-[85vw] snap-center">
                            <DayColumn
                                label={day.label}
                                headerClassName={day.headerClassName}
                                tasks={day.tasks}
                            />
                        </div>
                    ))}
                </div>
            </div>
        </>
    );
}
