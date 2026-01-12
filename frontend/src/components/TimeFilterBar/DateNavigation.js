/**
 * Navigation controls for traversing weeks or months alongside the active period labels.
 * @param {Object} props Component props.
 * @param {Function} props.onPrev Navigate to the previous period.
 * @param {Function} props.onNext Navigate to the next period.
 * @param {Function} props.onToday Jump back to today.
 * @param {Object} props.periodDisplay Labels derived from the time filter hook.
 * @param {string} props.periodDisplay.current Human readable period title.
 * @param {string} props.periodDisplay.rangeText Date range string for the period.
 * @param {string} props.periodDisplay.prevLabel Label for the previous period button.
 * @param {string} props.periodDisplay.nextLabel Label for the next period button.
 */
export default function DateNavigation({ onPrev, onNext, onToday, periodDisplay }) {
    const { current, rangeText, prevLabel, nextLabel } = periodDisplay;

    return (
        <div className="flex flex-wrap sm:flex-nowrap items-center gap-2 md:gap-3 justify-center sm:justify-end">
            <button
                type="button"
                onClick={onPrev}
                className="nav-btn px-2 md:px-3 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-all flex items-center gap-1 text-sm md:text-base"
                aria-label={prevLabel}
            >
                <i className="fas fa-chevron-left" />
                <span className="hidden sm:inline">{prevLabel}</span>
            </button>

            <div className="text-center min-w-[160px] md:min-w-[200px]">
                <div className="text-sm md:text-base font-bold text-gray-800">{current}</div>
                <div className="text-xs md:text-sm text-gray-500">{rangeText}</div>
            </div>

            <button
                type="button"
                onClick={onNext}
                className="nav-btn px-2 md:px-3 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-all flex items-center gap-1 text-sm md:text-base"
                aria-label={nextLabel}
            >
                <span className="hidden sm:inline">{nextLabel}</span>
                <i className="fas fa-chevron-right" />
            </button>

            <button
                type="button"
                onClick={onToday}
                className="px-2 md:px-3 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-all flex items-center gap-1 text-sm md:text-base"
                aria-label="今天"
            >
                <i className="fas fa-calendar-day hidden sm:inline" />
                <span className="hidden sm:inline">今天</span>
                <i className="fas fa-calendar-day sm:hidden" />
            </button>
        </div>
    );
}
