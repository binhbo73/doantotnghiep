// components/layouts/MainLayout.tsx - Main app layout
import { Header, Sidebar } from '@/components/common'

export function MainLayout({ children }: { children: React.ReactNode }) {
    return (
        <div className="flex h-screen">
            <Sidebar />
            <div className="flex-1 flex flex-col">
                <Header />
                <main className="flex-1 overflow-auto">{children}</main>
            </div>
        </div>
    )
}
