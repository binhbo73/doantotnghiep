/**
 * Loading Skeletons for Department Detail Page
 */

export default function LoadingSkeletons() {
    return (
        <div className="min-h-screen bg-surface">
            <div className="max-w-7xl mx-auto px-6 py-8 space-y-6">
                {/* Breadcrumb */}
                <div className="h-4 bg-surface-container-low rounded w-32 animate-pulse" />

                {/* Header */}
                <div className="space-y-4">
                    <div className="h-10 bg-surface-container-low rounded w-2/3 animate-pulse" />
                    <div className="h-6 bg-surface-container-low rounded w-full animate-pulse" />
                    <div className="h-6 bg-surface-container-low rounded w-3/4 animate-pulse" />
                </div>

                {/* Manager Card */}
                <div className="p-6 bg-surface-container-low rounded-lg animate-pulse">
                    <div className="flex gap-4">
                        <div className="w-20 h-20 bg-surface-container-highest rounded-full" />
                        <div className="flex-1 space-y-2">
                            <div className="h-5 bg-surface-container-highest rounded w-2/3" />
                            <div className="h-4 bg-surface-container-highest rounded w-full" />
                            <div className="h-4 bg-surface-container-highest rounded w-3/4" />
                        </div>
                    </div>
                </div>

                {/* Sub-departments */}
                <div className="space-y-3">
                    <div className="h-7 bg-surface-container-low rounded w-1/4 animate-pulse" />
                    {[1, 2, 3].map((i) => (
                        <div key={i} className="h-24 bg-surface-container-low rounded-lg animate-pulse" />
                    ))}
                </div>

                {/* Tabs & Table */}
                <div className="space-y-4">
                    <div className="flex gap-4 border-b border-outline-variant pb-4">
                        {[1, 2, 3].map((i) => (
                            <div key={i} className="h-6 bg-surface-container-low rounded w-20 animate-pulse" />
                        ))}
                    </div>
                    <div className="space-y-3">
                        {[1, 2, 3].map((i) => (
                            <div key={i} className="h-16 bg-surface-container-low rounded-lg animate-pulse" />
                        ))}
                    </div>
                </div>

                {/* Info Cards */}
                <div className="grid grid-cols-3 gap-6">
                    {[1, 2, 3].map((i) => (
                        <div key={i} className="h-40 bg-surface-container-low rounded-lg animate-pulse" />
                    ))}
                </div>
            </div>
        </div>
    );
}
