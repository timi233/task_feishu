/**
 * Render a centered loading spinner with optional status text.
 * @param {Object} props Component props.
 * @param {string} [props.message='正在加载派工数据...'] Text displayed below the spinner.
 */
export default function LoadingSpinner({ message = '正在加载派工数据...' }) {
    return (
        <div className="text-center">
            <div className="spinner" />
            <p>{message}</p>
        </div>
    );
}
