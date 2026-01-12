import { useMemo } from 'react';
import LoginButton from './LoginButton';
import { canAssignRole } from '../utils/permission';

/**
 * Display the dashboard header with title, subtitle, and the current date.
 * @param {Object} props Component props.
 * @param {string} [props.title='派工管理系统'] Primary heading text.
 * @param {string} [props.subtitle='本周工作任务分配与进度跟踪'] Supporting description text.
 * @param {string|Date} [props.date] Override date value used for display; defaults to now.
 * @param {Function} [props.onSync] Callback function when sync button is clicked.
 * @param {boolean} [props.syncing] Whether sync is in progress.
 * @param {boolean} [props.autoSyncEnabled] Whether auto sync is enabled.
 * @param {Function} [props.onToggleAutoSync] Callback to toggle auto sync.
 * @param {Date} [props.nextSyncTime] Next scheduled sync time.
 * @param {Function} [props.onCreateDispatch] Callback function when create dispatch button is clicked.
 * @param {Function} [props.onViewDispatchOrders] Callback to open dispatch orders view.
 * @param {Function} [props.onManageUsers] Callback function when user management button is clicked (system admin only).
 */
export default function Header({
    title = '派工管理系统',
    subtitle = '本周工作任务分配与进度跟踪',
    date,
    onSync,
    syncing = false,
    autoSyncEnabled = false,
    onToggleAutoSync,
    nextSyncTime,
    onCreateDispatch,
    onViewDispatchOrders,
    onManageDispatches,
    onManageUsers,
}) {
    // 检查用户是否有系统管理员权限
    const hasAdminPermission = canAssignRole();
    const formattedDate = useMemo(() => {
        const baseDate = date ? new Date(date) : new Date();
        return baseDate.toLocaleDateString('zh-CN', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            weekday: 'long',
        });
    }, [date]);

    // 计算距离下次同步的时间
    const timeUntilSync = useMemo(() => {
        if (!nextSyncTime) return null;

        const now = new Date();
        const diff = nextSyncTime - now;

        if (diff <= 0) return '即将同步';

        const minutes = Math.floor(diff / 1000 / 60);
        const hours = Math.floor(minutes / 60);
        const remainingMinutes = minutes % 60;

        if (hours > 0) {
            return `${hours}小时${remainingMinutes}分钟后`;
        }
        return `${remainingMinutes}分钟后`;
    }, [nextSyncTime]);

    return (
        <header className="header-gradient text-white shadow-lg">
            <div className="container mx-auto px-3 md:px-4 py-4 md:py-6">
                <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-3">
                    <div className="w-full md:w-auto">
                        <h1 className="text-xl md:text-2xl lg:text-3xl font-bold">
                            <i className="fas fa-tasks mr-2" />
                            {title}
                        </h1>
                        <p className="text-blue-100 text-sm md:text-base mt-1">{subtitle}</p>
                        <div className="md:hidden text-blue-100 text-sm mt-2">{formattedDate}</div>
                    </div>
                    <div className="w-full md:w-auto flex flex-wrap items-center gap-2">
                        <LoginButton />
                        {onViewDispatchOrders && hasAdminPermission && (
                            <button
                                type="button"
                                onClick={onViewDispatchOrders}
                                className="px-3 md:px-4 py-2 rounded-lg font-medium transition-all flex items-center gap-2 bg-orange-500 hover:bg-orange-600 active:bg-orange-700"
                                title="查看派工单"
                            >
                                <i className="fas fa-clipboard-list" />
                                <span className="hidden lg:inline">派工单查看</span>
                                <span className="lg:hidden">派工单</span>
                            </button>
                        )}
                        {onCreateDispatch && hasAdminPermission && (
                            <button
                                type="button"
                                onClick={onCreateDispatch}
                                className="px-3 md:px-4 py-2 rounded-lg font-medium transition-all flex items-center gap-2 bg-green-500 hover:bg-green-600 active:bg-green-700"
                                title="新建派工申请"
                            >
                                <i className="fas fa-plus" />
                                <span className="hidden lg:inline">新建派工</span>
                            </button>
                        )}
                        {onManageDispatches && hasAdminPermission && (
                            <button
                                type="button"
                                onClick={onManageDispatches}
                                className="px-3 md:px-4 py-2 rounded-lg font-medium transition-all flex items-center gap-2 bg-purple-500 hover:bg-purple-600 active:bg-purple-700"
                                title="工单管理"
                            >
                                <i className="fas fa-list-alt" />
                                <span className="hidden lg:inline">工单管理</span>
                            </button>
                        )}
                        {onManageUsers && hasAdminPermission && (
                            <button
                                type="button"
                                onClick={onManageUsers}
                                className="px-3 md:px-4 py-2 rounded-lg font-medium transition-all flex items-center gap-2 bg-orange-500 hover:bg-orange-600 active:bg-orange-700"
                                title="用户管理"
                            >
                                <i className="fas fa-users-cog" />
                                <span className="hidden lg:inline">用户管理</span>
                            </button>
                        )}
                        {onSync && (
                            <>
                                <button
                                    type="button"
                                    onClick={onSync}
                                    disabled={syncing}
                                    className={`px-3 md:px-4 py-2 rounded-lg font-medium transition-all flex items-center gap-2 ${
                                        syncing
                                            ? 'bg-blue-400 cursor-not-allowed'
                                            : 'bg-blue-500 hover:bg-blue-600 active:bg-blue-700'
                                    }`}
                                    title="手动从飞书同步最新数据"
                                >
                                    <i className={`fas fa-sync-alt ${syncing ? 'fa-spin' : ''}`} />
                                    <span className="hidden md:inline">
                                        {syncing ? '同步中...' : '同步数据'}
                                    </span>
                                </button>
                                <div className="flex items-center gap-2 bg-blue-800 bg-opacity-30 px-2 md:px-3 py-2 rounded-lg">
                                    <label className="flex items-center gap-1 md:gap-2 cursor-pointer" title="开启/关闭每小时自动同步">
                                        <input
                                            type="checkbox"
                                            checked={autoSyncEnabled}
                                            onChange={onToggleAutoSync}
                                            className="w-4 h-4 cursor-pointer"
                                        />
                                        <i className="fas fa-clock text-blue-100 md:hidden" />
                                        <span className="text-xs md:text-sm text-blue-100 hidden md:inline">自动同步</span>
                                    </label>
                                    {autoSyncEnabled && timeUntilSync && (
                                        <span className="text-xs text-blue-200 hidden lg:inline border-l border-blue-400 pl-2">
                                            {timeUntilSync}
                                        </span>
                                    )}
                                </div>
                            </>
                        )}
                        <div className="hidden md:block text-blue-100 text-right text-sm">
                            <span className="hidden lg:inline">当前日期: </span>
                            <span className="font-medium">{formattedDate}</span>
                        </div>
                    </div>
                </div>
            </div>
        </header>
    );
}
