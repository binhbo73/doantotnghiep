export function FinalCTA() {
    return (
        <section className="mb-24 px-6 py-24">
            <div className="mx-auto max-w-7xl">
                <div className="relative overflow-hidden rounded-[2.5rem] bg-gradient-to-br from-[#9d4300] to-[#f97316] p-12 lg:p-24">
                    <div className="absolute inset-0 bg-gradient-to-br from-[#f97316] to-[#006398] mix-blend-multiply opacity-20" />
                    <div className="relative z-10 space-y-8 text-center">
                        <h2 className="text-4xl font-black leading-tight tracking-tight text-white lg:text-6xl">
                            Sẵn sàng kiến tạo thông minh của bạn?
                        </h2>
                        <p className="mx-auto max-w-2xl text-xl leading-relaxed text-white/80">
                            Tham gia 500+ doanh nghiệp triển khai hệ thống kiến thức cục bộ để có tốc độ và bảo mật chưa từng có.
                        </p>
                        <div className="flex flex-col items-center justify-center gap-6 pt-4 sm:flex-row">
                            <button className="w-full rounded-2xl bg-white px-10 py-5 font-extrabold text-[#9d4300] transition-all hover:scale-105 hover:bg-white/90 active:scale-95 sm:w-auto">
                                Bắt đầu Dùng thử miễn phí
                            </button>
                            <button className="w-full rounded-2xl border-2 border-white/30 px-10 py-5 font-bold text-white transition-all hover:bg-white/10 sm:w-auto">
                                Lên lịch Demo
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </section>
    )
}
