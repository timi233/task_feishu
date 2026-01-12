/**
 * Display aggregated task counts for company/vendor field dispatch (unit: 人天).
 * @param {Object} props Component props.
 * @param {Object} props.stats Dispatch totals, e.g. { companyField, vendorField }.
 */
export default function StatsPanel({ stats }) {
    const { companyField = 0, vendorField = 0 } = stats || {};

    return (
        <div className="bg-white rounded-lg shadow p-4 md:p-6 mb-6 md:mb-8">
            <h2 className="text-lg md:text-xl font-bold text-gray-800 mb-3 md:mb-4 flex items-center">
                <i className="fas fa-chart-pie mr-2 text-blue-600" />
                本周任务统计
                <span className="ml-auto text-xs md:text-sm text-gray-500">单位：人天</span>
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 md:gap-4">
                <div className="bg-blue-50 rounded-lg p-3 md:p-4">
                    <div className="flex items-center">
                        <div className="bg-blue-100 p-3 rounded-full mr-3">
                            <i className="fas fa-building text-blue-600" />
                        </div>
                        <div>
                            <p className="text-xs md:text-sm text-gray-500">公司外勤派单</p>
                            <p className="text-lg md:text-xl font-bold text-gray-800">{companyField}</p>
                        </div>
                    </div>
                </div>
                <div className="bg-purple-50 rounded-lg p-3 md:p-4">
                    <div className="flex items-center">
                        <div className="bg-purple-100 p-3 rounded-full mr-3">
                            <i className="fas fa-industry text-purple-600" />
                        </div>
                        <div>
                            <p className="text-xs md:text-sm text-gray-500">厂家外勤派单</p>
                            <p className="text-lg md:text-xl font-bold text-gray-800">{vendorField}</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
