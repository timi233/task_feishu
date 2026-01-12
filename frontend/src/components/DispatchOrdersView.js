import { useCallback, useEffect, useMemo, useState } from 'react';
import {
    fetchDispatchOrders,
    fetchDispatchOrderDetail,
    fetchDispatchStats,
    syncDispatchOrders,
} from '../utils/api';
import useEngineers from '../hooks/useEngineers';
import LoadingSpinner from './LoadingSpinner';
import DispatchOrderDetailModal from './DispatchOrderDetailModal';

const PAGE_SIZE = 20;
const ORDER_TYPES = [
    { value: 'all', label: '全部' },
    { value: 'eisoo_dispatch', label: '爱数原厂派单' },
    { value: 'work_order', label: '工单' },
];
const PRIORITY_OPTIONS = [
    { value: 'all', label: '全部优先级' },
    { value: '非常紧急', label: '非常紧急' },
    { value: '紧急', label: '紧急' },
    { value: '重要', label: '重要' },
    { value: '普通', label: '普通' },
];
const PRIORITY_BADGES = {
    非常紧急: 'bg-red-50 text-red-700 border border-red-200',
    紧急: 'bg-orange-50 text-orange-700 border border-orange-200',
    重要: 'bg-amber-50 text-amber-700 border border-amber-200',
    普通: 'bg-green-50 text-green-700 border border-green-200',
};

