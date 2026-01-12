import { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import EngineerSelector from './EngineerSelector';
import { transferDispatch } from '../utils/api';

/**
 * TransferDispatchModal - 转交工单弹窗
 *
 * 功能:
 * - 选择新工程师
 * - 填写转交原因(可选)
 * - 调用transferDispatch API
 *
 * Props:
 * - isOpen: 是否显示
 * - onClose: 关闭回调
 * - dispatch: 工单对象 {instance_code, task_name, assignee, ...}
 * - onSuccess: 成功回调 (result) => void
 */
export default function TransferDispatchModal({ isOpen, onClose, dispatch, onSuccess }) {
    const [newAssignee, setNewAssignee] = useState('');
    const [reason, setReason] = useState('');
    const [error, setError] = useState(null);
    const [isSubmitting, setIsSubmitting] = useState(false);

    // 重置表单
    useEffect(() => {
        if (isOpen) {
            setNewAssignee('');
            setReason('');
            setError(null);
        }
    }, [isOpen]);

    const validate = () => {
        if (!newAssignee || !newAssignee.trim()) {
            setError('请选择新工程师');
            return false;
        }

        if (dispatch && newAssignee.trim() === dispatch.assignee) {
            setError('新工程师不能与当前工程师相同');
            return false;
        }

        setError(null);
        return true;
    };

    const handleSubmit = async (e) => {
        e.preventDefault();

        if (!validate()) {
            return;
        }

        if (!dispatch || !dispatch.instance_code) {
            setError('工单信息缺失');
            return;
        }

        try {
            setIsSubmitting(true);
            const result = await transferDispatch(
                dispatch.instance_code,
                newAssignee.trim(),
                reason.trim() || undefined
            );

            if (typeof onSuccess === 'function') {
                onSuccess(result);
            }

            onClose();
        } catch (err) {
            setError(err.message || '转交失败,请稍后重试');
        } finally {
            setIsSubmitting(false);
        }
    };

    if (!isOpen) {
        return null;
    }

    return (
        <div className="fixed inset-0 z-50">
            <div className="fixed inset-0 bg-black bg-opacity-50" />
            <div className="relative z-10 flex h-full w-full items-center justify-center px-3 md:px-4 py-4 md:py-8">
                <div className="w-full h-full md:h-auto md:max-w-lg md:mx-auto md:my-8 bg-white shadow-xl md:rounded-lg overflow-y-auto">
                    <div className="px-4 md:px-6 py-5 md:py-6">
                        <div className="flex items-start justify-between mb-6">
                            <div>
                                <h2 className="text-xl font-semibold text-gray-900">转交派工</h2>
                                <p className="mt-1 text-sm text-gray-500">
                                    任务: {dispatch?.task_name || '未命名任务'}
                                </p>
                                <p className="text-sm text-gray-500">
                                    当前工程师: {dispatch?.assignee || '未知'}
                                </p>
                            </div>
                            <button
                                type="button"
                                onClick={onClose}
                                className="text-gray-400 transition hover:text-gray-600"
                                aria-label="关闭"
                            >
                                <span className="text-2xl leading-none">×</span>
                            </button>
                        </div>

                        <form onSubmit={handleSubmit} className="space-y-4">
                    {/* 新工程师 */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            转交给 <span className="text-red-500">*</span>
                        </label>
                        <EngineerSelector
                            value={newAssignee}
                            onChange={(value) => {
                                setNewAssignee(value);
                                setError(null);
                            }}
                            placeholder="选择新工程师"
                            required
                        />
                    </div>

                    {/* 转交原因 */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            转交原因 (可选)
                        </label>
                        <textarea
                            value={reason}
                            onChange={(e) => setReason(e.target.value)}
                            placeholder="请简要说明转交原因"
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                            rows={3}
                        />
                    </div>

                    {/* 错误提示 */}
                    {error && (
                        <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                            {error}
                        </div>
                    )}

                    {/* 按钮组 */}
                    <div className="flex justify-end space-x-3 pt-4 border-t">
                        <button
                            type="button"
                            onClick={onClose}
                            className="inline-flex items-center rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition hover:bg-gray-50"
                        >
                            取消
                        </button>
                        <button
                            type="submit"
                            disabled={isSubmitting}
                            className="inline-flex items-center rounded-md bg-orange-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-orange-700 disabled:cursor-not-allowed disabled:bg-orange-300"
                        >
                            {isSubmitting ? '转交中...' : '确认转交'}
                        </button>
                    </div>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    );
}

TransferDispatchModal.propTypes = {
    isOpen: PropTypes.bool.isRequired,
    onClose: PropTypes.func.isRequired,
    dispatch: PropTypes.shape({
        instance_code: PropTypes.string.isRequired,
        task_name: PropTypes.string,
        assignee: PropTypes.string,
    }),
    onSuccess: PropTypes.func,
};
