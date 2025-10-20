import ViewSwitcher from './ViewSwitcher';
import DateNavigation from './DateNavigation';

/**
 * Wrapper combining view switcher and date navigation controls.
 * @param {Object} props Component props sourced from the time filter hook.
 * @param {'week'|'month'} props.currentView Active calendar view.
 * @param {Function} props.setView Setter for the active view.
 * @param {Function} props.navigatePrev Handler for moving to the previous period.
 * @param {Function} props.navigateNext Handler for moving to the next period.
 * @param {Function} props.goToToday Handler for returning to the current period.
 * @param {Object} props.periodDisplay Metadata returned by useTimeFilter.
 */
export default function TimeFilterBar({
    currentView,
    setView,
    navigatePrev,
    navigateNext,
    goToToday,
    periodDisplay,
}) {
    return (
        <div className="bg-white shadow-md mb-6">
            <div className="container mx-auto px-4 py-4">
                <div className="flex flex-col md:flex-row items-center justify-between gap-4">
                    <ViewSwitcher currentView={currentView} onChange={setView} />
                    <DateNavigation
                        onPrev={navigatePrev}
                        onNext={navigateNext}
                        onToday={goToToday}
                        periodDisplay={periodDisplay}
                    />
                </div>
            </div>
        </div>
    );
}
