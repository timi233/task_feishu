import React, { useEffect, useMemo, useCallback, useState, useRef } from 'react';
import Header from './components/Header';
import TimeFilterBar from './components/TimeFilterBar';
import WeekView from './components/WeekView';
import EngineerView from './components/EngineerView';
import MonthView from './components/MonthView';
import StatsPanel from './components/StatsPanel';
import LoadingSpinner from './components/LoadingSpinner';
import ErrorMessage from './components/ErrorMessage';
import CreateDispatchModal from './components/CreateDispatchModal';
import DispatchManagementPanel from './components/DispatchManagementPanel';
import UserManagement from './components/UserManagement';
import DispatchOrdersView from './components/DispatchOrdersView';
import useTasks from './hooks/useTasks';
import useTimeFilter from './hooks/useTimeFilter';
import { formatDate } from './utils/dateUtils';
import { groupTasksByEngineer } from './utils/taskUtils';
import { syncFromFeishu } from './utils/api';
import { isSystemAdmin } from './utils/permission';

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

    // Dispatch modal state
    const [showCreateDispatchModal, setShowCreateDispatchModal] = useState(false);
    const [showDispatchManagementPanel, setShowDispatchManagementPanel] = useState(false);
    const [showDispatchOrders, setShowDispatchOrders] = useState(false);

    // User management state
    const [showUserManagement, setShowUserManagement] = useState(false);

    const currentRange = periodDisplay?.range || periodDisplay?.dateRange;
    const rangeStart = currentRange?.start;
    const rangeEnd = currentRange?.end;

    const rangeRef = useRef({ start: currentRange?.start || null, end: currentRange?.end || null });

    useEffect(() => {
        rangeRef.current = { start: rangeStart || null, end: rangeEnd || null };
    }, [rangeStart, rangeEnd]);

    const calculateNextSyncTime = useCallback(() => {
        const now = new Date();
        return new Date(now.getTime() + 60 * 60 * 1000);
    }, []);

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

    const handleCreateDispatch = useCallback(() => {
        setShowCreateDispatchModal(true);
    }, []);

    const handleCloseDispatchModal = useCallback(() => {
        setShowCreateDispatchModal(false);
    }, []);

    const handleDispatchCreated = useCallback(() => {
        setShowCreateDispatchModal(false);
        // 刷新任务列表
        if (rangeStart && rangeEnd) {
            fetchTasks(rangeStart, rangeEnd);
        }
    }, [rangeStart, rangeEnd, fetchTasks]);

    const handleManageDispatches = useCallback(() => {
        setShowDispatchManagementPanel(true);
    }, []);

    const handleCloseManagementPanel = useCallback(() => {
        setShowDispatchManagementPanel(false);
    }, []);

    const handleManageUsers = useCallback(() => {
        setShowUserManagement(true);
    }, []);

    const handleCloseUserManagement = useCallback(() => {
        setShowUserManagement(false);
    }, []);

    const canViewDispatchOrders = isSystemAdmin();

    const handleViewDispatchOrders = useCallback(() => {
        if (!isSystemAdmin()) return;
        setShowDispatchOrders(true);
    }, []);

    const handleCloseDispatchOrders = useCallback(() => {
        setShowDispatchOrders(false);
    }, []);

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
                const { start, end } = rangeRef.current;
                if (start && end) {
                    setTimeout(() => {
                        fetchTasks(start, end);
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
    }, [fetchTasks]);

    // 自动同步功能 - 页面打开时同步一次,然后每小时执行一次
    useEffect(() => {
        if (!autoSyncEnabled) {
            setNextSyncTime(null);
            return;
        }

        // 页面打开时立即执行一次同步
        handleSync();

        // 设置初始下次同步时间
        setNextSyncTime(calculateNextSyncTime());

        // 自动同步定时器 (1小时 = 3600000毫秒)
        const syncInterval = setInterval(() => {
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
    }, [autoSyncEnabled, handleSync, calculateNextSyncTime]);

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
        const totals = { companyField: 0, vendorField: 0 };

        TASK_GROUP_KEYS.forEach((key) => {
            const dayTasks = Array.isArray(tasks?.[key]) ? tasks[key] : [];
            dayTasks.forEach((task) => {
                if (task?.order_type === 'eisoo_dispatch') {
                    totals.vendorField += 1;
                } else {
                    totals.companyField += 1;
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
                onCreateDispatch={handleCreateDispatch}
                onViewDispatchOrders={canViewDispatchOrders ? handleViewDispatchOrders : null}
                onManageDispatches={handleManageDispatches}
                onManageUsers={handleManageUsers}
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

            <main className="container mx-auto px-3 md:px-4 py-6 md:py-8">
                <TimeFilterBar
                    currentView={currentView}
                    setView={setView}
                    navigatePrev={navigatePrev}
                    navigateNext={navigateNext}
                    goToToday={goToToday}
                    periodDisplay={periodDisplay}
                />

                {currentView === 'week' && (
                    <div className="bg-white shadow-md mb-4 md:mb-6 rounded-lg">
                        <div className="container mx-auto px-3 md:px-4 py-2 md:py-3">
                            <div className="flex items-center justify-center gap-2">
                                <button
                                    type="button"
                                    className={`px-3 md:px-4 py-2 text-sm md:text-base rounded-lg font-medium transition-all flex items-center ${
                                        viewMode === 'day'
                                            ? 'bg-blue-600 text-white'
                                            : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                                    }`}
                                    onClick={() => setViewMode('day')}
                                >
                                    <i className="fas fa-calendar-day mr-1 md:mr-2" />
                                    <span className="hidden sm:inline">按日期视图</span>
                                    <span className="sm:hidden">日期</span>
                                </button>
                                <button
                                    type="button"
                                    className={`px-3 md:px-4 py-2 text-sm md:text-base rounded-lg font-medium transition-all flex items-center ${
                                        viewMode === 'engineer'
                                            ? 'bg-blue-600 text-white'
                                            : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                                    }`}
                                    onClick={() => setViewMode('engineer')}
                                >
                                    <i className="fas fa-users mr-1 md:mr-2" />
                                    <span className="hidden sm:inline">按工程师视图</span>
                                    <span className="sm:hidden">工程师</span>
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

            <footer className="bg-gray-100 py-4 md:py-6 mt-6 md:mt-8">
                <div className="container mx-auto px-3 md:px-4 text-center text-gray-600 text-xs md:text-sm">
                    <p>派工管理系统</p>
                </div>
            </footer>

            {/* 新建派工模态框 */}
            <CreateDispatchModal
                isOpen={showCreateDispatchModal}
                onClose={handleCloseDispatchModal}
                onSuccess={handleDispatchCreated}
            />

            {/* 工单管理面板 */}
            <DispatchManagementPanel
                isOpen={showDispatchManagementPanel}
                onClose={handleCloseManagementPanel}
            />

            {/* 派工单查看页面 */}
            {showDispatchOrders && canViewDispatchOrders && (
                <div className="fixed inset-0 bg-white z-50 overflow-auto">
                    <DispatchOrdersView onClose={handleCloseDispatchOrders} />
                </div>
            )}

            {/* 用户管理页面 */}
            {showUserManagement && (
                <div className="fixed inset-0 bg-white z-50 overflow-auto">
                    <div className="sticky top-0 bg-white border-b border-gray-200 px-3 md:px-4 py-3 flex items-center justify-between shadow-sm z-10">
                        <h2 className="text-lg md:text-xl font-semibold">用户管理</h2>
                        <button
                            onClick={handleCloseUserManagement}
                            className="px-3 md:px-4 py-2 bg-gray-200 hover:bg-gray-300 rounded-lg text-sm md:text-base font-medium transition-all flex items-center gap-2"
                        >
                            <i className="fas fa-arrow-left" />
                            <span className="hidden sm:inline">返回</span>
                        </button>
                    </div>
                    <UserManagement />
                </div>
            )}
        </div>
    );
}

export default App;
