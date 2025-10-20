import React, { useEffect, useMemo, useCallback } from 'react';
import Header from './components/Header';
import TimeFilterBar from './components/TimeFilterBar';
import WeekView from './components/WeekView';
import MonthView from './components/MonthView';
import StatsPanel from './components/StatsPanel';
import LoadingSpinner from './components/LoadingSpinner';
import ErrorMessage from './components/ErrorMessage';
import useTasks from './hooks/useTasks';
import useTimeFilter from './hooks/useTimeFilter';
import { formatDate } from './utils/dateUtils';

const WEEK_CONFIG = [
    { key: 'monday', label: '周一', headerClassName: 'bg-blue-600' },
    { key: 'tuesday', label: '周二', headerClassName: 'bg-blue-700' },
    { key: 'wednesday', label: '周三', headerClassName: 'bg-blue-800' },
    { key: 'thursday', label: '周四', headerClassName: 'bg-blue-900' },
    { key: 'friday', label: '周五', headerClassName: 'bg-indigo-900' },
];

const TASK_GROUP_KEYS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'weekend', 'unknown_date'];

function App() {
    const { tasks, loading, error, fetchTasks } = useTasks();
    const timeFilter = useTimeFilter();
    const {
        currentView,
        setView,
        navigatePrev,
        navigateNext,
        goToToday,
        periodDisplay,
    } = timeFilter;

    const currentRange = periodDisplay?.range || periodDisplay?.dateRange;
    const rangeStart = currentRange?.start;
    const rangeEnd = currentRange?.end;

    useEffect(() => {
        if (!rangeStart || !rangeEnd) {
            return;
        }
        fetchTasks(rangeStart, rangeEnd);
    }, [rangeStart, rangeEnd, fetchTasks]);

    const handleRetry = useCallback(() => {
        if (!rangeStart || !rangeEnd) {
            return;
        }
        fetchTasks(rangeStart, rangeEnd);
    }, [rangeStart, rangeEnd, fetchTasks]);

    const weekDays = useMemo(() => (
        WEEK_CONFIG.map(({ key, label, headerClassName }) => ({
            id: key,
            label,
            headerClassName,
            tasks: Array.isArray(tasks?.[key]) ? tasks[key] : [],
        }))
    ), [tasks]);

    const monthDays = useMemo(() => {
        if (currentView !== 'month' || !rangeStart) {
            return [];
        }

        const firstDay = new Date(rangeStart);
        if (Number.isNaN(firstDay.getTime())) {
            return [];
        }

        const calendarStart = new Date(firstDay);
        calendarStart.setDate(firstDay.getDate() - calendarStart.getDay());

        const todayStr = formatDate(new Date());
        const tasksByDate = TASK_GROUP_KEYS.reduce((acc, key) => {
            const dayTasks = Array.isArray(tasks?.[key]) ? tasks[key] : [];
            dayTasks.forEach((task) => {
                if (!task?.date) {
                    return;
                }
                if (!acc[task.date]) {
                    acc[task.date] = [];
                }
                acc[task.date].push(task);
            });
            return acc;
        }, {});

        return Array.from({ length: 42 }, (_, index) => {
            const cellDate = new Date(calendarStart);
            cellDate.setDate(calendarStart.getDate() + index);
            const dateStr = formatDate(cellDate);

            return {
                date: dateStr,
                isCurrentMonth: cellDate.getMonth() === firstDay.getMonth(),
                isToday: dateStr === todayStr,
                tasks: tasksByDate[dateStr] || [],
            };
        });
    }, [currentView, rangeStart, tasks]);

    const stats = useMemo(() => {
        const totals = { veryUrgent: 0, urgent: 0, important: 0 };

        TASK_GROUP_KEYS.forEach((key) => {
            const dayTasks = Array.isArray(tasks?.[key]) ? tasks[key] : [];
            dayTasks.forEach((task) => {
                switch (task?.priority) {
                    case '非常紧急':
                        totals.veryUrgent += 1;
                        break;
                    case '紧急':
                        totals.urgent += 1;
                        break;
                    case '重要':
                        totals.important += 1;
                        break;
                    default:
                        break;
                }
            });
        });

        return totals;
    }, [tasks]);

    return (
        <div className="min-h-screen bg-gray-100">
            <Header />
            <main className="container mx-auto px-4 py-8">
                <TimeFilterBar
                    currentView={currentView}
                    setView={setView}
                    navigatePrev={navigatePrev}
                    navigateNext={navigateNext}
                    goToToday={goToToday}
                    periodDisplay={periodDisplay}
                />

                {loading && (
                    <div className="my-8">
                        <LoadingSpinner />
                    </div>
                )}

                {!loading && error && (
                    <div className="my-8">
                        <ErrorMessage
                            message={error?.message || '获取派工数据时发生错误'}
                            onRetry={handleRetry}
                        />
                    </div>
                )}

                {!loading && !error && (
                    <>
                        {currentView === 'week' ? (
                            <WeekView days={weekDays} />
                        ) : (
                            <MonthView days={monthDays} />
                        )}
                        <StatsPanel stats={stats} />
                    </>
                )}
            </main>

            <footer className="bg-gray-100 py-6 mt-8">
                <div className="container mx-auto px-4 text-center text-gray-600 text-sm">
                    <p>派工管理系统</p>
                </div>
            </footer>
        </div>
    );
}

export default App;
