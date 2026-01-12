import PropTypes from 'prop-types';
import CollapsibleSection from './CollapsibleSection';
import EngineerSelector from './EngineerSelector';

/**
 * 公司日常工单表单组件 (19个字段)
 * 审批Code: F3E2FECF-0669-4EED-B764-5764DA494C9B
 */
export default function DailyWorkForm({ formData, onChange, errors }) {
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
                            <option value="IP-Guard">IP-Guard</option>
                            <option value="绿盟">绿盟</option>
                            <option value="爱数">爱数</option>
                            <option value="深信服">深信服</option>
                            <option value="其他产品">其他产品</option>
                            <option value="公司事务">公司事务</option>
                        </select>
                    </div>

                    {/* 产品型号 */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            产品型号
                        </label>
                        <input
                            type="text"
                            value={data.product_model || ''}
                            onChange={(e) => handleChange('product_model', e.target.value)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                            placeholder="输入产品型号"
                        />
                    </div>

                    {/* 工作类型 */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            工作类型
                        </label>
                        <select
                            value={data.work_type || ''}
                            onChange={(e) => handleChange('work_type', e.target.value)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                            <option value="">请选择</option>
                            <option value="售前沟通">售前沟通</option>
                            <option value="部署测试">部署测试</option>
                            <option value="实施交付">实施交付</option>
                            <option value="客户培训">客户培训</option>
                            <option value="渠道培训">渠道培训</option>
                            <option value="测试问题处理">测试问题处理</option>
                            <option value="售后问题处理">售后问题处理</option>
                            <option value="售后巡检">售后巡检</option>
                            <option value="其他-请在工作内容里注明">其他-请在工作内容里注明</option>
                        </select>
                    </div>

                    {/* 优先级 */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            优先级 <span className="text-red-500">*</span>
                        </label>
                        <select
                            value={data.priority || ''}
                            onChange={(e) => handleChange('priority', e.target.value)}
                            className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                                formErrors.priority ? 'border-red-500' : 'border-gray-300'
                            }`}
                        >
                            <option value="">请选择</option>
                            <option value="一般">一般</option>
                            <option value="重要">重要</option>
                            <option value="紧急">紧急</option>
                            <option value="非常紧急">非常紧急</option>
                        </select>
                        {formErrors.priority && (
                            <p className="mt-1 text-sm text-red-600">{formErrors.priority}</p>
                        )}
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

            {/* 渠道信息 */}
            <CollapsibleSection title="渠道信息 (选填)" icon="🔗" defaultExpanded={false}>
                <div className="space-y-4">
                    {/* 是否有渠道 */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            是否有渠道
                        </label>
                        <select
                            value={data.has_channel || ''}
                            onChange={(e) => handleChange('has_channel', e.target.value)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                            <option value="">请选择</option>
                            <option value="是">是</option>
                            <option value="否">否</option>
                        </select>
                    </div>

                    {/* 渠道详细信息 - 只在选择"是"时显示 */}
                    {data.has_channel === '是' && (
                        <div className="space-y-4 pl-4 border-l-2 border-blue-200">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    渠道名称
                                </label>
                                <input
                                    type="text"
                                    value={data.channel_name || ''}
                                    onChange={(e) => handleChange('channel_name', e.target.value)}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    placeholder="输入渠道名称"
                                />
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                        渠道联系人
                                    </label>
                                    <input
                                        type="text"
                                        value={data.channel_contact || ''}
                                        onChange={(e) => handleChange('channel_contact', e.target.value)}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                        placeholder="输入渠道联系人"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                        渠道联系方式
                                    </label>
                                    <input
                                        type="tel"
                                        value={data.channel_phone || ''}
                                        onChange={(e) => handleChange('channel_phone', e.target.value)}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                        placeholder="输入联系电话"
                                    />
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </CollapsibleSection>

            {/* 其他信息 */}
            <CollapsibleSection title="其他信息 (选填)" icon="👨‍💼" defaultExpanded={false}>
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                        工程师身份
                    </label>
                    <select
                        value={data.engineer_role || ''}
                        onChange={(e) => handleChange('engineer_role', e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                        <option value="">请选择</option>
                        <option value="厂家">厂家</option>
                        <option value="总代">总代</option>
                        <option value="公司">公司</option>
                    </select>
                </div>
            </CollapsibleSection>
        </div>
    );
}

DailyWorkForm.propTypes = {
    formData: PropTypes.object,
    onChange: PropTypes.func.isRequired,
    errors: PropTypes.object,
};

DailyWorkForm.defaultProps = {
    formData: {},
    errors: {},
};
