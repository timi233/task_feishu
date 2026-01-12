import { useState } from 'react';
import PropTypes from 'prop-types';

/**
 * ConfirmDialog - 通用确认对话框组件
 *
 * 功能:
 * - 模态弹窗确认操作
 * - 可选输入框(用于填写原因/备注)
 * - 自定义标题、消息、按钮文本
 * - 遮罩层点击关闭
 *
 * Props:
 * - isOpen: 是否显示
 * - onClose: 关闭回调
 * - onConfirm: 确认回调 (inputValue) => void
 * - title: 对话框标题
 * - message: 提示消息
 * - confirmText: 确认按钮文本
 * - cancelText: 取消按钮文本
 * - showInput: 是否显示输入框
 * - inputPlaceholder: 输入框占位符
 * - confirmButtonClass: 确认按钮样式类(用于区分危险/普通操作)
 */
export default function ConfirmDialog({
    isOpen,
    onClose,
    onConfirm,
    title = '确认操作',
    message = '确定要执行此操作吗?',
    confirmText = '确认',
    cancelText = '取消',
    showInput = false,
    inputPlaceholder = '请输入备注(可选)',
    confirmButtonClass = 'bg-blue-600 hover:bg-blue-700',
}) {
    const [inputValue, setInputValue] = useState('');

    if (!isOpen) {
        return null;
    }

    const handleConfirm = () => {
        onConfirm(showInput ? inputValue : undefined);
        setInputValue(''); // 重置输入
    };

    const handleClose = () => {
        setInputValue(''); // 重置输入
        onClose();
    };

    const handleOverlayClick = (e) => {
        if (e.target === e.currentTarget) {
            handleClose();
        }
    };

    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/60 px-4"
            onClick={handleOverlayClick}
        >
            <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
                {/* 标题 */}
                <h3 className="text-lg font-semibold text-gray-900 mb-3">{title}</h3>

                {/* 消息 */}
                <p className="text-sm text-gray-600 mb-4">{message}</p>

                {/* 可选输入框 */}
                {showInput && (
                    <textarea
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                        placeholder={inputPlaceholder}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 mb-4 resize-none"
                        rows={3}
                        autoFocus
                    />
                )}

                {/* 按钮组 */}
                <div className="flex justify-end space-x-3">
                    <button
                        type="button"
                        onClick={handleClose}
                        className="inline-flex items-center rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition hover:bg-gray-50"
                    >
                        {cancelText}
                    </button>
                    <button
                        type="button"
                        onClick={handleConfirm}
                        className={`inline-flex items-center rounded-md px-4 py-2 text-sm font-semibold text-white transition ${confirmButtonClass}`}
                    >
                        {confirmText}
                    </button>
                </div>
            </div>
        </div>
    );
}

ConfirmDialog.propTypes = {
    isOpen: PropTypes.bool.isRequired,
    onClose: PropTypes.func.isRequired,
    onConfirm: PropTypes.func.isRequired,
    title: PropTypes.string,
    message: PropTypes.string,
    confirmText: PropTypes.string,
    cancelText: PropTypes.string,
    showInput: PropTypes.bool,
    inputPlaceholder: PropTypes.string,
    confirmButtonClass: PropTypes.string,
};
