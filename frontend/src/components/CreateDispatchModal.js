import { useCallback, useEffect, useMemo, useState } from 'react';
import PropTypes from 'prop-types';
import ApprovalTypeSelector from './ApprovalTypeSelector';
import DailyWorkForm from './DailyWorkForm';
import EisooVendorForm from './EisooVendorForm';
import { createDispatch } from '../utils/api';

// 公司日常工单表单模板
const DAILY_TEMPLATE = {
    product_category: '',
    product_model: '',
    work_type: '',
    priority: '',
    work_mode: '',
    start_date: '',
    start_period: '',
    end_date: '',
    end_period: '',
    assignee: '',
    work_content: '',
    customer_name: '',
    contact_person: '',
    contact_phone: '',
    has_channel: '',
    channel_name: '',
    channel_contact: '',
    channel_phone: '',
    engineer_role: '',
};

// 爱数原厂派单表单模板
const EISOO_TEMPLATE = {
    vendor_contact: '',
    product_category: '',
    work_mode: '',
    start_date: '',
    start_period: '',
    end_date: '',
    end_period: '',
    assignee: '',
    work_content: '',
    customer_name: '',
    contact_person: '',
    contact_phone: '',
};

function createInitialForms() {
    return {
        daily_work: { ...DAILY_TEMPLATE },
        eisoo_vendor: { ...EISOO_TEMPLATE },
    };
}

