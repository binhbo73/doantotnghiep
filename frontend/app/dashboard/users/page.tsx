'use client'

export default function UsersPage() {
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
                        👥 Quản lý người
                    </h1>
                    <p
                        className="text-sm"
                        style={{ color: '#727785' }}
                    >
                        Quản lý người dùng, phân quyền và cấu hình tài khoản
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
                        🚧 Trang Quản lý người
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
