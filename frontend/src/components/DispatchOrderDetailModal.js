import LoadingSpinner from './LoadingSpinner';

function formatDisplayDate(value) {
    if (!value) return '—';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
        return value;
    }
    return `${date.getFullYear()}年${(date.getMonth() + 1).toString().padStart(2, '0')}月${date
        .getDate()
        .toString()
        .padStart(2, '0')}日`;
}

function InfoItem({ label, value }) {
    return (
        <div className="flex flex-col gap-1">
            <span className="text-xs text-gray-500">{label}</span>
            <span className="text-sm md:text-base text-gray-900 break-words">{value || '—'}</span>
        </div>
    );
}

export default function DispatchOrderDetailModal({
    isOpen,
    order,
    loading = false,
    error = null,
    onClose,
    onRetry,
}) {
    if (!isOpen) {
        return null;
    }

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center px-3 py-6 md:py-10">
            <div className="bg-white rounded-2xl shadow-2xl w-full max-w-3xl max-h-full overflow-y-auto">
                <div className="sticky top-0 flex items-center justify-between px-4 md:px-6 py-4 border-b border-gray-100 bg-white/95 backdrop-blur">
                    <div>
                        <h2 className="text-lg md:text-xl font-semibold text-gray-900">派工单详情</h2>
                        {order?.order_type && (
                            <p className="text-sm text-gray-500 mt-1">{order.order_type}</p>
                        )}
                    </div>
                    <button
                        type="button"
                        onClick={onClose}
                        className="p-2 rounded-full text-gray-500 hover:bg-gray-100 transition"
                        aria-label="关闭"
                    >
                        <i className="fas fa-times" />
                    </button>
                </div>

                <div className="p-4 md:p-6 space-y-6">
                    {loading && (
                        <div className="py-12">
                            <LoadingSpinner />
                        </div>
                    )}

                    {!loading && error && (
                        <div className="bg-red-50 border border-red-100 text-red-600 rounded-xl p-4">
                            <div className="flex items-center gap-2">
                                <i className="fas fa-exclamation-triangle" />
                                <span>{error}</span>
                            </div>
                            {onRetry && (
                                <button
                                    type="button"
                                    onClick={onRetry}
                                    className="mt-3 px-4 py-2 text-sm font-medium bg-red-500 text-white rounded-lg hover:bg-red-600"
                                >
                                    重试
                                </button>
                            )}
                        </div>
                    )}

                    {!loading && !error && order && (
                        <div className="space-y-6">
                            <section>
                                <h3 className="text-base md:text-lg font-semibold text-gray-800 mb-3 flex items-center gap-2">
                                    <i className="fas fa-file-alt text-blue-500" />
                                    基本信息
                                </h3>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 bg-blue-50 rounded-xl p-4">
                                    <InfoItem label="申请编号" value={order.approval_code} />
                                    <InfoItem label="审批状态" value={order.approval_status} />
                                    <InfoItem label="优先级" value={order.priority || '—'} />
                                    <InfoItem label="派工类型" value={order.order_type === 'eisoo_dispatch' ? '爱数原厂派单' : order.order_type === 'work_order' ? '工单' : order.order_type} />
                                </div>
                            </section>

                            <section>
                                <h3 className="text-base md:text-lg font-semibold text-gray-800 mb-3 flex items-center gap-2">
                                    <i className="fas fa-clock text-indigo-500" />
                                    时间信息
                                </h3>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 bg-indigo-50 rounded-xl p-4">
                                    <InfoItem label="提交时间" value={formatDisplayDate(order.submit_time)} />
                                    <InfoItem label="服务开始时间" value={formatDisplayDate(order.service_start_time)} />
                                    <InfoItem label="服务结束时间" value={formatDisplayDate(order.service_end_time)} />
                                    <InfoItem label="完成时间" value={formatDisplayDate(order.complete_time)} />
                                </div>
                            </section>

                            <section>
                                <h3 className="text-base md:text-lg font-semibold text-gray-800 mb-3 flex items-center gap-2">
                                    <i className="fas fa-user-friends text-emerald-500" />
                                    人员信息
                                </h3>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 bg-emerald-50 rounded-xl p-4">
                                    <InfoItem label="提交人" value={order.submitter_name} />
                                    <InfoItem label="提交部门" value={order.submitter_department} />
                                    <InfoItem label="工程师" value={order.engineer_name} />
                                    <InfoItem label="工程师身份" value={order.engineer_identity} />
                                    <InfoItem label="当前处理人" value={order.current_handler} />
                                    <InfoItem label="客户公司" value={order.customer_company} />
                                    <InfoItem label="客户联系人" value={order.customer_contact} />
                                    <InfoItem label="客户电话" value={order.customer_phone} />
                                </div>
                            </section>

                            <section>
                                <h3 className="text-base md:text-lg font-semibold text-gray-800 mb-3 flex items-center gap-2">
                                    <i className="fas fa-tasks text-orange-500" />
                                    工作内容
                                </h3>
                                <div className="bg-orange-50 rounded-xl p-4 text-sm md:text-base text-gray-800 leading-relaxed whitespace-pre-line min-h-[88px]">
                                    {order.work_content || '暂无工作内容'}
                                </div>
                            </section>

                            <section>
                                <h3 className="text-base md:text-lg font-semibold text-gray-800 mb-3 flex items-center gap-2">
                                    <i className="fas fa-info-circle text-gray-500" />
                                    附加信息
                                </h3>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 bg-gray-50 rounded-xl p-4">
                                    <InfoItem label="产品分类" value={order.product_category} />
                                    <InfoItem label="产品型号" value={order.product_model} />
                                    <InfoItem label="工作类型" value={order.work_type} />
                                    <InfoItem label="工作方式" value={order.work_method} />
                                    <InfoItem label="是否渠道" value={order.has_channel} />
                                    <InfoItem label="渠道名称" value={order.channel_name} />
                                    <InfoItem label="渠道联系人" value={order.channel_contact} />
                                    <InfoItem label="渠道电话" value={order.channel_phone} />
                                </div>
                            </section>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