export default function CreateDispatchModal({ isOpen, onClose, onSuccess }) {
    const [approvalType, setApprovalType] = useState('daily_work');
    const [forms, setForms] = useState(createInitialForms);
    const [fieldErrors, setFieldErrors] = useState({});
    const [generalError, setGeneralError] = useState(null);
    const [submitError, setSubmitError] = useState(null);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [submissionResult, setSubmissionResult] = useState(null);

    useEffect(() => {
        if (!isOpen) {
            setApprovalType('daily_work');
            setForms(createInitialForms());
            setFieldErrors({});
            setGeneralError(null);
            setSubmitError(null);
            setIsSubmitting(false);
            setSubmissionResult(null);
        }
    }, [isOpen]);

    const activeForm = useMemo(() => forms[approvalType] || {}, [approvalType, forms]);
    const activeErrors = useMemo(() => fieldErrors[approvalType] || {}, [approvalType, fieldErrors]);

    const handleTypeChange = (type) => {
        setApprovalType(type);
        setGeneralError(null);
        setSubmitError(null);
        setSubmissionResult(null);
    };

    const handleFieldChange = (field, value) => {
        if (!approvalType) {
            return;
        }
        setForms((prev) => ({
            ...prev,
            [approvalType]: {
                ...prev[approvalType],
                [field]: value,
            },
        }));
        // 清除该字段的错误
        setFieldErrors((prev) => {
            const current = prev[approvalType];
            if (!current || !current[field]) {
                return prev;
            }
            const updated = { ...current };
            delete updated[field];
            return { ...prev, [approvalType]: updated };
        });
        setSubmitError(null);
        setSubmissionResult(null);
    };

    const validate = useCallback(() => {
        if (!approvalType) {
            setGeneralError('请选择工单类型');
            return false;
        }

        const data = forms[approvalType] || {};
        const errorsForType = {};

        if (approvalType === 'daily_work') {
            // 必填字段: 优先级、工程师、工作内容、客户、时间
            const requiredFields = {
                priority: '优先级',
                assignee: '售后工程师',
                work_content: '工作内容',
                customer_name: '客户公司名称',
                start_date: '服务开始时间',
                end_date: '服务结束时间',
            };

            Object.entries(requiredFields).forEach(([field, label]) => {
                if (!data[field] || data[field].trim() === '') {
                    errorsForType[field] = `${label}为必填项`;
                }
            });
        } else if (approvalType === 'eisoo_vendor') {
            // 必填字段: 厂家对接人、工程师、工作内容、客户、时间
            const requiredFields = {
                vendor_contact: '厂家对接人',
                assignee: '售后工程师',
                work_content: '工作内容',
                customer_name: '客户公司名称',
                start_date: '服务开始时间',
                end_date: '服务结束时间',
            };

            Object.entries(requiredFields).forEach(([field, label]) => {
                if (!data[field] || data[field].trim() === '') {
                    errorsForType[field] = `${label}为必填项`;
                }
            });
        }

        // 验证日期顺序
        if (data.start_date && data.end_date && data.start_date > data.end_date) {
            errorsForType.end_date = '结束日期不能早于开始日期';
        }

        // 验证联系电话格式(如果填写了)
        if (data.contact_phone && data.contact_phone.trim()) {
            const phonePattern = /^[0-9+\-\s()]{6,}$/;
            if (!phonePattern.test(data.contact_phone)) {
                errorsForType.contact_phone = '请输入有效的联系电话';
            }
        }

        setFieldErrors((prev) => ({ ...prev, [approvalType]: errorsForType }));
        setGeneralError(null);

        return Object.keys(errorsForType).length === 0;
    }, [approvalType, forms]);

    const buildPayload = () => {
        if (approvalType === 'daily_work') {
            const data = forms.daily_work;

            // 构建extra_fields包含所有可选字段
            const extraFields = {};

            if (data.product_category) extraFields.product_category = data.product_category;
            if (data.product_model) extraFields.product_model = data.product_model.trim();
            if (data.work_type) extraFields.work_type = data.work_type;
            if (data.work_mode) extraFields.work_mode = data.work_mode;
            if (data.start_period) extraFields.start_period = data.start_period;
            if (data.end_period) extraFields.end_period = data.end_period;
            if (data.contact_person) extraFields.contact_person = data.contact_person.trim();
            if (data.contact_phone) extraFields.contact_phone = data.contact_phone.trim();
            if (data.has_channel) extraFields.has_channel = data.has_channel;
            if (data.channel_name) extraFields.channel_name = data.channel_name.trim();
            if (data.channel_contact) extraFields.channel_contact = data.channel_contact.trim();
            if (data.channel_phone) extraFields.channel_phone = data.channel_phone.trim();
            if (data.engineer_role) extraFields.engineer_role = data.engineer_role;

            const payload = {
                assignee: data.assignee.trim(),
                priority: data.priority,
                start_date: data.start_date,
                end_date: data.end_date,
                customer_name: data.customer_name.trim(),
                work_content: data.work_content.trim(),
            };

            if (Object.keys(extraFields).length > 0) {
                payload.extra_fields = extraFields;
            }

            return payload;
        }

        if (approvalType === 'eisoo_vendor') {
            const data = forms.eisoo_vendor;

            // 构建extra_fields包含所有可选字段
            const extraFields = {};

            extraFields.vendor_contact = data.vendor_contact.trim(); // 厂家对接人(必填)
            if (data.product_category) extraFields.product_category = data.product_category;
            if (data.work_mode) extraFields.work_mode = data.work_mode;
            if (data.start_period) extraFields.start_period = data.start_period;
            if (data.end_period) extraFields.end_period = data.end_period;
            if (data.contact_person) extraFields.contact_person = data.contact_person.trim();
            if (data.contact_phone) extraFields.contact_phone = data.contact_phone.trim();

            const payload = {
                assignee: data.assignee.trim(),
                start_date: data.start_date,
                end_date: data.end_date,
                customer_name: data.customer_name.trim(),
                work_content: data.work_content.trim(),
            };

            if (Object.keys(extraFields).length > 0) {
                payload.extra_fields = extraFields;
            }

            return payload;
        }

        return {};
    };

    const handleSubmit = async (event) => {
        event.preventDefault();
        setSubmitError(null);
        setGeneralError(null);

        const isValid = validate();
        if (!isValid) {
            return;
        }

        const payload = buildPayload();

        try {
            setIsSubmitting(true);
            const result = await createDispatch(approvalType, payload);
            setSubmissionResult(result);
            if (typeof onSuccess === 'function') {
                onSuccess(result);
            }
        } catch (error) {
            setSubmitError(error.message || '提交失败,请稍后重试');
        } finally {
            setIsSubmitting(false);
        }
    };

    if (!isOpen) {
        return null;
    }

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/60 px-4 py-6 overflow-y-auto">
            <div className="w-full max-w-3xl rounded-lg bg-white p-6 shadow-xl my-8">
                <div className="flex items-start justify-between">
                    <div>
                        <h2 className="text-xl font-semibold text-gray-900">新建派工审批</h2>
                        <p className="mt-1 text-sm text-gray-500">请选择工单类型并填写对应信息</p>
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

                <form onSubmit={handleSubmit} className="mt-6 space-y-6">
                    <ApprovalTypeSelector value={approvalType} onChange={handleTypeChange} />

                    {generalError && <p className="text-sm text-red-600">{generalError}</p>}

                    <div className="max-h-[calc(100vh-300px)] overflow-y-auto pr-2">
                        {approvalType === 'daily_work' && (
                            <DailyWorkForm
                                formData={activeForm}
                                onChange={handleFieldChange}
                                errors={activeErrors}
                            />
                        )}

                        {approvalType === 'eisoo_vendor' && (
                            <EisooVendorForm
                                formData={activeForm}
                                onChange={handleFieldChange}
                                errors={activeErrors}
                            />
                        )}
                    </div>

                    {submissionResult?.success && (
                        <div className="rounded-md border border-green-200 bg-green-50 p-4 text-sm text-green-700">
                            <p>{submissionResult.message || '派工申请已提交,等待审批'}</p>
                            {submissionResult.approval_url && (
                                <a
                                    href={submissionResult.approval_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="mt-2 inline-flex items-center text-green-700 underline hover:text-green-800"
                                >
                                    查看审批详情
                                </a>
                            )}
                        </div>
                    )}

                    {submitError && (
                        <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
                            {submitError}
                        </div>
                    )}

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
                            {isSubmitting ? '提交中...' : '提交派工'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}

CreateDispatchModal.propTypes = {
    isOpen: PropTypes.bool.isRequired,
    onClose: PropTypes.func.isRequired,
    onSuccess: PropTypes.func,
};
