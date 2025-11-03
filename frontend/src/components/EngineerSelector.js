import { useState, useEffect, useMemo } from 'react';
import PropTypes from 'prop-types';
import useEngineers from '../hooks/useEngineers';

/**
 * EngineerSelector - 工程师选择器组件
 *
 * 功能:
 * - 输入时实时过滤工程师列表
 * - 下拉列表展示匹配结果
 * - 支持键盘上下选择
 * - 显示loading和error状态
 *
 * Props:
 * - value: 当前选中的工程师姓名
 * - onChange: 值改变回调 (name) => void
 * - error: 外部验证错误信息
 * - placeholder: 占位符文本
 * - required: 是否必填
 * - className: 额外的CSS类名
 */
export default function EngineerSelector({
    value,
    onChange,
    error,
    placeholder = '输入或选择工程师姓名',
    required = false,
    className = '',
}) {
    const { engineers, loading, error: loadError } = useEngineers();
    const [inputValue, setInputValue] = useState(value || '');
    const [showDropdown, setShowDropdown] = useState(false);
    const [focusedIndex, setFocusedIndex] = useState(-1);

    // 当外部value改变时同步到inputValue
    useEffect(() => {
        setInputValue(value || '');
    }, [value]);

    // 过滤工程师列表
    const filteredEngineers = useMemo(() => {
        if (!inputValue.trim()) {
            return engineers;
        }

        const searchTerm = inputValue.toLowerCase();
        return engineers.filter((eng) =>
            eng.name.toLowerCase().includes(searchTerm)
        );
    }, [engineers, inputValue]);

    const handleInputChange = (e) => {
        const newValue = e.target.value;
        setInputValue(newValue);
        setShowDropdown(true);
        setFocusedIndex(-1);

        // 即时向父组件传递输入值
        if (onChange) {
            onChange(newValue);
        }
    };

    const handleSelectEngineer = (engineerName) => {
        setInputValue(engineerName);
        setShowDropdown(false);
        setFocusedIndex(-1);

        if (onChange) {
            onChange(engineerName);
        }
    };

    const handleKeyDown = (e) => {
        if (!showDropdown || filteredEngineers.length === 0) {
            return;
        }

        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                setFocusedIndex((prev) =>
                    prev < filteredEngineers.length - 1 ? prev + 1 : prev
                );
                break;

            case 'ArrowUp':
                e.preventDefault();
                setFocusedIndex((prev) => (prev > 0 ? prev - 1 : -1));
                break;

            case 'Enter':
                e.preventDefault();
                if (focusedIndex >= 0 && focusedIndex < filteredEngineers.length) {
                    handleSelectEngineer(filteredEngineers[focusedIndex].name);
                }
                break;

            case 'Escape':
                setShowDropdown(false);
                setFocusedIndex(-1);
                break;

            default:
                break;
        }
    };

    const handleFocus = () => {
        setShowDropdown(true);
    };

    const handleBlur = () => {
        // 延迟关闭下拉列表,允许点击事件���发
        setTimeout(() => {
            setShowDropdown(false);
            setFocusedIndex(-1);
        }, 200);
    };

    // 组合样式类名
    const inputClassName = `w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
        error || loadError ? 'border-red-500' : 'border-gray-300'
    } ${className}`;

    return (
        <div className="relative">
            <input
                type="text"
                value={inputValue}
                onChange={handleInputChange}
                onKeyDown={handleKeyDown}
                onFocus={handleFocus}
                onBlur={handleBlur}
                placeholder={placeholder}
                required={required}
                disabled={loading}
                className={inputClassName}
                autoComplete="off"
            />

            {/* 加载状态 */}
            {loading && (
                <div className="absolute right-3 top-3 text-gray-400">
                    <i className="fas fa-spinner fa-spin"></i>
                </div>
            )}

            {/* 下拉列表 */}
            {showDropdown && !loading && filteredEngineers.length > 0 && (
                <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-y-auto">
                    {filteredEngineers.map((engineer, index) => (
                        <div
                            key={engineer.user_id || engineer.name}
                            className={`px-3 py-2 cursor-pointer hover:bg-blue-50 ${
                                index === focusedIndex ? 'bg-blue-100' : ''
                            }`}
                            onClick={() => handleSelectEngineer(engineer.name)}
                        >
                            <div className="font-medium text-gray-900">{engineer.name}</div>
                            {engineer.user_id && (
                                <div className="text-xs text-gray-500">{engineer.user_id}</div>
                            )}
                        </div>
                    ))}
                </div>
            )}

            {/* 无匹配结果 */}
            {showDropdown && !loading && inputValue && filteredEngineers.length === 0 && (
                <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg p-3 text-center text-gray-500">
                    未找到匹配的工程师
                </div>
            )}

            {/* 错误信息 */}
            {(error || loadError) && (
                <p className="mt-1 text-sm text-red-600">{error || loadError}</p>
            )}
        </div>
    );
}

EngineerSelector.propTypes = {
    value: PropTypes.string,
    onChange: PropTypes.func.isRequired,
    error: PropTypes.string,
    placeholder: PropTypes.string,
    required: PropTypes.bool,
    className: PropTypes.string,
};
