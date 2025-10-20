/**
 * Toggle buttons allowing the user to switch between week and month views.
 * @param {Object} props Component props.
 * @param {'week'|'month'} props.currentView Active view identifier.
 * @param {Function} props.onChange Handler invoked with the next view key.
 */
export default function ViewSwitcher({ currentView, onChange }) {
    const baseClass = 'view-btn px-4 py-2 rounded-lg font-medium transition-all';

    return (
        <div className="flex items-center gap-2">
            <button
                type="button"
                className={`${baseClass} ${currentView === 'week' ? 'active' : ''}`.trim()}
                onClick={() => onChange('week')}
            >
                <i className="fas fa-calendar-week mr-2" />
                周视图
            </button>
            <button
                type="button"
                className={`${baseClass} ${currentView === 'month' ? 'active' : ''}`.trim()}
                onClick={() => onChange('month')}
            >
                <i className="fas fa-calendar-alt mr-2" />
                月视图
            </button>
        </div>
    );
}
