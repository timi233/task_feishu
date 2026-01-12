import { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import EngineerSelector from './EngineerSelector';
import { updateDispatch } from '../utils/api';

/**
 * UpdateDispatchModal - 修改工单弹窗
 *
 * 功能:
 * - 预填充现有工单数据
 * - 修改工程师、优先级、时间
 * - 调用updateDispatch API
 *
 * Props:
 * - isOpen: 是否显示
 * - onClose: 关闭回调
 * - dispatch: 工单对象 {instance_code, assignee, priority, start_date, end_date, ...}
 * - onSuccess: 成功回调 (result) => void
 */
export default function UpdateDispatchModal({ isOpen, onClose, dispatch, onSuccess }) {
    const [formData, setFormData] = useState({
        assignee: '',
        priority: '',
        start_date: '',
        end_date: '',
    });
    const [errors, setErrors] = useState({});
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [submitError, setSubmitError] = useState(null);

    // 预填充数据
    useEffect(() => {
        if (isOpen && dispatch) {
            setFormData({
                assignee: dispatch.assignee || '',
                priority: dispatch.priority || '',
                start_date: dispatch.start_date || '',
                end_date: dispatch.end_date || '',
            });
            setErrors({});
            setSubmitError(null);
        }
    }, [isOpen, dispatch]);

    const handleFieldChange = (field, value) => {
        setFormData((prev) => ({ ...prev, [field]: value }));
        // 清除该字段错误
        if (errors[field]) {
            setErrors((prev) => {
                const updated = { ...prev };
                delete updated[field];
                return updated;
            });
        }
        setSubmitError(null);
    };

    const validate = () => {
        const newErrors = {};

        if (!formData.assignee || !formData.assignee.trim()) {
            newErrors.assignee = '售后工程师为必填项';
        }

        if (!formData.start_date) {
            newErrors.start_date = '服务开始时间为必填项';
        }

        if (!formData.end_date) {
            newErrors.end_date = '服务结束时间为必填项';
        }

        if (formData.start_date && formData.end_date && formData.start_date > formData.end_date) {
            newErrors.end_date = '结束日期不能早于开始日期';
        }

        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setSubmitError(null);

        if (!validate()) {
            return;
        }

        if (!dispatch || !dispatch.instance_code) {
            setSubmitError('工单信息缺失');
            return;
        }

        try {
            setIsSubmitting(true);
            const result = await updateDispatch(dispatch.instance_code, formData);

            if (typeof onSuccess === 'function') {
                onSuccess(result);
            }

            onClose();
        } catch (error) {
            setSubmitError(error.message || '修改失败,请稍后重试');
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
                <div className="w-full h-full md:h-auto md:max-w-xl md:mx-auto md:my-8 bg-white shadow-xl md:rounded-lg overflow-y-auto">
                    <div className="px-4 md:px-6 py-5 md:py-6">
                        <div className="flex items-start justify-between mb-6">
                            <div>
                                <h2 className="text-xl font-semibold text-gray-900">修改派工</h2>
                                <p className="mt-1 text-sm text-gray-500">
                                    任务: {dispatch?.task_name || '未命名任务'}
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
                    {/* 售后工程师 */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            售后工程师 <span className="text-red-500">*</span>
                        </label>
                        <EngineerSelector
                            value={formData.assignee}
                            onChange={(value) => handleFieldChange('assignee', value)}
                            error={errors.assignee}
                            required
                        />
                    </div>

                    {/* 优先级 */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            优先级
                        </label>
                        <select
                            value={formData.priority}
                            onChange={(e) => handleFieldChange('priority', e.target.value)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                            <option value="">请选择优先级</option>
                            <option value="紧急">紧急</option>
                            <option value="重要">重要</option>
                            <option value="普通">普通</option>
                        </select>
                    </div>

                    {/* 服务开始时间 */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            服务开始时间 <span className="text-red-500">*</span>
                        </label>
                        <input
                            type="date"
                            value={formData.start_date}
                            onChange={(e) => handleFieldChange('start_date', e.target.value)}
                            className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                                errors.start_date ? 'border-red-500' : 'border-gray-300'
                            }`}
                            required
                        />
                        {errors.start_date && (
                            <p className="mt-1 text-sm text-red-600">{errors.start_date}</p>
                        )}
                    </div>

                    {/* 服务结束时间 */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            服务结束时间 <span className="text-red-500">*</span>
                        </label>
                        <input
                            type="date"
                            value={formData.end_date}
                            onChange={(e) => handleFieldChange('end_date', e.target.value)}
                            className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                                errors.end_date ? 'border-red-500' : 'border-gray-300'
                            }`}
                            required
                        />
                        {errors.end_date && (
                            <p className="mt-1 text-sm text-red-600">{errors.end_date}</p>
                        )}
                    </div>

                    {/* 错误提示 */}
                    {submitError && (
                        <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                            {submitError}
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
                            className="inline-flex items-center rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-blue-300"
                        >
                            {isSubmitting ? '提交中...' : '确认修改'}
                        </button>
                    </div>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    );
}

UpdateDispatchModal.propTypes = {
    isOpen: PropTypes.bool.isRequired,
    onClose: PropTypes.func.isRequired,
    dispatch: PropTypes.shape({
        instance_code: PropTypes.string.isRequired,
        task_name: PropTypes.string,
        assignee: PropTypes.string,
        priority: PropTypes.string,
        start_date: PropTypes.string,
        end_date: PropTypes.string,
    }),
    onSuccess: PropTypes.func,
};
