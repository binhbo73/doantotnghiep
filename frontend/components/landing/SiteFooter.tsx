export function SiteFooter() {
    return (
        <footer className="w-full border-t border-[#e0c0b1]/20 bg-white py-8">
            <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 px-6 md:flex-row">
                <span className="font-sans text-xs font-medium text-[#8c7164] antialiased">
                    © 2024 Enterprise Knowledge OS. Nexus Solutions. Bảo lưu mọi quyền.
                </span>
                <div className="flex items-center gap-6">
                    {['Quy định bảo mật', 'Điều khoản sử dụng', 'Bảo mật', 'Trạng thái'].map((link) => (
                        <a
                            key={link}
                            className="font-sans text-xs font-medium text-[#8c7164] transition-colors hover:text-[#f97316] antialiased"
                            href="#"
                        >
                            {link}
                        </a>
                    ))}
                </div>
            </div>
        </footer>
    )
}
