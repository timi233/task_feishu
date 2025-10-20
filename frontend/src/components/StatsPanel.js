/**
 * Display aggregated task counts grouped by priority level.
 * @param {Object} props Component props.
 * @param {Object} props.stats Object containing priority totals.
 * @param {number} [props.stats.veryUrgent=0] Count of "非常紧急" tasks.
 * @param {number} [props.stats.urgent=0] Count of "紧急" tasks.
 * @param {number} [props.stats.important=0] Count of "重要" tasks.
 */
export default function StatsPanel({ stats }) {
    const { veryUrgent = 0, urgent = 0, important = 0 } = stats || {};

    return (
        <div className="bg-white rounded-lg shadow p-6 mb-8">
            <h2 className="text-xl font-bold text-gray-800 mb-4 flex items-center">
                <i className="fas fa-chart-pie mr-2 text-blue-600" />
                本周任务统计
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-blue-50 rounded-lg p-4">
                    <div className="flex items-center">
                        <div className="bg-blue-100 p-3 rounded-full mr-3">
                            <i className="fas fa-exclamation-circle text-blue-600" />
                        </div>
                        <div>
                            <p className="text-sm text-gray-500">非常紧急</p>
                            <p className="text-xl font-bold text-gray-800">{veryUrgent}</p>
                        </div>
                    </div>
                </div>
                <div className="bg-orange-50 rounded-lg p-4">
                    <div className="flex items-center">
                        <div className="bg-orange-100 p-3 rounded-full mr-3">
                            <i className="fas fa-exclamation-triangle text-orange-600" />
                        </div>
                        <div>
                            <p className="text-sm text-gray-500">紧急</p>
                            <p className="text-xl font-bold text-gray-800">{urgent}</p>
                        </div>
                    </div>
                </div>
                <div className="bg-red-50 rounded-lg p-4">
                    <div className="flex items-center">
                        <div className="bg-red-100 p-3 rounded-full mr-3">
                            <i className="fas fa-flag text-red-600" />
                        </div>
                        <div>
                            <p className="text-sm text-gray-500">重要</p>
                            <p className="text-xl font-bold text-gray-800">{important}</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
