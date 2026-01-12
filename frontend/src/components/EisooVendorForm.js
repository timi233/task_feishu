import PropTypes from 'prop-types';
import CollapsibleSection from './CollapsibleSection';
import EngineerSelector from './EngineerSelector';

/**
 * 爱数原厂派单表单组件 (12个字段)
 * 审批Code: 1258F9D1-FFEB-4C1F-A0ED-200A7807261A
 */
export default function EisooVendorForm({ formData, onChange, errors }) {
    const data = formData || {};
    const formErrors = errors || {};

    const handleChange = (field, value) => {
        onChange(field, value);
    };

    return (
        <div className="space-y-4">
            {/* 基本信息 */}
            <CollapsibleSection title="基本信息" icon="📋" defaultExpanded={true}>
                <div className="space-y-4">
                    {/* 厂家对接人 */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            厂家对接人 <span className="text-red-500">*</span>
                        </label>
                        <input
                            type="text"
                            value={data.vendor_contact || ''}
                            onChange={(e) => handleChange('vendor_contact', e.target.value)}
                            className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                                formErrors.vendor_contact ? 'border-red-500' : 'border-gray-300'
                            }`}
                            placeholder="输入厂家对接人姓名"
                        />
                        {formErrors.vendor_contact && (
                            <p className="mt-1 text-sm text-red-600">{formErrors.vendor_contact}</p>
                        )}
                    </div>

                    {/* 产品分类 */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            产品分类
                        </label>
                        <select
                            value={data.product_category || ''}
                            onChange={(e) => handleChange('product_category', e.target.value)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                            <option value="">请选择</option>
                            <option value="AnyBackup">AnyBackup</option>
                            <option value="AnyShare">AnyShare</option>
                            <option value="其他产品">其他产品</option>
                        </select>
                    </div>

                    {/* 工作方式 */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            工作方式
                        </label>
                        <select
                            value={data.work_mode || ''}
                            onChange={(e) => handleChange('work_mode', e.target.value)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                            <option value="">请选择</option>
                            <option value="线上">线上</option>
                            <option value="线下">线下</option>
                        </select>
                    </div>
                </div>
            </CollapsibleSection>

            {/* 服务时间 */}
            <CollapsibleSection title="服务时间" icon="⏰" defaultExpanded={true}>
                <div className="space-y-4">
                    {/* 服务开始时间 */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            服务开始时间 <span className="text-red-500">*</span>
                        </label>
                        <div className="grid grid-cols-2 gap-3">
                            <input
                                type="date"
                                value={data.start_date || ''}
                                onChange={(e) => handleChange('start_date', e.target.value)}
                                className={`px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                                    formErrors.start_date ? 'border-red-500' : 'border-gray-300'
                                }`}
                            />
                            <select
                                value={data.start_period || ''}
                                onChange={(e) => handleChange('start_period', e.target.value)}
                                className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                            >
                                <option value="">时间段</option>
                                <option value="上午">上午</option>
                                <option value="下午">下午</option>
                            </select>
                        </div>
                        {formErrors.start_date && (
                            <p className="mt-1 text-sm text-red-600">{formErrors.start_date}</p>
                        )}
                    </div>

                    {/* 服务结束时间 */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            服务结束时间 <span className="text-red-500">*</span>
                        </label>
                        <div className="grid grid-cols-2 gap-3">
                            <input
                                type="date"
                                value={data.end_date || ''}
                                onChange={(e) => handleChange('end_date', e.target.value)}
                                className={`px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                                    formErrors.end_date ? 'border-red-500' : 'border-gray-300'
                                }`}
                            />
                            <select
                                value={data.end_period || ''}
                                onChange={(e) => handleChange('end_period', e.target.value)}
                                className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                            >
                                <option value="">时间段</option>
                                <option value="上午">上午</option>
                                <option value="下午">下午</option>
                            </select>
                        </div>
                        {formErrors.end_date && (
                            <p className="mt-1 text-sm text-red-600">{formErrors.end_date}</p>
                        )}
                    </div>

                    {/* 售后工程师 */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            售后工程师 <span className="text-red-500">*</span>
                        </label>
                        <EngineerSelector
                            value={data.assignee || ''}
                            onChange={(value) => handleChange('assignee', value)}
                            error={formErrors.assignee}
                            placeholder="输入或选择工程师姓名"
                            required
                        />
                    </div>
                </div>
            </CollapsibleSection>

            {/* 工作内容 */}
            <CollapsibleSection title="工作内容" icon="📝" defaultExpanded={true}>
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                        工作内容 <span className="text-red-500">*</span>
                    </label>
                    <textarea
                        value={data.work_content || ''}
                        onChange={(e) => handleChange('work_content', e.target.value)}
                        className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                            formErrors.work_content ? 'border-red-500' : 'border-gray-300'
                        }`}
                        rows="4"
                        placeholder="详细描述工作内容"
                    />
                    {formErrors.work_content && (
                        <p className="mt-1 text-sm text-red-600">{formErrors.work_content}</p>
                    )}
                </div>
            </CollapsibleSection>

            {/* 客户信息 */}
            <CollapsibleSection title="客户信息" icon="👤" defaultExpanded={true}>
                <div className="space-y-4">
                    {/* 客户公司名称 */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            客户公司名称 <span className="text-red-500">*</span>
                        </label>
                        <input
                            type="text"
                            value={data.customer_name || ''}
                            onChange={(e) => handleChange('customer_name', e.target.value)}
                            className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                                formErrors.customer_name ? 'border-red-500' : 'border-gray-300'
                            }`}
                            placeholder="输入客户公司名称"
                        />
                        {formErrors.customer_name && (
                            <p className="mt-1 text-sm text-red-600">{formErrors.customer_name}</p>
                        )}
                    </div>

                    {/* 客户联系人和联系方式 */}
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                客户联系人
                            </label>
                            <input
                                type="text"
                                value={data.contact_person || ''}
                                onChange={(e) => handleChange('contact_person', e.target.value)}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                placeholder="输入联系人"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                联系方式
                            </label>
                            <input
                                type="tel"
                                value={data.contact_phone || ''}
                                onChange={(e) => handleChange('contact_phone', e.target.value)}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                placeholder="输入联系电话"
                            />
                        </div>
                    </div>
                </div>
            </CollapsibleSection>
        </div>
    );
}

EisooVendorForm.propTypes = {
    formData: PropTypes.object,
    onChange: PropTypes.func.isRequired,
    errors: PropTypes.object,
};

EisooVendorForm.defaultProps = {
    formData: {},
    errors: {},
};
