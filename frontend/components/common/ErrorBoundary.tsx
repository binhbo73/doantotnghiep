/**
 * Error Boundary Component
 * Catches and displays errors
 */

interface ErrorBoundaryProps {
    error: string | null;
    onRetry?: () => void;
}

export default function ErrorBoundary({ error, onRetry }: ErrorBoundaryProps) {
    return (
        <div className="min-h-screen flex items-center justify-center bg-surface">
            <div className="max-w-md w-full p-6 bg-error-container rounded-lg text-center">
                <h2 className="text-2xl font-bold text-error mb-2">
                    ⚠️ Đã xảy ra lỗi
                </h2>
                <p className="text-body-md text-error mb-6">
                    {error || 'Lỗi không xác định'}
                </p>
                {onRetry && (
                    <button
                        onClick={onRetry}
                        className="px-6 py-3 bg-error text-on-error rounded-lg hover:bg-error_container transition-colors font-medium"
                    >
                        Thử lại
                    </button>
                )}
            </div>
        </div>
    );
}
