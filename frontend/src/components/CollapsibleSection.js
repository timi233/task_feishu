import { useState } from 'react';
import PropTypes from 'prop-types';

/**
 * 可折叠的表单分组组件
 */
export default function CollapsibleSection({ title, icon, defaultExpanded = true, children }) {
    const [isExpanded, setIsExpanded] = useState(defaultExpanded);

    return (
        <div className="border border-gray-200 rounded-lg overflow-hidden">
            <button
                type="button"
                onClick={() => setIsExpanded(!isExpanded)}
                className="w-full px-4 py-3 bg-gray-50 hover:bg-gray-100 transition-colors flex items-center justify-between text-left"
            >
                <div className="flex items-center gap-2">
                    {icon && <span className="text-lg">{icon}</span>}
                    <span className="font-medium text-gray-900">{title}</span>
                </div>
                <i className={`fas fa-chevron-${isExpanded ? 'up' : 'down'} text-gray-400 text-sm`} />
            </button>
            {isExpanded && (
                <div className="px-4 py-4 bg-white">
                    {children}
                </div>
            )}
        </div>
    );
}

CollapsibleSection.propTypes = {
    title: PropTypes.string.isRequired,
    icon: PropTypes.string,
    defaultExpanded: PropTypes.bool,
    children: PropTypes.node.isRequired,
};
