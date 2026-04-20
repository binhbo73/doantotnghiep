'use client'

import Link from 'next/link'

export default function HomePage() {
    return (
        <main className="min-h-screen bg-[#f8f9ff] text-[#0d1c2e]" style={{ fontFamily: 'Inter, sans-serif' }}>
            {/* Navigation */}
            <nav className="fixed top-0 z-50 w-full bg-white/80 backdrop-blur-md border-b border-[#e0c0b1]/20">
                <div className="flex justify-between items-center px-8 py-4 w-full max-w-screen-2xl mx-auto ml-auto mr-auto">
                    <div className="flex items-center gap-8">
                        <span className="text-xl font-bold tracking-tighter text-[#0d1c2e]">
                            Enterprise Knowledge OS
                        </span>
                        <div className="hidden md:flex gap-6 items-center">
                            <a href="#features" className="text-[#f97316] font-semibold border-b-2 border-[#f97316] pb-1 text-sm">Tính năng</a>
                            <a href="#about" className="text-[#584237] hover:text-[#0d1c2e] hover:bg-slate-100/50 transition-colors duration-300 text-sm">Giới thiệu</a>
                        </div>
                    </div>
                    <div className="flex items-center gap-4">
                        <Link href="/login" className="px-4 py-2 text-[#584237] hover:bg-slate-100/50 transition-colors duration-300 active:scale-95 text-sm">Đăng nhập</Link>
                        <Link href="/login" className="px-6 py-2 bg-[#f97316] text-white font-semibold rounded-lg hover:shadow-lg active:scale-95 transition-all text-sm">Bắt đầu</Link>
                    </div>
                </div>
            </nav>

            {/* Hero Section */}
            <section className="relative min-h-[870px] flex items-center px-8 overflow-hidden pt-20">
                <div className="max-w-screen-2xl mx-auto w-full grid grid-cols-1 lg:grid-cols-2 gap-12 items-center relative z-10">
                    <div className="space-y-8">
                        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#ffdbca] text-[#9d4300] text-xs font-bold uppercase tracking-wider">
                            ✓ Nexus Solutions Premium
                        </div>
                        <h1 className="text-6xl md:text-7xl font-extrabold tracking-tighter leading-[1.1] text-[#0d1c2e]">
                            Hệ điều hành <span className="text-[#9d4300]">Tri thức</span> Doanh nghiệp
                        </h1>
                        <p className="text-xl text-[#584237] max-w-xl leading-relaxed">
                            Quản trị thông minh, Bảo mật nội bộ. Chuyển đổi dữ liệu thô thành tài sản tri thức sống động với AI dành riêng cho tổ chức của bạn.
                        </p>
                        <div className="flex flex-wrap gap-4">
                            <button className="px-8 py-4 bg-gradient-to-r from-[#9d4300] to-[#f97316] text-white rounded-xl font-bold text-lg shadow-xl shadow-[#9d4300]/20 hover:opacity-90 active:scale-95 transition-all">
                                Trải nghiệm Ngay
                            </button>
                            <div className="flex items-center gap-3 px-6 py-4 rounded-xl bg-[#eff4ff] border border-[#e0c0b1]/20">
                                <span className="text-[#9d4300]">🏢</span>
                                <div>
                                    <p className="text-[10px] uppercase font-bold text-[#584237]">Gói dịch vụ</p>
                                    <p className="text-sm font-bold text-[#0d1c2e]">Gói Enterprise (Doanh nghiệp)</p>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="relative hidden lg:block">
                        <div className="absolute -top-20 -right-20 w-96 h-96 bg-[#9d4300]/10 rounded-full blur-3xl"></div>
                        <div className="relative glass-card p-4 rounded-3xl overflow-hidden shadow-2xl">
                            <img alt="UI Dashboard Preview" className="w-full aspect-[4/3] object-cover rounded-2xl"
                                src="https://lh3.googleusercontent.com/aida-public/AB6AXuBcj3OReSjkW0E4vELaGooZPGOXqDXi3lyQ3Vq1xi2ViQXD8R1jVCiphWU_JA0Cka1ZCTka38DyNcfFaK1wC056jI_AnrszrcJyC1jFY6XA7mZwnT2gWvqum_3GRUloT6L06svBUq3VNcmv4RnS9kvXQTEBb2qgK7B6yKG4oo2psKQcGgpFfi9E64FqCaM-sm7lT5cxhPi36sIMkxHrVhEG3IZNEzo8YDYZRkusQICoo3Lz3ThrfIQ0y2GwqvsnMevTJBH72cFwzIQ" />
                            <div className="absolute bottom-8 left-8 right-8 glass-card p-6 rounded-2xl flex items-center justify-between">
                                <div className="flex gap-4 items-center">
                                    <div className="w-12 h-12 rounded-full bg-[#9d4300] flex items-center justify-center text-white">
                                        ⭐
                                    </div>
                                    <div>
                                        <p className="text-xs text-[#584237]">Trạng thái hệ thống</p>
                                        <p className="font-bold text-[#0d1c2e]">AI Đang sẵn sàng</p>
                                    </div>
                                </div>
                                <div className="flex -space-x-3">
                                    <div className="w-8 h-8 rounded-full border-2 border-white bg-slate-200"></div>
                                    <div className="w-8 h-8 rounded-full border-2 border-white bg-slate-300"></div>
                                    <div className="w-8 h-8 rounded-full border-2 border-white bg-slate-400"></div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* Features Section */}
            <section className="py-24 px-8 bg-[#eff4ff]">
                <div className="max-w-screen-2xl mx-auto">
                    <div className="text-center mb-16 space-y-4">
                        <h2 className="text-4xl font-extrabold tracking-tight text-[#0d1c2e]">Sức mạnh Tri thức Tập trung</h2>
                        <p className="text-[#584237]">Giải pháp On-premise tối ưu cho bảo mật và hiệu suất</p>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-12 gap-6 h-auto md:h-[600px]">
                        <div className="md:col-span-4 bg-white p-8 rounded-[2rem] shadow-sm flex flex-col justify-between group hover:shadow-xl transition-all border border-[#e0c0b1]/10">
                            <div className="w-16 h-16 rounded-2xl bg-orange-50 flex items-center justify-center text-[#9d4300] group-hover:bg-[#9d4300] group-hover:text-white transition-colors text-3xl">
                                🔍
                            </div>
                            <div>
                                <h3 className="text-2xl font-bold mb-3 text-[#0d1c2e]">Tìm kiếm thông minh</h3>
                                <p className="text-[#584237] leading-relaxed">Truy vấn ngữ nghĩa trên toàn bộ kho tài liệu của doanh nghiệp với độ chính xác tuyệt đối.</p>
                            </div>
                        </div>
                        <div className="md:col-span-8 bg-gradient-to-br from-[#9d4300] to-orange-700 p-8 rounded-[2rem] text-white flex flex-col justify-center relative overflow-hidden">
                            <div className="relative z-10">
                                <h3 className="text-3xl font-bold mb-4">Trò chuyện AI nhanh</h3>
                                <p className="text-orange-100 text-lg max-w-lg mb-8">Trợ lý ảo thông minh hiểu rõ cấu trúc tổ chức và quy trình nội bộ của bạn. Phản hồi tức thì, chính xác.</p>
                                <button className="px-6 py-3 bg-white text-[#9d4300] font-bold rounded-xl hover:bg-orange-50 transition-colors">Thử nghiệm AI Chat</button>
                            </div>
                            <span className="absolute -right-10 -bottom-10 text-[20rem] opacity-10 pointer-events-none">⚡</span>
                        </div>
                        <div className="md:col-span-7 bg-[#dce9ff] p-8 rounded-[2rem] flex items-center gap-8 border border-[#e0c0b1]/20">
                            <div className="flex-1">
                                <h3 className="text-2xl font-bold mb-3 text-[#0d1c2e]">Lưu trữ nội bộ</h3>
                                <p className="text-[#584237]">Dữ liệu không bao giờ rời khỏi hạ tầng của bạn. Đảm bảo tuân thủ các quy định bảo mật khắt khe nhất.</p>
                            </div>
                            <div className="hidden sm:block w-48">
                                <img alt="Server" className="rounded-2xl grayscale hover:grayscale-0 transition-all duration-500"
                                    src="https://lh3.googleusercontent.com/aida-public/AB6AXuAvi9eCQifPTb0VnvbvVDGOj69zFo5RbLywxrgY3TG56i_iw6issOzHIE3orbVjlCBhJRm08wli4XEr5UzjHUmNpiKnaivUB9A4QvbhnAoBgmkNfR7Atszg06lYaGLCFxKTCGd-CVop8ScVmKaEykmH8esG_xrgLZB5cK0mUKYmvd6CVZsUahaTf-rymmbIMvnbxlsFGXNVb66y6j2-Y7I9Xo3FJF4mELRQh2IuhHrVjdpIF1I9p_IwAoW8GfZ0D1NVYhg3jmSbMtk" />
                            </div>
                        </div>
                        <div className="md:col-span-5 bg-white p-8 rounded-[2rem] shadow-sm flex flex-col justify-center border border-[#e0c0b1]/10">
                            <div className="flex items-center gap-4 mb-6">
                                <span className="text-[#9d4300] p-3 bg-orange-50 rounded-full text-3xl">🔒</span>
                                <h3 className="text-2xl font-bold text-[#0d1c2e]">Truy cập an toàn</h3>
                            </div>
                            <p className="text-[#584237]">Phân quyền đa cấp (RBAC), mã hóa đầu cuối và xác thực đa nhân tố tích hợp sẵn.</p>
                        </div>
                    </div>
                </div>
            </section>

            {/* Process Section */}
            <section className="py-24 px-8 bg-[#f8f9ff]">
                <div className="max-w-screen-xl mx-auto">
                    <div className="text-center mb-20">
                        <h2 className="text-4xl font-extrabold tracking-tight mb-4 text-[#0d1c2e]">Luồng hoạt động tối giản</h2>
                        <div className="w-20 h-1 bg-[#9d4300] mx-auto rounded-full"></div>
                    </div>
                    <div className="flex flex-col md:flex-row gap-12 justify-between items-center relative">
                        <div className="hidden md:block absolute top-1/2 left-0 w-full h-[1px] bg-[#e0c0b1]/30 -z-10"></div>
                        {[
                            { icon: '📤', title: 'Tải tài liệu', desc: 'Hỗ trợ PDF, Docx, Wiki, và cơ sở dữ liệu SQL.' },
                            { icon: '🧠', title: 'AI xử lý', desc: 'Tự động phân loại, tóm tắt và nhúng vào không gian vector.' },
                            { icon: '💬', title: 'Tra cứu & Trò chuyện', desc: 'Tìm kiếm câu trả lời ngay lập tức dựa trên dữ liệu thật.' }
                        ].map((step, idx) => (
                            <div key={idx} className="flex flex-col items-center text-center max-w-[280px] bg-[#f8f9ff] p-6 rounded-3xl">
                                <div className={`w-20 h-20 rounded-full flex items-center justify-center mb-6 text-3xl ${idx === 1 ? 'bg-[#9d4300] shadow-xl shadow-[#9d4300]/30' : 'bg-white shadow-xl border border-[#9d4300]/20'}`}>
                                    {step.icon}
                                </div>
                                <h4 className="text-xl font-bold mb-2 text-[#0d1c2e]">{step.title}</h4>
                                <p className="text-sm text-[#584237]">{step.desc}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Company Info Section */}
            <section className="py-24 px-8 border-t border-[#e0c0b1]/10">
                <div className="max-w-screen-2xl mx-auto flex flex-col md:flex-row justify-between items-end gap-12">
                    <div className="space-y-6">
                        <h2 className="text-3xl font-bold text-[#0d1c2e]">Về chúng tôi</h2>
                        <div className="space-y-4">
                            <div className="flex items-center gap-4">
                                <span className="text-2xl">🏢</span>
                                <span className="text-lg font-medium text-[#0d1c2e]">Nexus Solutions</span>
                            </div>
                            <div className="flex items-center gap-4 text-[#584237]">
                                <span className="text-2xl">📋</span>
                                <span>Mã số thuế: 0101234567</span>
                            </div>
                            <div className="flex items-center gap-4 text-[#584237]">
                                <span className="text-2xl">📍</span>
                                <span>Tòa nhà TechHub, Quận 1, TP. Hồ Chí Minh</span>
                            </div>
                        </div>
                    </div>
                    <div className="w-full md:w-1/3">
                        <div className="bg-[#d5e3fc] p-8 rounded-3xl relative overflow-hidden">
                            <div className="relative z-10">
                                <p className="text-sm font-bold text-[#9d4300] mb-2">Hệ thống Tri thức</p>
                                <h3 className="text-xl font-bold mb-4 text-[#0d1c2e]">Sẵn sàng để bắt đầu?</h3>
                                <button className="w-full py-4 bg-[#9d4300] text-white font-bold rounded-xl hover:bg-opacity-90 transition-all">Liên hệ Tư vấn</button>
                            </div>
                            <span className="absolute -right-4 -bottom-4 text-8xl opacity-10">🏛️</span>
                        </div>
                    </div>
                </div>
            </section>

            {/* Footer */}
            <footer className="bg-white w-full py-12 px-8 border-t border-[#e0c0b1]/10">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-screen-2xl mx-auto">
                    <div className="space-y-4">
                        <p className="font-semibold text-[#0d1c2e] text-base">Enterprise Knowledge OS</p>
                        <p className="text-[#8c7164] text-xs">© 2024 Enterprise Knowledge OS. Bản quyền đã được bảo hộ.</p>
                    </div>
                    <div className="flex flex-wrap gap-x-8 gap-y-2 md:justify-end items-center">
                        <a className="text-[#8c7164] hover:text-[#0d1c2e] hover:underline text-xs transition-opacity duration-200" href="#">Chính sách bảo mật</a>
                        <a className="text-[#8c7164] hover:text-[#0d1c2e] hover:underline text-xs transition-opacity duration-200" href="#">Điều khoản dịch vụ</a>
                        <a className="text-[#8c7164] hover:text-[#0d1c2e] hover:underline text-xs transition-opacity duration-200" href="#">Liên hệ</a>
                    </div>
                </div>
            </footer>
        </main>
    )
}
