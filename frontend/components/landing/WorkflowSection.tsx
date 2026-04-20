import { ChevronRight } from 'lucide-react'

const steps = [
    {
        number: '01',
        title: 'Tiếp nhận & Ánh xạ',
        description:
            'Kết nối kho lưu trữ của bạn - Drive, Slack, Notion, hoặc Ổ cứng cục bộ. Công cụ của chúng tôi tự động ánh xạ các mối quan hệ và phân cấp mà không di chuyển tệp.',
    },
    {
        number: '02',
        title: 'Nhúng ngữ nghĩa',
        description:
            'Kiến trúc Nhận thức tạo các phép nhúng vectơ chiều cao của mọi điểm dữ liệu cục bộ, đảm bảo bí mật độc quyền của bạn vẫn là bí mật.',
    },
    {
        number: '03',
        title: 'Trò chuyện & Truy vấn',
        description:
            'Truy cập kiến thức của bạn thông qua giao diện ngôn ngữ tự nhiên. Đặt những câu hỏi phức tạp, tạo báo cáo và khám phá các mẫu ẩn trong lịch sử của bạn.',
    },
]

export function WorkflowSection() {
    return (
        <section className="px-6 py-24 bg-[#f8f9ff]">
            <div className="mx-auto max-w-7xl">
                <div className="flex flex-col items-start gap-16 md:flex-row">
                    <div className="w-full space-y-6 md:sticky md:top-32 md:w-1/3">
                        <h2 className="text-4xl font-extrabold tracking-tight text-[#0d1c2e]">
                            Luồng hoạt động tổng quát
                        </h2>
                        <p className="leading-relaxed text-[#584237]">
                            Ba bước đơn giản để biến dữ liệu thô của bạn thành biểu đồ kiến thức có thể hành động được.
                        </p>
                        <div className="pt-6">
                            <button className="group flex items-center gap-2 font-bold text-[#f97316]">
                                Đọc bản giấy trắng đầy đủ
                                <ChevronRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
                            </button>
                        </div>
                    </div>

                    <div className="w-full space-y-12 md:w-2/3">
                        {steps.map((step) => (
                            <div key={step.number} className="group flex gap-8">
                                <div className="flex h-16 w-16 flex-shrink-0 items-center justify-center rounded-full border-2 border-[#e0c0b1]/30 text-2xl font-black text-[#e0c0b1] transition-colors group-hover:border-[#f97316] group-hover:text-[#f97316]">
                                    {step.number}
                                </div>
                                <div className="space-y-4 pt-2">
                                    <h4 className="text-2xl font-bold text-[#0d1c2e]">{step.title}</h4>
                                    <p className="leading-relaxed text-[#584237]">
                                        {step.description}
                                    </p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </section>
    )
}
