import { useState } from 'react';
import PropTypes from 'prop-types';
import ConfirmDialog from './ConfirmDialog';
import UpdateDispatchModal from './UpdateDispatchModal';
import TransferDispatchModal from './TransferDispatchModal';
import { completeDispatch, closeDispatch, fetchApprovalDetail } from '../utils/api';

/**
 * DispatchOperationCard - 工单操作卡片
 *
 * 功能:
 * - 显示工单基本信息
 * - 提供操作按钮: 修改、转交、完成、关闭、查看详情
 * - 根据status显示/隐藏按钮
 *
 * Props:
 * - dispatch: 工单对象 {instance_code, task_name, assignee, customer_name, start_date, end_date, status, approval_url}
 * - onUpdate: 工单更新回调
 */
export default function DispatchOperationCard({ dispatch, onUpdate }) {
    const [showUpdateModal, setShowUpdateModal] = useState(false);
    const [showTransferModal, setShowTransferModal] = useState(false);
    const [showCompleteDialog, setShowCompleteDialog] = useState(false);
    const [showCloseDialog, setShowCloseDialog] = useState(false);
    const [showDetailDialog, setShowDetailDialog] = useState(false);
    const [detailContent, setDetailContent] = useState(null);
    const [isLoadingDetail, setIsLoadingDetail] = useState(false);
    const [operationError, setOperationError] = useState(null);

    // 根据状态显示对应的badge样式
    const getStatusBadge = (status) => {
        const statusMap = {
            pending: { text: '待审批', class: 'bg-yellow-100 text-yellow-800' },
            approved: { text: '已通过', class: 'bg-green-100 text-green-800' },
            rejected: { text: '已拒绝', class: 'bg-red-100 text-red-800' },
            completed: { text: '已完成', class: 'bg-blue-100 text-blue-800' },
            closed: { text: '已关闭', class: 'bg-gray-100 text-gray-800' },
        };

        const config = statusMap[status] || { text: status || '未知', class: 'bg-gray-100 text-gray-800' };

        return (
            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.class}`}>
                {config.text}
            </span>
        );
    };

    // 处理完成操作
    const handleComplete = async (completionNote) => {
        setOperationError(null);
        try {
            await completeDispatch(dispatch.instance_code, completionNote);
            if (typeof onUpdate === 'function') {
                onUpdate();
            }
            setShowCompleteDialog(false);
        } catch (error) {
            setOperationError(error.message || '完成操作失败');
        }
    };

    // 处理关闭操作
    const handleClose = async (reason) => {
        setOperationError(null);
        try {
            await closeDispatch(dispatch.instance_code, reason);
            if (typeof onUpdate === 'function') {
                onUpdate();
            }
            setShowCloseDialog(false);
        } catch (error) {
            setOperationError(error.message || '关闭操作失败');
        }
    };

    // 查看审批详情
    const handleViewDetail = async () => {
        setIsLoadingDetail(true);
        setDetailContent(null);
        setShowDetailDialog(true);

        try {
            const detail = await fetchApprovalDetail(dispatch.instance_code);
            setDetailContent(detail);
        } catch (error) {
            setDetailContent({ error: error.message || '获取详情失败' });
        } finally {
            setIsLoadingDetail(false);
        }
    };

    // 成功回调
    const handleOperationSuccess = () => {
        if (typeof onUpdate === 'function') {
            onUpdate();
        }
    };

    // 判断是否可以执行各种操作
    const canModify = dispatch.status === 'pending' || dispatch.status === 'approved';
    const canTransfer = dispatch.status === 'pending' || dispatch.status === 'approved';
    const canComplete = dispatch.status === 'approved';
    const canClose = dispatch.status !== 'completed' && dispatch.status !== 'closed';

    return (
        <>
            <div className="border border-gray-200 rounded-lg p-4 bg-white shadow-sm hover:shadow-md transition-shadow">
                {/* 标题行 */}
                <div className="flex items-start justify-between mb-3">
                    <div className="flex-1">
                        <h3 className="text-lg font-semibold text-gray-900 mb-1">
                            {dispatch.task_name || '未命名任务'}
                        </h3>
                        {getStatusBadge(dispatch.status)}
                    </div>
                </div>

                {/* 信息行 */}
                <div className="space-y-2 text-sm text-gray-600 mb-4">
                    {dispatch.customer_name && (
                        <div className="flex items-center gap-2">
                            <i className="fas fa-building w-4 text-gray-400"></i>
                            <span>客户: {dispatch.customer_name}</span>
                        </div>
                    )}
                    {dispatch.assignee && (
                        <div className="flex items-center gap-2">
                            <i className="fas fa-user w-4 text-gray-400"></i>
                            <span>工程师: {dispatch.assignee}</span>
                        </div>
                    )}
                    {(dispatch.start_date || dispatch.end_date) && (
                        <div className="flex items-center gap-2">
                            <i className="fas fa-calendar w-4 text-gray-400"></i>
                            <span>
                                时间: {dispatch.start_date || '未知'} ~ {dispatch.end_date || '未知'}
                            </span>
                        </div>
                    )}
                </div>

                {/* 错误提示 */}
                {operationError && (
                    <div className="mb-3 rounded-md border border-red-200 bg-red-50 p-2 text-sm text-red-700">
                        {operationError}
                    </div>
                )}

                {/* 操作按钮 */}
                <div className="flex flex-wrap gap-2">
                    {canModify && (
                        <button
                            onClick={() => setShowUpdateModal(true)}
                            className="inline-flex items-center px-3 py-1.5 text-sm font-medium text-blue-700 bg-blue-50 border border-blue-200 rounded-md hover:bg-blue-100 transition"
                        >
                            <i className="fas fa-edit mr-1.5"></i>
                            修改
                        </button>
                    )}

                    {canTransfer && (
                        <button
                            onClick={() => setShowTransferModal(true)}
                            className="inline-flex items-center px-3 py-1.5 text-sm font-medium text-orange-700 bg-orange-50 border border-orange-200 rounded-md hover:bg-orange-100 transition"
                        >
                            <i className="fas fa-exchange-alt mr-1.5"></i>
                            转交
                        </button>
                    )}

                    {canComplete && (
                        <button
                            onClick={() => setShowCompleteDialog(true)}
                            className="inline-flex items-center px-3 py-1.5 text-sm font-medium text-green-700 bg-green-50 border border-green-200 rounded-md hover:bg-green-100 transition"
                        >
                            <i className="fas fa-check-circle mr-1.5"></i>
                            完成
                        </button>
                    )}

                    {canClose && (
                        <button
                            onClick={() => setShowCloseDialog(true)}
                            className="inline-flex items-center px-3 py-1.5 text-sm font-medium text-red-700 bg-red-50 border border-red-200 rounded-md hover:bg-red-100 transition"
                        >
                            <i className="fas fa-times-circle mr-1.5"></i>
                            关闭
                        </button>
                    )}

                    <button
                        onClick={handleViewDetail}
                        className="inline-flex items-center px-3 py-1.5 text-sm font-medium text-gray-700 bg-gray-50 border border-gray-200 rounded-md hover:bg-gray-100 transition"
                    >
                        <i className="fas fa-info-circle mr-1.5"></i>
                        查看详情
                    </button>

                    {dispatch.approval_url && (
                        <a
                            href={dispatch.approval_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center px-3 py-1.5 text-sm font-medium text-purple-700 bg-purple-50 border border-purple-200 rounded-md hover:bg-purple-100 transition"
                        >
                            <i className="fas fa-external-link-alt mr-1.5"></i>
                            飞书审批
                        </a>
                    )}
                </div>
            </div>

            {/* 修改弹窗 */}
            <UpdateDispatchModal
                isOpen={showUpdateModal}
                onClose={() => setShowUpdateModal(false)}
                dispatch={dispatch}
                onSuccess={handleOperationSuccess}
            />

            {/* 转交弹窗 */}
            <TransferDispatchModal
                isOpen={showTransferModal}
                onClose={() => setShowTransferModal(false)}
                dispatch={dispatch}
                onSuccess={handleOperationSuccess}
            />

            {/* 完成确认 */}
            <ConfirmDialog
                isOpen={showCompleteDialog}
                onClose={() => setShowCompleteDialog(false)}
                onConfirm={handleComplete}
                title="确认完成"
                message="确认标记此派工为已完成?"
                confirmText="确认完成"
                confirmButtonClass="bg-green-600 hover:bg-green-700"
                showInput
                inputPlaceholder="请输入完成备注(可选)"
            />

            {/* 关闭确认 */}
            <ConfirmDialog
                isOpen={showCloseDialog}
                onClose={() => setShowCloseDialog(false)}
                onConfirm={handleClose}
                title="确认关闭"
                message="关闭后将撤回审批实例,确定要关闭此派工吗?"
                confirmText="确认关闭"
                confirmButtonClass="bg-red-600 hover:bg-red-700"
                showInput
                inputPlaceholder="请输入关闭原因(可选)"
            />

            {/* 详情对话框 */}
            <ConfirmDialog
                isOpen={showDetailDialog}
                onClose={() => setShowDetailDialog(false)}
                onConfirm={() => setShowDetailDialog(false)}
                title="审批详情"
                message={
                    isLoadingDetail
                        ? '加载中...'
                        : detailContent?.error
                        ? detailContent.error
                        : JSON.stringify(detailContent, null, 2)
                }
                confirmText="关闭"
                cancelText=""
                confirmButtonClass="bg-gray-600 hover:bg-gray-700"
            />
        </>
    );
}

DispatchOperationCard.propTypes = {
    dispatch: PropTypes.shape({
        instance_code: PropTypes.string.isRequired,
        task_name: PropTypes.string,
        assignee: PropTypes.string,
        customer_name: PropTypes.string,
        start_date: PropTypes.string,
        end_date: PropTypes.string,
        status: PropTypes.string,
        approval_url: PropTypes.string,
    }).isRequired,
    onUpdate: PropTypes.func,
};
