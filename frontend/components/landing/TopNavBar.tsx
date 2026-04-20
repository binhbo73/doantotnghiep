import Link from 'next/link'

export function TopNavBar() {
    return (
        <nav className="fixed top-0 z-50 w-full bg-white/80 backdrop-blur-md border-b border-[#e0c0b1]/20">
            <div className="mx-auto flex h-16 w-full max-w-7xl items-center justify-between px-6">
                <div className="flex items-center gap-8">
                    <span className="text-xl font-bold tracking-tight text-[#0d1c2e]">
                        Enterprise Knowledge OS
                    </span>
                    <div className="hidden items-center gap-6 md:flex">
                        <a
                            href="#features"
                            className="border-b-2 border-[#f97316] py-1 text-sm font-semibold text-[#f97316] antialiased"
                        >
                            Tính năng
                        </a>
                        <a
                            href="#about"
                            className="text-sm font-medium text-[#584237] transition-colors hover:text-[#0d1c2e]"
                        >
                            Giới thiệu
                        </a>
                    </div>
                </div>
                <div className="flex items-center gap-4">
                    <Link href="/login" className="px-4 py-2 text-sm font-medium text-[#584237] transition-colors duration-200 hover:text-[#0d1c2e]">
                        Đăng nhập
                    </Link>
                    <Link href="/login" className="rounded-xl bg-[#f97316] px-5 py-2.5 text-sm font-bold text-white shadow-lg shadow-[#f97316]/20 transition-all duration-200 hover:translate-y-[-2px] hover:shadow-[#f97316]/30">
                        Bắt đầu
                    </Link>
                </div>
            </div>
        </nav>
    )
}
