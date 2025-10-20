/**
 * Format a Date object into the YYYY-MM-DD string required by the backend API.
 */
export function formatDate(date) {
    const safeDate = new Date(date);
    const year = safeDate.getFullYear();
    const month = String(safeDate.getMonth() + 1).padStart(2, '0');
    const day = String(safeDate.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

/**
 * Calculate the start (Monday) and end (Sunday) dates for the week containing `date`.
 */
export function getWeekRange(date) {
    const baseDate = new Date(date);
    const day = baseDate.getDay();
    const diff = baseDate.getDate() - day + (day === 0 ? -6 : 1);

    const monday = new Date(baseDate);
    monday.setDate(diff);

    const sunday = new Date(monday);
    sunday.setDate(monday.getDate() + 6);

    return {
        start: formatDate(monday),
        end: formatDate(sunday),
    };
}

/**
 * Calculate the first and last day of the month containing `date`.
 */
export function getMonthRange(date) {
    const baseDate = new Date(date);
    const firstDay = new Date(baseDate.getFullYear(), baseDate.getMonth(), 1);
    const lastDay = new Date(baseDate.getFullYear(), baseDate.getMonth() + 1, 0);

    return {
        start: formatDate(firstDay),
        end: formatDate(lastDay),
    };
}

/**
 * Determine the ISO-like week number for a given date.
 */
export function getWeekNumber(date) {
    const currentDate = new Date(date);
    const firstDayOfYear = new Date(currentDate.getFullYear(), 0, 1);
    const pastDaysOfYear = (currentDate - firstDayOfYear) / 86400000;
    return Math.ceil((pastDaysOfYear + firstDayOfYear.getDay() + 1) / 7);
}
