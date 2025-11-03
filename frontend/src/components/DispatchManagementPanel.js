import { useState, useMemo, useEffect } from 'react';
import PropTypes from 'prop-types';
import DispatchOperationCard from './DispatchOperationCard';

/**
 * DispatchManagementPanel - 工单管理主面板
 *
 * 功能:
 * - 右侧滑出式面板
 * - 状态tabs筛选
 * - 搜索功能(任务名称/客户/工程师)
 * - 工单列表展示
 * - 刷新按钮
 *
 * 注意: 由于后端暂无列表API,使用localStorage读取最近创建的工单
 *
 * Props:
 * - isOpen: 是否显示
 * - onClose: 关闭回调
 */
export default function DispatchManagementPanel({ isOpen, onClose }) {
    const [activeTab, setActiveTab] = useState('all');
    const [searchQuery, setSearchQuery] = useState('');
    const [dispatches, setDispatches] = useState([]);

    // 从localStorage加载工单(模拟数据)
    const loadDispatches = () => {
        try {
            const stored = localStorage.getItem('created_dispatches');
            if (stored) {
                const parsed = JSON.parse(stored);
                setDispatches(Array.isArray(parsed) ? parsed : []);
            } else {
                setDispatches([]);
            }
        } catch (error) {
            console.error('Failed to load dispatches:', error);
            setDispatches([]);
        }
    };

    // 初始加载
    useEffect(() => {
        if (isOpen) {
            loadDispatches();
        }
    }, [isOpen]);

    // 状态筛选
    const filteredByStatus = useMemo(() => {
        if (activeTab === 'all') {
            return dispatches;
        }
        return dispatches.filter((d) => d.status === activeTab);
    }, [dispatches, activeTab]);

    // 搜索筛选
    const filteredDispatches = useMemo(() => {
        if (!searchQuery.trim()) {
            return filteredByStatus;
        }

        const query = searchQuery.toLowerCase();
        return filteredByStatus.filter(
            (d) =>
                d.task_name?.toLowerCase().includes(query) ||
                d.customer_name?.toLowerCase().includes(query) ||
                d.assignee?.toLowerCase().includes(query)
        );
    }, [filteredByStatus, searchQuery]);

    // 刷新数据
    const handleRefresh = () => {
        loadDispatches();
    };

    // 工单更新回调
    const handleDispatchUpdate = () => {
        loadDispatches();
    };

    if (!isOpen) {
        return null;
    }

    // 状态tabs配置
    const tabs = [
        { key: 'all', label: '全部', count: dispatches.length },
        {
            key: 'pending',
            label: '待审批',
            count: dispatches.filter((d) => d.status === 'pending').length,
        },
        {
            key: 'approved',
            label: '已通过',
            count: dispatches.filter((d) => d.status === 'approved').length,
        },
        {
            key: 'completed',
            label: '已完成',
            count: dispatches.filter((d) => d.status === 'completed').length,
        },
        {
            key: 'closed',
            label: '已关闭',
            count: dispatches.filter((d) => d.status === 'closed').length,
        },
    ];

    return (
        <>
            {/* 遮罩层 */}
            <div
                className="fixed inset-0 z-40 bg-gray-900/60 transition-opacity"
                onClick={onClose}
            ></div>

            {/* 右侧滑出面板 */}
            <div className="fixed inset-y-0 right-0 z-50 w-full max-w-3xl bg-white shadow-xl overflow-hidden flex flex-col">
                {/* 头部 */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-gray-50">
                    <div>
                        <h2 className="text-xl font-semibold text-gray-900">工单管理</h2>
                        <p className="text-sm text-gray-500 mt-1">查看和管理所有派工工单</p>
                    </div>
                    <button
                        onClick={onClose}
                        className="text-gray-400 hover:text-gray-600 transition"
                        aria-label="关闭"
                    >
                        <i className="fas fa-times text-2xl"></i>
                    </button>
                </div>

                {/* 搜索和刷新 */}
                <div className="px-6 py-4 border-b border-gray-200 bg-white">
                    <div className="flex items-center gap-3">
                        <div className="flex-1 relative">
                            <i className="fas fa-search absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400"></i>
                            <input
                                type="text"
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                placeholder="搜索任务名称、客户或工程师..."
                                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                            />
                        </div>
                        <button
                            onClick={handleRefresh}
                            className="inline-flex items-center px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition"
                        >
                            <i className="fas fa-sync-alt mr-2"></i>
                            刷新
                        </button>
                    </div>
                </div>

                {/* 状态tabs */}
                <div className="px-6 py-3 border-b border-gray-200 bg-white overflow-x-auto">
                    <div className="flex gap-2">
                        {tabs.map((tab) => (
                            <button
                                key={tab.key}
                                onClick={() => setActiveTab(tab.key)}
                                className={`inline-flex items-center px-4 py-2 text-sm font-medium rounded-md transition whitespace-nowrap ${
                                    activeTab === tab.key
                                        ? 'bg-blue-100 text-blue-700 border border-blue-200'
                                        : 'bg-gray-50 text-gray-600 border border-gray-200 hover:bg-gray-100'
                                }`}
                            >
                                {tab.label}
                                <span className="ml-2 px-2 py-0.5 text-xs rounded-full bg-white">
                                    {tab.count}
                                </span>
                            </button>
                        ))}
                    </div>
                </div>

                {/* 工单列表 */}
                <div className="flex-1 overflow-y-auto px-6 py-4 bg-gray-50">
                    {filteredDispatches.length === 0 ? (
                        <div className="flex flex-col items-center justify-center py-12 text-gray-500">
                            <i className="fas fa-inbox text-5xl mb-4 text-gray-300"></i>
                            <p className="text-lg font-medium">暂无工单</p>
                            <p className="text-sm mt-1">
                                {searchQuery
                                    ? '未找到匹配的工单,尝试调整搜索关键词'
                                    : '创建新派工后将在此显示'}
                            </p>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            {filteredDispatches.map((dispatch) => (
                                <DispatchOperationCard
                                    key={dispatch.instance_code}
                                    dispatch={dispatch}
                                    onUpdate={handleDispatchUpdate}
                                />
                            ))}
                        </div>
                    )}
                </div>

                {/* 底部提示 */}
                <div className="px-6 py-3 border-t border-gray-200 bg-gray-50 text-center">
                    <p className="text-xs text-gray-500">
                        注意: 当前数据从本地存储读取,刷新页面后仅显示本地缓存的工单
                    </p>
                </div>
            </div>
        </>
    );
}

DispatchManagementPanel.propTypes = {
    isOpen: PropTypes.bool.isRequired,
    onClose: PropTypes.func.isRequired,
};
