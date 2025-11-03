import { useEffect, useMemo, useState } from 'react';
import PropTypes from 'prop-types';
import { fetchApprovalTypes } from '../utils/api';

/**
 * Approval type selection control.
 */
export default function ApprovalTypeSelector({ value, onChange }) {
    const [types, setTypes] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);

    useEffect(() => {
        let isMounted = true;
        setIsLoading(true);
        setError(null);
        fetchApprovalTypes()
            .then((list) => {
                if (!isMounted) {
                    return;
                }
                setTypes(list);
            })
            .catch((err) => {
                if (!isMounted) {
                    return;
                }
                setError(err.message || '无法加载工单类型');
                setTypes([]);
            })
            .finally(() => {
                if (!isMounted) {
                    return;
                }
                setIsLoading(false);
            });

        return () => {
            isMounted = false;
        };
    }, []);

    useEffect(() => {
        if (!value && types.length > 0) {
            onChange(types[0].type);
        }
    }, [onChange, types, value]);

    const currentDescription = useMemo(() => {
        const active = types.find((item) => item.type === value);
        return active ? active.description : '';
    }, [types, value]);

    const handleChange = (event) => {
        onChange(event.target.value);
    };

    return (
        <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
                工单类型 <span className="text-red-500">*</span>
            </label>
            <select
                className="block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={value || ''}
                onChange={handleChange}
                disabled={isLoading}
            >
                {isLoading && <option value="">加载中...</option>}
                {!isLoading && types.length === 0 && <option value="">暂无可用工单类型</option>}
                {!isLoading &&
                    types.map((type) => (
                        <option key={type.type} value={type.type}>
                            {type.name}
                        </option>
                    ))}
            </select>
            {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
            {currentDescription && !error && (
                <p className="mt-2 text-sm text-gray-600">{currentDescription}</p>
            )}
        </div>
    );
}

ApprovalTypeSelector.propTypes = {
    value: PropTypes.string,
    onChange: PropTypes.func.isRequired,
};
