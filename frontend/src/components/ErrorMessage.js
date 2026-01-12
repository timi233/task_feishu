/**
 * Present an error alert with optional retry control.
 * @param {Object} props Component props.
 * @param {string} [props.title='加载失败!'] Bold label summarising the error.
 * @param {string} props.message Detailed error description.
 * @param {Function} [props.onRetry] Optional callback rendered as an action button.
 * @param {string} [props.retryLabel='重试'] Text shown on the retry button.
 */
export default function ErrorMessage({
    title = '加载失败!',
    message,
    onRetry,
    retryLabel = '重试',
}) {
    return (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
            <strong className="font-bold mr-2">{title}</strong>
            <span className="block sm:inline">{message}</span>
            {onRetry && (
                <button
                    type="button"
                    onClick={onRetry}
                    className="mt-3 inline-flex items-center bg-red-500 hover:bg-red-600 text-white font-medium px-3 py-1 rounded"
                >
                    <i className="fas fa-sync-alt mr-2" />
                    {retryLabel}
                </button>
            )}
        </div>
    );
}
