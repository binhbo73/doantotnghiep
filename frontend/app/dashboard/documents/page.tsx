'use client'

export default function DocumentsPage() {
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
                        📁 Kho tài liệu
                    </h1>
                    <p
                        className="text-sm"
                        style={{ color: '#727785' }}
                    >
                        Quản lý và tìm kiếm tất cả tài liệu trong hệ thống
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
                        🚧 Trang Kho tài liệu
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