function formatFriendlyDate(value) {
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

function deriveStatsFromOrders(orders) {
    const priority = {};
    const type = {};
    orders.forEach((order) => {
        const pr = order.priority || order.priority_label || '普通';
        priority[pr] = (priority[pr] || 0) + 1;
        const ty = order.order_type || '其他';
        type[ty] = (type[ty] || 0) + 1;
    });
    return {
        total: orders.length,
        by_priority: priority,
        by_type: type,
    };
}

export default function DispatchOrdersView({ onClose }) {
    const { engineers } = useEngineers();
    const [orders, setOrders] = useState([]);
    const [page, setPage] = useState(1);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const [filters, setFilters] = useState({
        orderType: 'all',
        priority: 'all',
        engineer: '',
        startDate: '',
        endDate: '',
    });

    const [stats, setStats] = useState(null);
    const [statsLoading, setStatsLoading] = useState(false);

    const [syncing, setSyncing] = useState(false);
    const [syncMessage, setSyncMessage] = useState(null);

    const [detailOpen, setDetailOpen] = useState(false);
    const [detailOrder, setDetailOrder] = useState(null);
    const [detailData, setDetailData] = useState(null);
    const [detailLoading, setDetailLoading] = useState(false);
    const [detailError, setDetailError] = useState(null);

    const loadStats = useCallback(async () => {
        setStatsLoading(true);
        try {
            const data = await fetchDispatchStats();
            setStats(data);
        } catch (err) {
            console.error('Failed to fetch dispatch stats', err);
        } finally {
            setStatsLoading(false);
        }
    }, []);

    const loadOrders = useCallback(
        async (targetPage = 1) => {
            setLoading(true);
            setError(null);
            try {
                const params = {
                    page: targetPage,
                    page_size: PAGE_SIZE,
                };
                if (filters.orderType && filters.orderType !== 'all') {
                    params.order_type = filters.orderType;
                }
                if (filters.startDate) {
                    params.start_time = filters.startDate;
                }
                if (filters.endDate) {
                    params.end_time = filters.endDate;
                }
                if (filters.priority && filters.priority !== 'all') {
                    params.priority = filters.priority;
                }
                if (filters.engineer) {
                    params.engineer = filters.engineer;
                }
                const data = await fetchDispatchOrders(params);
                const list = Array.isArray(data?.orders)
                    ? data.orders
                    : Array.isArray(data?.data)
                    ? data.data
                    : [];
                const totalCount =
                    data?.total ?? data?.pagination?.total ?? data?.count ?? list.length;
                setOrders(list);
                setTotal(totalCount);
            } catch (err) {
                setError(err.message || '加载派工单失败');
            } finally {
                setLoading(false);
            }
        },
        [filters.orderType, filters.startDate, filters.endDate, filters.priority, filters.engineer]
    );

    useEffect(() => {
        setPage(1);
        loadOrders(1);
    }, [filters.orderType, filters.startDate, filters.endDate, filters.priority, filters.engineer, loadOrders]);

    useEffect(() => {
        loadStats();
    }, [loadStats]);

    const { priority, engineer, orderType } = filters;

    const filteredOrders = useMemo(() => {
        return orders.filter((order) => {
            if (priority !== 'all') {
                const pr = order.priority || order.priority_label || '普通';
                if (pr !== priority) {
                    return false;
                }
            }
            if (engineer) {
                const engineerName =
                    order.assignee_name || order.engineer_name || order.assignee || '';
                if (!engineerName.includes(engineer)) {
                    return false;
                }
            }
            if (orderType !== 'all') {
                const type = order.order_type;
                if (type !== orderType) {
                    return false;
                }
            }
            return true;
        });
    }, [orders, priority, engineer, orderType]);

    useEffect(() => {
        const timer = syncMessage ? setTimeout(() => setSyncMessage(null), 3000) : null;
        return () => {
            if (timer) clearTimeout(timer);
        };
    }, [syncMessage]);

    const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

    const displayedOrders = filteredOrders;

    const handlePriorityChange = (e) => {
        setFilters((prev) => ({ ...prev, priority: e.target.value }));
    };

    const handleEngineerChange = (e) => {
        setFilters((prev) => ({ ...prev, engineer: e.target.value }));
    };

    const handleDateChange = (field, value) => {
        setFilters((prev) => ({ ...prev, [field]: value }));
    };

    const handleTypeChange = (value) => {
        setFilters((prev) => ({ ...prev, orderType: value }));
    };

    const handlePageChange = (newPage) => {
        if (newPage < 1 || newPage > totalPages) return;
        setPage(newPage);
        loadOrders(newPage);
    };

    const handleViewDetail = async (order) => {
        if (!order) return;
        setDetailOrder(order);
        setDetailData(null);
        setDetailError(null);
        setDetailLoading(true);
        setDetailOpen(true);
        const sourceId = order.source_id || order.instance_code || order.id;
        if (!sourceId) {
            setDetailError('无法获取派工单ID');
            setDetailLoading(false);
            return;
        }
        try {
            const response = await fetchDispatchOrderDetail(sourceId);
            setDetailData(response?.data || response);
        } catch (err) {
            setDetailError(err.message || '加载详情失败');
        } finally {
            setDetailLoading(false);
        }
    };

    const closeDetail = () => {
        setDetailOpen(false);
        setDetailOrder(null);
        setDetailData(null);
        setDetailError(null);
    };

    const handleSync = async () => {
        setSyncing(true);
        setSyncMessage(null);
        try {
            const result = await syncDispatchOrders();
            const success = result?.success !== false;
            setSyncMessage(success ? '同步成功' : result?.message || '同步完成');
            await loadOrders(page);
            await loadStats();
        } catch (err) {
            setSyncMessage(err.message || '同步失败');
        } finally {
            setSyncing(false);
        }
    };

    const statsToDisplay = useMemo(() => {
        if (stats && (stats.total || stats.by_priority || stats.by_type)) {
            return stats;
        }
        return deriveStatsFromOrders(orders);
    }, [stats, orders]);

    const modalOrder = detailData || detailOrder;

    return (
        <div className="bg-gray-100 min-h-screen pb-12">
            <div className="header-gradient text-white px-4 md:px-8 py-6 shadow-lg">
                <div className="max-w-6xl mx-auto flex flex-col md:flex-row gap-4 md:gap-6 items-start md:items-center justify-between">
                    <div>
                        <h1 className="text-2xl font-bold flex items-center gap-3">
                            <i className="fas fa-clipboard-list text-white text-2xl" />
                            派工单查看
                        </h1>
                        <p className="text-blue-100 text-sm mt-2">
                            实时查看派工单，支持筛选、统计与详情查看
                        </p>
                    </div>
                    <div className="flex flex-wrap gap-2 w-full md:w-auto">
                        <button
                            type="button"
                            onClick={handleSync}
                            disabled={syncing}
                            className={`flex-1 md:flex-none px-4 py-2 rounded-lg font-medium flex items-center justify-center gap-2 transition ${
                                syncing
                                    ? 'bg-orange-300 cursor-not-allowed'
                                    : 'bg-orange-500 hover:bg-orange-600'
                            }`}
                        >
                            <i className={`fas fa-sync-alt ${syncing ? 'fa-spin' : ''}`} />
                            {syncing ? '同步中...' : '同步派工单'}
                        </button>
                        {onClose && (
                            <button
                                type="button"
                                onClick={onClose}
                                className="flex-1 md:flex-none px-4 py-2 rounded-lg font-medium flex items-center justify-center gap-2 bg-white/20 hover:bg-white/30"
                            >
                                <i className="fas fa-arrow-left" /> 返回
                            </button>
                        )}
                    </div>
                </div>
            </div>

            <div className="max-w-6xl mx-auto px-3 md:px-6 -mt-8 space-y-6">
                {syncMessage && (
                    <div className="bg-white shadow rounded-2xl p-4 border border-orange-100">
                        <div className="flex items-center gap-2 text-orange-600 text-sm">
                            <i className="fas fa-info-circle" />
                            <span>{syncMessage}</span>
                        </div>
                    </div>
                )}

                {/* Stats section */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="bg-white rounded-2xl shadow-sm border border-blue-50 p-5">
                        <p className="text-sm text-gray-500">派工单总数</p>
                        <p className="text-3xl font-bold text-blue-600 mt-2">
                            {statsLoading ? '...' : statsToDisplay?.total ?? displayedOrders.length}
                        </p>
                        <p className="text-xs text-gray-400 mt-1">最近更新 {new Date().toLocaleString('zh-CN')}</p>
                    </div>
                    <div className="bg-white rounded-2xl shadow-sm border border-amber-50 p-5">
                        <p className="text-sm font-semibold text-gray-600 mb-2">按优先级</p>
                        <div className="flex flex-wrap gap-2">
                            {Object.entries(statsToDisplay?.by_priority || {}).map(([name, value]) => (
                                <span
                                    key={name}
                                    className={`px-3 py-1 rounded-full text-xs font-semibold ${
                                        PRIORITY_BADGES[name] || 'bg-gray-100 text-gray-600'
                                    }`}
                                >
                                    {name} {value}
                                </span>
                            ))}
                            {(!statsToDisplay?.by_priority ||
                                Object.keys(statsToDisplay.by_priority || {}).length === 0) && (
                                <span className="text-sm text-gray-400">暂无数据</span>
                            )}
                        </div>
                    </div>
                    <div className="bg-white rounded-2xl shadow-sm border border-purple-50 p-5">
                        <p className="text-sm font-semibold text-gray-600 mb-2">按类型</p>
                        <div className="flex flex-wrap gap-2">
                            {Object.entries(statsToDisplay?.by_type || {}).map(([name, value]) => (
                                <span
                                    key={name}
                                    className="px-3 py-1 rounded-full text-xs font-semibold bg-purple-50 text-purple-700 border border-purple-200"
                                >
                                    {name || '其他'} {value}
                                </span>
                            ))}
                            {(!statsToDisplay?.by_type || Object.keys(statsToDisplay.by_type || {}).length === 0) && (
                                <span className="text-sm text-gray-400">暂无数据</span>
                            )}
                        </div>
                    </div>
                </div>

                {/* Filters */}
                <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-4 space-y-4">
                    <div className="flex flex-wrap gap-2">
                        {ORDER_TYPES.map((type) => (
                            <button
                                key={type.value}
                                type="button"
                                onClick={() => handleTypeChange(type.value)}
                                className={`px-4 py-2 rounded-full text-sm font-medium flex items-center gap-2 transition ${
                                    filters.orderType === type.value
                                        ? 'bg-blue-600 text-white shadow'
                                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                                }`}
                            >
                                <i
                                    className={`fas ${
                                        type.value === 'all'
                                            ? 'fa-layer-group'
                                            : type.value === '爱数原厂派单'
                                            ? 'fa-paper-plane'
                                            : 'fa-ticket-alt'
                                    }`}
                                />
                                <span className="hidden sm:inline">{type.label}</span>
                                <span className="sm:hidden">{type.label.slice(0, 2)}</span>
                            </button>
                        ))}
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-sm">
                        <div className="flex flex-col">
                            <label className="text-gray-500 mb-1">优先级</label>
                            <select
                                className="border border-gray-200 rounded-lg px-3 py-2 focus:ring-blue-500 focus:border-blue-500"
                                value={filters.priority}
                                onChange={handlePriorityChange}
                            >
                                {PRIORITY_OPTIONS.map((option) => (
                                    <option key={option.value} value={option.value}>
                                        {option.label}
                                    </option>
                                ))}
                            </select>
                        </div>
                        <div className="flex flex-col">
                            <label className="text-gray-500 mb-1">工程师</label>
                            <select
                                className="border border-gray-200 rounded-lg px-3 py-2 focus:ring-blue-500 focus:border-blue-500"
                                value={filters.engineer}
                                onChange={handleEngineerChange}
                            >
                                <option value="">全部工程师</option>
                                {engineers.map((engineer) => (
                                    <option key={engineer.user_id || engineer.name} value={engineer.name}>
                                        {engineer.name}
                                    </option>
                                ))}
                            </select>
                        </div>
                        <div className="flex flex-col">
                            <label className="text-gray-500 mb-1">开始时间</label>
                            <input
                                type="date"
                                value={filters.startDate}
                                onChange={(e) => handleDateChange('startDate', e.target.value)}
                                className="border border-gray-200 rounded-lg px-3 py-2 focus:ring-blue-500 focus:border-blue-500"
                            />
                        </div>
                        <div className="flex flex-col">
                            <label className="text-gray-500 mb-1">结束时间</label>
                            <input
                                type="date"
                                value={filters.endDate}
                                onChange={(e) => handleDateChange('endDate', e.target.value)}
                                className="border border-gray-200 rounded-lg px-3 py-2 focus:ring-blue-500 focus:border-blue-500"
                            />
                        </div>
                    </div>
                </div>

                <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-4">
                    <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 mb-4">
                        <div>
                            <h2 className="text-lg font-semibold text-gray-800">派工单列表</h2>
                            <p className="text-sm text-gray-500">每页显示 {PAGE_SIZE} 条，共 {total} 条</p>
                            {(priority !== 'all' || engineer) && (
                                <p className="text-xs text-gray-400 mt-0.5">当前页符合条件: {displayedOrders.length} 条</p>
                            )}
                        </div>
                        <div className="text-sm text-gray-500">
                            第 {page} / {totalPages} 页
                        </div>
                    </div>

                    {loading && (
                        <div className="py-12">
                            <LoadingSpinner />
                        </div>
                    )}

                    {!loading && error && (
                        <div className="bg-red-50 border border-red-100 rounded-xl p-4 text-red-600 text-sm">
                            <div className="flex items-center gap-2">
                                <i className="fas fa-exclamation-triangle" />
                                <span>{error}</span>
                            </div>
                            <button
                                type="button"
                                className="mt-3 px-4 py-2 bg-red-500 text-white text-sm rounded-lg"
                                onClick={() => loadOrders(page)}
                            >
                                重试
                            </button>
                        </div>
                    )}

                    {!loading && !error && displayedOrders.length === 0 && (
                        <div className="text-center text-gray-500 py-12">
                            <i className="fas fa-inbox text-3xl mb-3" />
                            <p>暂无派工单</p>
                        </div>
                    )}

                    {!loading && !error && displayedOrders.length > 0 && (
                        <div className="space-y-3">
                            {displayedOrders.map((order) => {
                                const priority = order.priority || order.priority_label || '普通';
                                const status = order.status_label || order.status;
                                const engineerName = order.assignee_name || order.engineer_name || order.assignee || '未分配';
                                return (
                                    <div
                                        key={order.source_id || order.instance_code || order.id}
                                        className="border border-gray-100 rounded-2xl p-4 flex flex-col gap-3 md:flex-row md:items-center md:gap-4 hover:shadow-md transition"
                                    >
                                        <div className="flex-1 space-y-2">
                                            <div className="flex flex-wrap items-center gap-2 text-sm font-medium">
                                                <span className="text-gray-900 text-base">
                                                    {order.customer_company && order.work_content
                                                        ? `${order.customer_company} - ${order.work_content}`
                                                        : order.customer_company || order.work_content || order.approval_code || '未命名派工单'}
                                                </span>
                                                <span
                                                    className={`px-3 py-1 rounded-full text-xs font-semibold ${
                                                        PRIORITY_BADGES[priority] || 'bg-gray-100 text-gray-600'
                                                    }`}
                                                >
                                                    {priority}
                                                </span>
                                                {status && (
                                                    <span className="px-3 py-1 rounded-full text-xs font-semibold bg-blue-50 text-blue-600 border border-blue-100">
                                                        {status}
                                                    </span>
                                                )}
                                            </div>
                                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-sm text-gray-600">
                                                <div className="flex items-center gap-2">
                                                    <i className="fas fa-user-cog text-gray-400" />
                                                    <span>{engineerName}</span>
                                                </div>
                                                <div className="flex items-center gap-2">
                                                    <i className="fas fa-calendar-alt text-gray-400" />
                                                    <span>服务时间: {formatFriendlyDate(order.service_time || order.plan_start_time)}</span>
                                                </div>
                                                <div className="flex items-center gap-2">
                                                    <i className="fas fa-user text-gray-400" />
                                                    <span>发起人: {order.creator_name || order.applicant_name || '未知'}</span>
                                                </div>
                                                <div className="flex items-center gap-2">
                                                    <i className="fas fa-map-marker-alt text-gray-400" />
                                                    <span>{order.customer_name || '无客户信息'}</span>
                                                </div>
                                            </div>
                                            <p className="text-sm text-gray-500 line-clamp-2">
                                                {order.work_content || order.summary || '暂无描述'}
                                            </p>
                                        </div>
                                        <div className="flex items-center gap-2 self-stretch md:flex-col md:justify-between">
                                            <button
                                                type="button"
                                                onClick={() => handleViewDetail(order)}
                                                className="px-4 py-2 rounded-lg text-sm font-medium bg-blue-600 text-white hover:bg-blue-700 w-full"
                                            >
                                                查看详情
                                            </button>
                                            <div className="text-xs text-gray-400 text-right md:text-center">
                                                更新于 {formatFriendlyDate(order.updated_at || order.modified_at || order.created_at)}
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    )}

                    <div className="flex flex-wrap items-center justify-between gap-3 mt-6">
                        <button
                            type="button"
                            onClick={() => handlePageChange(page - 1)}
                            disabled={page <= 1}
                            className={`px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 ${
                                page <= 1
                                    ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                                    : 'bg-gray-200 hover:bg-gray-300'
                            }`}
                        >
                            <i className="fas fa-arrow-left" /> 上一页
                        </button>
                        <div className="text-sm text-gray-500">
                            第 {page} 页 / 共 {totalPages} 页
                        </div>
                        <button
                            type="button"
                            onClick={() => handlePageChange(page + 1)}
                            disabled={page >= totalPages}
                            className={`px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 ${
                                page >= totalPages
                                    ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                                    : 'bg-gray-200 hover:bg-gray-300'
                            }`}
                        >
                            下一页 <i className="fas fa-arrow-right" />
                        </button>
                    </div>
                </div>
            </div>

            <DispatchOrderDetailModal
                isOpen={detailOpen}
                order={modalOrder}
                loading={detailLoading}
                error={detailError}
                onClose={closeDetail}
                onRetry={() => {
                    if (detailOrder) {
                        handleViewDetail(detailOrder);
                    }
                }}
            />
        </div>
    );
}
