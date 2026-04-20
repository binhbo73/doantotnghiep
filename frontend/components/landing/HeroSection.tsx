import { ArrowRight } from 'lucide-react'

export function HeroSection() {
    return (
        <section className="relative flex min-h-[921px] items-center overflow-hidden px-6 pt-20">
            <div className="absolute inset-0 -z-10 bg-[#f8f9ff]" />
            <div className="mx-auto grid w-full max-w-7xl grid-cols-12 items-center gap-6">
                <div className="col-span-12 space-y-8 py-20 lg:col-span-7">
                    <div className="inline-flex items-center gap-2 rounded-full bg-[#ffdbca] px-3 py-1 text-xs font-bold uppercase tracking-widest text-[#9d4300]">
                        ✓
                        NEXUS SOLUTIONS PREMIUM
                    </div>
                    <h1 className="max-w-4xl text-5xl font-extrabold leading-[1.1] tracking-tight text-[#0d1c2e] lg:text-7xl">
                        Hệ điều hành <span className="text-[#f97316]">Tri thức</span> Doanh nghiệp
                    </h1>
                    <p className="max-w-xl text-xl leading-relaxed text-[#584237]">
                        Quản trị thông minh, Bảo mật nội bộ. Chuyển đổi dữ liệu thô thành tài sản tri thức sống động với AI dành riêng cho tổ chức của bạn.
                    </p>
                    <div className="flex flex-wrap gap-4 pt-4">
                        <button className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-[#9d4300] to-[#f97316] px-8 py-4 font-bold text-white shadow-xl shadow-[#f97316]/25 transition-all hover:translate-y-[-2px]">
                            Trải nghiệm Ngay
                            <ArrowRight className="h-5 w-5" />
                        </button>
                        <button className="rounded-xl bg-[#eff4ff] px-8 py-4 font-semibold text-[#0d1c2e] transition-colors hover:bg-[#dce9ff] border border-[#e0c0b1]/20">
                            Gói Enterprise (Doanh nghiệp)
                        </button>
                    </div>
                    <div className="flex items-center gap-12 pt-8">
                        <div>
                            <p className="text-3xl font-black text-[#0d1c2e]">10,000+</p>
                            <p className="text-sm font-medium text-[#584237]">Tài liệu được quản lý</p>
                        </div>
                        <div className="h-10 w-px bg-[#e0c0b1]/30" />
                        <div>
                            <p className="text-3xl font-black text-[#0d1c2e]">99.9%</p>
                            <p className="text-sm font-medium text-[#584237]">Thời gian hoạt động</p>
                        </div>
                    </div>
                </div>

                <div className="relative col-span-12 hidden lg:block lg:col-span-5">
                    <div className="relative z-10 aspect-square rounded-3xl border border-white/40 bg-white/70 backdrop-blur-md p-8 shadow-[0_32px_64px_rgba(157,67,0,0.06)]">
                        <img
                            alt="AI Interface"
                            className="h-full w-full rounded-2xl object-cover shadow-inner"
                            src="https://lh3.googleusercontent.com/aida-public/AB6AXuBcj3OReSjkW0E4vELaGooZPGOXqDXi3lyQ3Vq1xi2ViQXD8R1jVCiphWU_JA0Cka1ZCTka38DyNcfFaK1wC056jI_AnrszrcJyC1jFY6XA7mZwnT2gWvqum_3GRUloT6L06svBUq3VNcmv4RnS9kvXQTEBb2qgK7B6yKG4oo2psKQcGgpFfi9E64FqCaM-sm7lT5cxhPi36sIMkxHrVhEG3IZNEzo8YDYZRkusQICoo3Lz3ThrfIQ0y2GwqvsnMevTJBH72cFwzIQ"
                        />
                    </div>
                    <div className="absolute -right-12 -top-12 -z-10 h-64 w-64 rounded-full bg-[#ffdbca]/20 blur-[100px]" />
                    <div className="absolute -bottom-12 -left-12 -z-10 h-64 w-64 rounded-full bg-[#cde5ff]/20 blur-[100px]" />
                </div>
            </div>
        </section>
    )
}
