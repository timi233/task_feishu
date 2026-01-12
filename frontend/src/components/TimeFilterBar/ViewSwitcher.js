/**
 * Toggle buttons allowing the user to switch between week and month views.
 * @param {Object} props Component props.
 * @param {'week'|'month'} props.currentView Active view identifier.
 * @param {Function} props.onChange Handler invoked with the next view key.
 */
export default function ViewSwitcher({ currentView, onChange }) {
    const baseClass =
        'view-btn px-3 md:px-4 py-2 rounded-lg font-medium transition-all flex items-center gap-1 md:gap-2 text-sm md:text-base';

    return (
        <div className="flex items-center gap-2">
            <button
                type="button"
                className={`${baseClass} ${currentView === 'week' ? 'active' : ''}`.trim()}
                onClick={() => onChange('week')}
            >
                <i className="fas fa-calendar-week" />
                <span className="hidden sm:inline">周视图</span>
                <span className="sm:hidden">周</span>
            </button>
            <button
                type="button"
                className={`${baseClass} ${currentView === 'month' ? 'active' : ''}`.trim()}
                onClick={() => onChange('month')}
            >
                <i className="fas fa-calendar-alt" />
                <span className="hidden sm:inline">月视图</span>
                <span className="sm:hidden">月</span>
            </button>
        </div>
    );
}
