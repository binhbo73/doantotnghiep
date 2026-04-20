'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { forgotPassword } from '@/services/auth';

export default function ForgotPasswordPage() {
    const router = useRouter();
    const [email, setEmail] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [submitted, setSubmitted] = useState(false);
    const [error, setError] = useState('');

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setIsLoading(true);

        try {
            await forgotPassword(email);
            setSubmitted(true);
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Đã xảy ra lỗi. Vui lòng thử lại.';
            setError(message);
            console.error(err);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-[#f8f9ff] to-[#eff4ff] flex items-center justify-center p-4 relative overflow-hidden" style={{ fontFamily: 'Inter, sans-serif' }}>
            <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] rounded-full bg-[#ffdbca] opacity-20 blur-[120px]"></div>
            <div className="absolute bottom-[-10%] right-[-10%] w-[30%] h-[30%] rounded-full bg-[#cde5ff] opacity-20 blur-[100px]"></div>

            <div className="w-full max-w-md p-8 bg-white rounded-3xl shadow-2xl shadow-black/5 relative z-10">
                <div className="space-y-8">
                    <div>
                        <h3 className="text-2xl font-bold text-[#0d1c2e]">Đặt lại mật khẩu</h3>
                        <p className="text-[#584237] mt-2">
                            {submitted
                                ? 'Kiểm tra email của bạn để nhận liên kết đặt lại'
                                : 'Nhập email của bạn để nhận liên kết đặt lại mật khẩu'}
                        </p>
                    </div>

                    {submitted ? (
                        <div className="space-y-6">
                            <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                                <p className="text-green-700 text-sm">
                                    ✓ Liên kết đặt lại đã được gửi tới {email}
                                </p>
                            </div>
                            <p className="text-[#584237] text-sm">
                                Kiểm tra email của bạn để tìm liên kết đặt lại mật khẩu. Liên kết sẽ hết hạn trong 24 giờ.
                            </p>
                            <button
                                onClick={() => router.push('/login')}
                                className="w-full py-3 px-6 bg-gradient-to-r from-[#9d4300] to-[#f97316] text-white font-bold rounded-xl hover:opacity-90 active:scale-95 transition-all"
                            >
                                Quay lại Đăng nhập
                            </button>
                        </div>
                    ) : (
                        <form onSubmit={handleSubmit} className="space-y-6">
                            {error && (
                                <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                                    <p className="text-red-600 text-sm">{error}</p>
                                </div>
                            )}

                            <div className="space-y-2">
                                <label className="block text-sm font-medium text-[#0d1c2e]">
                                    Địa chỉ Email
                                </label>
                                <input
                                    type="email"
                                    placeholder="you@company.com"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    className="w-full px-4 py-3 rounded-xl bg-[#eff4ff] border border-[#e0c0b1]/20 text-[#0d1c2e] placeholder-[#8c7164] focus:outline-none focus:border-[#9d4300] focus:ring-2 focus:ring-[#f97316]/10 transition-all"
                                    required
                                />
                            </div>

                            <button
                                type="submit"
                                disabled={isLoading}
                                className="w-full py-3 px-6 bg-gradient-to-r from-[#9d4300] to-[#f97316] text-white font-bold rounded-xl hover:opacity-90 active:scale-95 transition-all disabled:opacity-50"
                            >
                                {isLoading ? 'Đang gửi...' : 'Gửi Liên kết Đặt lại'}
                            </button>
                        </form>
                    )}

                    <div className="pt-6 border-t border-[#e0c0b1]/20">
                        <p className="text-center text-[#584237] text-sm">
                            Nhớ mật khẩu của bạn?{' '}
                            <Link href="/login" className="text-[#f97316] hover:text-[#9d4300] font-semibold">
                                Quay lại Đăng nhập
                            </Link>
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}
