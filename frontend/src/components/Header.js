import { useMemo } from 'react';

/**
 * Display the dashboard header with title, subtitle, and the current date.
 * @param {Object} props Component props.
 * @param {string} [props.title='派工管理系统'] Primary heading text.
 * @param {string} [props.subtitle='本周工作任务分配与进度跟踪'] Supporting description text.
 * @param {string|Date} [props.date] Override date value used for display; defaults to now.
 */
export default function Header({
    title = '派工管理系统',
    subtitle = '本周工作任务分配与进度跟踪',
    date,
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
                    <div className="text-blue-100 text-right">
                        <span className="hidden md:inline-block">当前日期: </span>
                        <span className="font-medium">{formattedDate}</span>
                    </div>
                </div>
            </div>
        </header>
    );
}
