import type { LucideIcon } from 'lucide-react'
import { Bolt, MessageSquareText, Server, Database, ShieldCheck } from 'lucide-react'

const featureImages = {
    smartSearch:
        'https://lh3.googleusercontent.com/aida-public/AB6AXuDh8PeWmrqAdk7AJ-iqz8tgdqmlktsYaHGQC9GscXVZYc_DXmaLi9ihF2_0I8n2sM_KVHZq56asL6ozSPtImr7SkDrOjg3pNV1JLmdt08OsoeSrvOu8C63xrwupxOe_D1H-POPJrmInT-HMytayEV9q_R18JQAGQ-RTxf3-_rRZbbiFX42VgtIGPDSE0DNXOrlxjDSxQS9M_GDB5QwYlyTOoyyO6nclZSiMNJi3ABnniXn1MR6ZAdfNA-VHjC4G199hGMwBcc3cGCk',
}

function FeatureIcon({ icon: Icon, className }: { icon: LucideIcon; className?: string }) {
    return <Icon className={className} />
}

export function FeaturesBentoGrid() {
    return (
        <section className="bg-[#eff4ff] px-6 py-24">
            <div className="mx-auto max-w-7xl">
                <div className="mb-16 space-y-4 text-center">
                    <h2 className="text-4xl font-extrabold tracking-tight text-[#0d1c2e]">
                        Sức mạnh Trí thức Tập trung
                    </h2>
                    <p className="mx-auto max-w-2xl text-[#584237]">
                        Giải pháp Co-promise tối ưu cho bảo mật và hiệu năng.
                    </p>
                </div>

                <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
                    <div className="group md:col-span-2 rounded-3xl border border-[#e0c0b1]/10 bg-white p-10 shadow-sm transition-all hover:shadow-md">
                        <div className="flex h-full flex-col justify-between gap-12">
                            <div className="space-y-4">
                                <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[#f97316]/10">
                                    <FeatureIcon icon={Bolt} className="h-8 w-8 text-[#f97316]" />
                                </div>
                                <h3 className="text-2xl font-bold text-[#0d1c2e]">Tìm kiếm thông minh</h3>
                                <p className="text-lg leading-relaxed text-[#584237]">
                                    Lập chỉ mục ngữ nghĩa hiểu được ngữ cảnh, không chỉ từ khóa. Tìm bất cứ thứ gì trên toàn bộ kho dữ liệu của bạn trong milli giây.
                                </p>
                            </div>
                            <img
                                alt="Smart Search"
                                className="h-48 w-full rounded-xl object-cover shadow-lg transition-transform group-hover:scale-[1.02]"
                                src={featureImages.smartSearch}
                            />
                        </div>
                    </div>

                    <div className="flex flex-col justify-between rounded-3xl bg-gradient-to-br from-[#9d4300] to-[#f97316] p-10 text-white shadow-xl shadow-[#f97316]/20">
                        <div className="space-y-4">
                            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-white/20">
                                <FeatureIcon icon={ShieldCheck} className="h-8 w-8 text-white" />
                            </div>
                            <h3 className="text-2xl font-bold">Truy cập an toàn</h3>
                            <p className="text-white/80">
                                Quản lý danh tính được mã hóa end-to-end với xác thực sinh trắc học và hỗ trợ khóa bảo mật phần cứng.
                            </p>
                        </div>
                        <div className="mt-8 flex -space-x-3">
                            <div className="flex h-10 w-10 items-center justify-center rounded-full border-2 border-white/50 bg-white/10 text-[10px] font-bold">
                                RSA
                            </div>
                            <div className="flex h-10 w-10 items-center justify-center rounded-full border-2 border-white/50 bg-white/20 text-[10px] font-bold">
                                AES
                            </div>
                            <div className="flex h-10 w-10 items-center justify-center rounded-full border-2 border-white/50 bg-white/30 text-[10px] font-bold">
                                E2E
                            </div>
                        </div>
                    </div>

                    <div className="flex flex-col justify-between rounded-3xl border border-[#e0c0b1]/10 bg-white p-10">
                        <div className="space-y-4">
                            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[#006398]/10">
                                <FeatureIcon icon={MessageSquareText} className="h-8 w-8 text-[#006398]" />
                            </div>
                            <h3 className="text-2xl font-bold text-[#0d1c2e]">Chat nhanh</h3>
                            <p className="text-[#584237]">
                                Giao diện AI hợp tác thời gian thực sống cùng với tài liệu của bạn. Cuộc hội thoại nhận thức ngữ cảnh.
                            </p>
                        </div>
                        <div className="mt-8 rounded-xl border border-[#e0c0b1]/10 bg-[#eff4ff] p-4">
                            <div className="mb-2 h-2 w-3/4 rounded bg-[#f97316]/20" />
                            <div className="h-2 w-1/2 rounded bg-[#c2c6d6]/30" />
                        </div>
                    </div>

                    <div className="relative overflow-hidden rounded-3xl bg-[#2a313d] p-10 text-[#ebf1ff] md:col-span-2">
                        <div className="relative z-10 max-w-md space-y-4">
                            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-white/10">
                                <FeatureIcon icon={Database} className="h-8 w-8 text-white" />
                            </div>
                            <h3 className="text-2xl font-bold">Local Only</h3>
                            <p className="text-slate-400">
                                Your data never leaves your premises. Deploy on your own infrastructure with zero cloud dependencies for maximum privacy compliance.
                            </p>
                        </div>
                        <div className="absolute bottom-0 right-0 opacity-20">
                            <FeatureIcon icon={Server} className="h-[200px] w-[200px] text-white" />
                        </div>
                    </div>
                </div>
            </div>
        </section>
    )
}
