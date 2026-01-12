import { useState, useMemo, useCallback } from 'react';
import { getWeekRange, getMonthRange, getWeekNumber } from '../utils/dateUtils';

/**
 * Encapsulate the week/month navigation logic used by the dashboard views.
 */
export default function useTimeFilter(initialView = 'week') {
    const [currentView, setCurrentView] = useState(initialView === 'month' ? 'month' : 'week');
    const [currentDate, setCurrentDate] = useState(() => {
        const today = new Date();
        const dayOfWeek = today.getDay(); // 0=周日, 6=周六

        // 周六周日时,跳到下周一
        if (dayOfWeek === 0 || dayOfWeek === 6) {
            const daysToNextMonday = dayOfWeek === 0 ? 1 : 2;
            const nextMonday = new Date(today);
            nextMonday.setDate(today.getDate() + daysToNextMonday);
            return nextMonday;
        }

        return today;
    });

    const setView = useCallback((view) => {
        setCurrentView(view === 'month' ? 'month' : 'week');
    }, []);

    const navigatePrev = useCallback(() => {
        setCurrentDate((prevDate) => {
            const nextDate = new Date(prevDate);
            if (currentView === 'week') {
                nextDate.setDate(nextDate.getDate() - 7);
            } else {
                nextDate.setMonth(nextDate.getMonth() - 1);
            }
            return nextDate;
        });
    }, [currentView]);

    const navigateNext = useCallback(() => {
        setCurrentDate((prevDate) => {
            const nextDate = new Date(prevDate);
            if (currentView === 'week') {
                nextDate.setDate(nextDate.getDate() + 7);
            } else {
                nextDate.setMonth(nextDate.getMonth() + 1);
            }
            return nextDate;
        });
    }, [currentView]);

    const goToToday = useCallback(() => {
        setCurrentDate(new Date());
    }, []);

    const currentRange = useMemo(() => (
        currentView === 'week' ? getWeekRange(currentDate) : getMonthRange(currentDate)
    ), [currentDate, currentView]);

    const periodDisplay = useMemo(() => {
        const rangeLabel = `${currentRange.start} ~ ${currentRange.end}`;
        const isWeekView = currentView === 'week';
        const weekStartDate = new Date(currentRange.start);
        const monthDate = new Date(currentDate);

        return {
            current: isWeekView
                ? `第 ${getWeekNumber(weekStartDate)} 周`
                : `${monthDate.getFullYear()}年${monthDate.getMonth() + 1}月`,
            prevLabel: isWeekView ? '上一周' : '上个月',
            nextLabel: isWeekView ? '下一周' : '下个月',
            rangeText: rangeLabel,
            range: currentRange,
        };
    }, [currentDate, currentRange, currentView]);

    return {
        currentView,
        currentDate,
        setView,
        navigatePrev,
        navigateNext,
        goToToday,
        periodDisplay,
    };
}
