'use client'

export default function ProjectsPage() {
    return (
        <main
            className="min-h-screen p-6"
            style={{ backgroundColor: '#f9f9ff' }}
        >
            <div className="max-w-7xl mx-auto">
                {/* Header */}
                <div className="mb-8">
                    <h1
                        className="text-3xl font-bold mb-2"
                        style={{ color: '#151c27' }}
                    >
                        📋 Dự án
                    </h1>
                    <p
                        className="text-sm"
                        style={{ color: '#727785' }}
                    >
                        Theo dõi và quản lý các dự án trong tổ chức
                    </p>
                </div>

                {/* Content Placeholder */}
                <div
                    className="rounded-lg p-12 text-center"
                    style={{
                        backgroundColor: '#ffffff',
                        border: '2px dashed #dce2f3',
                    }}
                >
                    <p
                        className="text-lg font-semibold mb-2"
                        style={{ color: '#151c27' }}
                    >
                        🚧 Trang Dự án
                    </p>
                    <p
                        style={{ color: '#727785' }}
                    >
                        Chức năng này đang được phát triển...
                    </p>
                </div>
            </div>
        </main>
    )
}
