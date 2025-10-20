import React, { useEffect, useMemo, useCallback, useState } from 'react';
import Header from './components/Header';
import TimeFilterBar from './components/TimeFilterBar';
import WeekView from './components/WeekView';
import EngineerView from './components/EngineerView';
import MonthView from './components/MonthView';
import StatsPanel from './components/StatsPanel';
import LoadingSpinner from './components/LoadingSpinner';
import ErrorMessage from './components/ErrorMessage';
import useTasks from './hooks/useTasks';
import useTimeFilter from './hooks/useTimeFilter';
import { formatDate } from './utils/dateUtils';
import { groupTasksByEngineer } from './utils/taskUtils';
import { syncFromFeishu } from './utils/api';

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

    // View mode: 'day' for day-based view, 'engineer' for engineer-based view
    const [viewMode, setViewMode] = useState('day');

    // Sync state
    const [syncing, setSyncing] = useState(false);
    const [syncMessage, setSyncMessage] = useState(null);
    const [autoSyncEnabled, setAutoSyncEnabled] = useState(() => {
        // 从localStorage读取用户偏好,默认开启
        const saved = localStorage.getItem('autoSyncEnabled');
        return saved !== null ? saved === 'true' : true;
    });
    const [nextSyncTime, setNextSyncTime] = useState(null);

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

    const handleSync = useCallback(async () => {
        setSyncing(true);
        setSyncMessage(null);

        try {
            const data = await syncFromFeishu();

            if (data.success) {
                setSyncMessage({
                    type: 'success',
                    text: `同步成功!已同步 ${data.records_synced} 条记录`,
                });
                // 同步成功后重新获取数据
                if (rangeStart && rangeEnd) {
                    setTimeout(() => {
                        fetchTasks(rangeStart, rangeEnd);
                    }, 500);
                }
            } else {
                setSyncMessage({
                    type: 'warning',
                    text: data.message || '同步完成但未获取到新数据',
                });
            }
        } catch (err) {
            setSyncMessage({
                type: 'error',
                text: `同步失败: ${err.message}`,
            });
        } finally {
            setSyncing(false);
            // 3秒后自动清除消息
            setTimeout(() => setSyncMessage(null), 3000);
        }
    }, [rangeStart, rangeEnd, fetchTasks]);

    // 自动同步功能 - 页面打开时同步一次,然后每小时执行一次
    useEffect(() => {
        if (!autoSyncEnabled) {
            return;
        }

        // 计算下次同步时间 (当前时间 + 1小时)
        const calculateNextSyncTime = () => {
            const now = new Date();
            const next = new Date(now.getTime() + 60 * 60 * 1000); // 1小时后
            return next;
        };

        // 页面打开时立即执行一次同步
        console.log('[Auto Sync] Initial sync on page load...');
        handleSync();

        // 设置初始下次同步时间
        setNextSyncTime(calculateNextSyncTime());

        // 自动同步定时器 (1小时 = 3600000毫秒)
        const syncInterval = setInterval(() => {
            console.log('[Auto Sync] Triggering automatic sync...');
            handleSync();
            setNextSyncTime(calculateNextSyncTime());
        }, 60 * 60 * 1000); // 每小时

        // 更新倒计时显示 (每分钟更新一次)
        const countdownInterval = setInterval(() => {
            setNextSyncTime(prev => {
                if (!prev) return calculateNextSyncTime();
                return prev;
            });
        }, 60 * 1000); // 每分钟更新

        return () => {
            clearInterval(syncInterval);
            clearInterval(countdownInterval);
        };
    }, [autoSyncEnabled, handleSync]);

    const weekDays = useMemo(() => (
        WEEK_CONFIG.map(({ key, label, headerClassName }) => ({
            id: key,
            label,
            headerClassName,
            tasks: Array.isArray(tasks?.[key]) ? tasks[key] : [],
        }))
    ), [tasks]);

    const engineerData = useMemo(() => {
        if (viewMode !== 'engineer' || currentView !== 'week') {
            return null;
        }
        return groupTasksByEngineer(tasks);
    }, [tasks, viewMode, currentView]);

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

    // 切换自动同步开关
    const handleToggleAutoSync = useCallback(() => {
        setAutoSyncEnabled(prev => {
            const newValue = !prev;
            // 保存到localStorage
            localStorage.setItem('autoSyncEnabled', newValue.toString());
            return newValue;
        });
    }, []);

    return (
        <div className="min-h-screen bg-gray-100">
            <Header
                onSync={handleSync}
                syncing={syncing}
                autoSyncEnabled={autoSyncEnabled}
                onToggleAutoSync={handleToggleAutoSync}
                nextSyncTime={nextSyncTime}
            />

            {/* 同步消息提示 */}
            {syncMessage && (
                <div className={`mx-auto max-w-4xl mt-4 px-4`}>
                    <div
                        className={`px-4 py-3 rounded-lg shadow-md ${
                            syncMessage.type === 'success'
                                ? 'bg-green-100 text-green-800 border border-green-300'
                                : syncMessage.type === 'warning'
                                ? 'bg-yellow-100 text-yellow-800 border border-yellow-300'
                                : 'bg-red-100 text-red-800 border border-red-300'
                        }`}
                    >
                        <div className="flex items-center gap-2">
                            <i
                                className={`fas ${
                                    syncMessage.type === 'success'
                                        ? 'fa-check-circle'
                                        : syncMessage.type === 'warning'
                                        ? 'fa-exclamation-triangle'
                                        : 'fa-times-circle'
                                }`}
                            />
                            <span>{syncMessage.text}</span>
                        </div>
                    </div>
                </div>
            )}

            <main className="container mx-auto px-4 py-8">
                <TimeFilterBar
                    currentView={currentView}
                    setView={setView}
                    navigatePrev={navigatePrev}
                    navigateNext={navigateNext}
                    goToToday={goToToday}
                    periodDisplay={periodDisplay}
                />

                {currentView === 'week' && (
                    <div className="bg-white shadow-md mb-6 rounded-lg">
                        <div className="container mx-auto px-4 py-3">
                            <div className="flex items-center justify-center gap-2">
                                <button
                                    type="button"
                                    className={`px-4 py-2 rounded-lg font-medium transition-all ${
                                        viewMode === 'day'
                                            ? 'bg-blue-600 text-white'
                                            : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                                    }`}
                                    onClick={() => setViewMode('day')}
                                >
                                    <i className="fas fa-calendar-day mr-2" />
                                    按日期视图
                                </button>
                                <button
                                    type="button"
                                    className={`px-4 py-2 rounded-lg font-medium transition-all ${
                                        viewMode === 'engineer'
                                            ? 'bg-blue-600 text-white'
                                            : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                                    }`}
                                    onClick={() => setViewMode('engineer')}
                                >
                                    <i className="fas fa-users mr-2" />
                                    按工程师视图
                                </button>
                            </div>
                        </div>
                    </div>
                )}

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
                        {currentView === 'week' && viewMode === 'day' && (
                            <WeekView days={weekDays} />
                        )}
                        {currentView === 'week' && viewMode === 'engineer' && (
                            <EngineerView engineerData={engineerData} />
                        )}
                        {currentView === 'month' && (
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
