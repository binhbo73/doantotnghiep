/**
 * Tab Loading Skeleton
 */

export default function TabLoading() {
    return (
        <div className="space-y-3 animate-pulse">
            {[1, 2, 3, 4, 5].map((i) => (
                <div
                    key={i}
                    className="h-16 bg-surface-container-low rounded-lg"
                />
            ))}
        </div>
    );
}
