import { useMemo } from 'react';

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
}) {
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
            <div className="container mx-auto px-4 py-6">
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-2xl md:text-3xl font-bold">
                            <i className="fas fa-tasks mr-3" />
                            {title}
                        </h1>
                        <p className="text-blue-100 mt-1">{subtitle}</p>
                    </div>
                    <div className="flex items-center gap-3">
                        {onSync && (
                            <>
                                {/* 手动同步按钮 */}
                                <button
                                    type="button"
                                    onClick={onSync}
                                    disabled={syncing}
                                    className={`px-4 py-2 rounded-lg font-medium transition-all flex items-center gap-2 ${
                                        syncing
                                            ? 'bg-blue-400 cursor-not-allowed'
                                            : 'bg-blue-500 hover:bg-blue-600 active:bg-blue-700'
                                    }`}
                                    title="手动从飞书同步最新数据"
                                >
                                    <i className={`fas fa-sync-alt ${syncing ? 'fa-spin' : ''}`} />
                                    <span className="hidden sm:inline">
                                        {syncing ? '同步中...' : '同步数据'}
                                    </span>
                                </button>

                                {/* 自动同步开关和状态 */}
                                <div className="flex items-center gap-2 bg-blue-800 bg-opacity-30 px-3 py-2 rounded-lg">
                                    <label className="flex items-center gap-2 cursor-pointer" title="开启/关闭每小时自动同步">
                                        <input
                                            type="checkbox"
                                            checked={autoSyncEnabled}
                                            onChange={onToggleAutoSync}
                                            className="w-4 h-4 cursor-pointer"
                                        />
                                        <span className="text-sm text-blue-100 hidden md:inline">自动同步</span>
                                        <i className="fas fa-clock md:hidden text-blue-100" />
                                    </label>
                                    {autoSyncEnabled && timeUntilSync && (
                                        <span className="text-xs text-blue-200 hidden lg:inline border-l border-blue-400 pl-2">
                                            {timeUntilSync}
                                        </span>
                                    )}
                                </div>
                            </>
                        )}
                        <div className="text-blue-100 text-right">
                            <span className="hidden md:inline-block">当前日期: </span>
                            <span className="font-medium">{formattedDate}</span>
                        </div>
                    </div>
                </div>
            </div>
        </header>
    );
}
