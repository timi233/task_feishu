import CalendarDay from './CalendarDay';

const WEEKDAY_LABELS = ['日', '一', '二', '三', '四', '五', '六'];

/**
 * Month calendar grid showing 42 days (7 columns x 6 rows).
 * @param {Object} props Component props.
 * @param {Array<Object>} props.days Sequential collection of day data objects.
 */
export default function MonthView({ days }) {
    if (!Array.isArray(days) || days.length === 0) {
        return null;
    }

    return (
        <div className="bg-white rounded-lg shadow overflow-hidden mb-8">
            <div className="month-calendar">
                {WEEKDAY_LABELS.map((label) => (
                    <div key={label} className="calendar-day-header">
                        {label}
                    </div>
                ))}
            </div>
            <div className="month-calendar">
                {days.slice(0, 42).map((day, index) => (
                    <CalendarDay
                        key={day.date || index}
                        date={day.date}
                        isCurrentMonth={day.isCurrentMonth}
                        isToday={day.isToday}
                        tasks={day.tasks}
                    />
                ))}
            </div>
        </div>
    );
}
