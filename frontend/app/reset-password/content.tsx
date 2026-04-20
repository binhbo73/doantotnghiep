'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { resetPassword } from '@/services/auth';

const PASSWORD_MIN_LENGTH = 8;
const PASSWORD_REGEX = /^(?=.*[a-zA-Z])(?=.*[0-9])(?=.*[!@#$%^&*])/;

interface PasswordStrength {
    score: number;
    message: string;
    color: string;
}

function calculatePasswordStrength(password: string): PasswordStrength {
    let score = 0;
    let message = 'Yếu';
    let color = 'text-red-500';

    if (password.length >= PASSWORD_MIN_LENGTH) score++;
    if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score++;
    if (/[0-9]/.test(password)) score++;
    if (/[!@#$%^&*]/.test(password)) score++;

    if (score <= 1) {
        message = 'Yếu';
        color = 'text-red-500';
    } else if (score === 2) {
        message = 'Trung bình';
        color = 'text-yellow-500';
    } else if (score >= 3) {
        message = 'Mạnh';
        color = 'text-green-500';
    }

    return { score: score - 1, message, color };
}

export default function ResetPasswordContent() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const token = searchParams.get('token');

    const [newPassword, setNewPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [showConfirmPassword, setShowConfirmPassword] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState(false);
    const [passwordStrength, setPasswordStrength] = useState<PasswordStrength>({
        score: 0,
        message: 'Yếu',
        color: 'text-red-500',
    });

    useEffect(() => {
        if (!token) {
            setError('Token không hợp lệ hoặc bị mất. Vui lòng yêu cầu link reset mới.');
        }
    }, [token]);

    useEffect(() => {
        if (newPassword) {
            setPasswordStrength(calculatePasswordStrength(newPassword));
        }
    }, [newPassword]);

    const validateInputs = (): boolean => {
        if (!token) {
            setError('Token không hợp lệ');
            return false;
        }

        if (newPassword.length < PASSWORD_MIN_LENGTH) {
            setError(`Mật khẩu phải có ít nhất ${PASSWORD_MIN_LENGTH} ký tự`);
            return false;
        }

        if (newPassword !== confirmPassword) {
            setError('Mật khẩu xác nhận không khớp');
            return false;
        }

        if (!PASSWORD_REGEX.test(newPassword)) {
            setError('Mật khẩu phải chứa chữ cái, số và ký tự đặc biệt (!@#$%^&*)');
            return false;
        }

        setError('');
        return true;
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!validateInputs()) {
            return;
        }

        setIsLoading(true);
        setError('');

        try {
            await resetPassword(token!, newPassword, confirmPassword);
            setSuccess(true);
            setNewPassword('');
            setConfirmPassword('');

            setTimeout(() => {
                router.push('/login');
            }, 3000);
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Đã xảy ra lỗi. Vui lòng thử lại.';
            setError(message);
            console.error('Reset password error:', err);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div
            className="min-h-screen bg-gradient-to-br from-[#f8f9ff] to-[#eff4ff] flex items-center justify-center p-4 relative overflow-hidden"
            style={{ fontFamily: 'Inter, sans-serif' }}
        >
            <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] rounded-full bg-[#ffdbca] opacity-20 blur-[120px]"></div>
            <div className="absolute bottom-[-10%] right-[-10%] w-[30%] h-[30%] rounded-full bg-[#cde5ff] opacity-20 blur-[100px]"></div>

            <div className="w-full max-w-md p-8 bg-white rounded-3xl shadow-2xl shadow-black/5 relative z-10">
                <div className="space-y-8">
                    <div>
                        <h3 className="text-2xl font-bold text-[#0d1c2e]">Đặt lại mật khẩu</h3>
                        <p className="text-[#584237] mt-2">
                            {success
                                ? 'Mật khẩu của bạn đã được đặt lại thành công!'
                                : 'Nhập mật khẩu mới cho tài khoản của bạn'}
                        </p>
                    </div>

                    {success ? (
                        <div className="space-y-6">
                            <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                                <p className="text-green-700 text-sm">
                                    ✓ Mật khẩu của bạn đã được cập nhật. Vui lòng đăng nhập với mật khẩu mới.
                                </p>
                            </div>
                            <p className="text-[#584237] text-sm text-center">
                                Chuyển hướng tới trang đăng nhập trong 3 giây...
                            </p>
                            <Link
                                href="/login"
                                className="w-full py-3 px-6 bg-gradient-to-r from-[#9d4300] to-[#f97316] text-white font-bold rounded-xl hover:opacity-90 active:scale-95 transition-all text-center block"
                            >
                                Quay lại Đăng nhập
                            </Link>
                        </div>
                    ) : !token ? (
                        <div className="space-y-6">
                            <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                                <p className="text-red-600 text-sm">{error}</p>
                            </div>
                            <Link
                                href="/forgot-password"
                                className="w-full py-3 px-6 bg-gradient-to-r from-[#9d4300] to-[#f97316] text-white font-bold rounded-xl hover:opacity-90 active:scale-95 transition-all text-center block"
                            >
                                Yêu cầu Link Reset Mới
                            </Link>
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
                                    Mật khẩu mới
                                </label>
                                <div className="relative">
                                    <input
                                        type={showPassword ? 'text' : 'password'}
                                        placeholder="••••••••"
                                        value={newPassword}
                                        onChange={(e) => setNewPassword(e.target.value)}
                                        className="w-full px-4 py-3 rounded-xl bg-[#eff4ff] border border-[#e0c0b1]/20 text-[#0d1c2e] placeholder-[#8c7164] focus:outline-none focus:border-[#9d4300] focus:ring-2 focus:ring-[#f97316]/10 transition-all"
                                        required
                                    />
                                    <button
                                        type="button"
                                        onClick={() => setShowPassword(!showPassword)}
                                        className="absolute right-3 top-1/2 -translate-y-1/2 text-[#8c7164] hover:text-[#0d1c2e] transition-colors"
                                    >
                                        {showPassword ? '👁️' : '👁️‍🗨️'}
                                    </button>
                                </div>

                                {newPassword && (
                                    <div className="space-y-2">
                                        <div className="flex items-center justify-between text-xs">
                                            <span className="text-[#8c7164]">Độ mạnh: </span>
                                            <span className={passwordStrength.color}>{passwordStrength.message}</span>
                                        </div>
                                        <div className="h-2 bg-[#e0c0b1]/30 rounded-full overflow-hidden">
                                            <div
                                                className={`h-full transition-all ${passwordStrength.score === 0
                                                    ? 'w-1/4 bg-red-500'
                                                    : passwordStrength.score === 1
                                                        ? 'w-1/2 bg-yellow-500'
                                                        : passwordStrength.score === 2
                                                            ? 'w-3/4 bg-blue-500'
                                                            : 'w-full bg-green-500'
                                                    }`}
                                            ></div>
                                        </div>
                                    </div>
                                )}

                                <div className="text-xs text-[#8c7164] space-y-1 mt-2">
                                    <p>Yêu cầu mật khẩu:</p>
                                    <ul className="list-disc list-inside space-y-1">
                                        <li className={newPassword.length >= PASSWORD_MIN_LENGTH ? 'text-green-600' : ''}>
                                            Ít nhất {PASSWORD_MIN_LENGTH} ký tự
                                        </li>
                                        <li className={/[a-z]/.test(newPassword) && /[A-Z]/.test(newPassword) ? 'text-green-600' : ''}>
                                            Chứa chữ hoa và chữ thường
                                        </li>
                                        <li className={/[0-9]/.test(newPassword) ? 'text-green-600' : ''}>
                                            Chứa ít nhất một số
                                        </li>
                                        <li className={/[!@#$%^&*]/.test(newPassword) ? 'text-green-600' : ''}>
                                            Chứa ký tự đặc biệt (!@#$%^&*)
                                        </li>
                                    </ul>
                                </div>
                            </div>

                            <div className="space-y-2">
                                <label className="block text-sm font-medium text-[#0d1c2e]">
                                    Xác nhận mật khẩu
                                </label>
                                <div className="relative">
                                    <input
                                        type={showConfirmPassword ? 'text' : 'password'}
                                        placeholder="••••••••"
                                        value={confirmPassword}
                                        onChange={(e) => setConfirmPassword(e.target.value)}
                                        className="w-full px-4 py-3 rounded-xl bg-[#eff4ff] border border-[#e0c0b1]/20 text-[#0d1c2e] placeholder-[#8c7164] focus:outline-none focus:border-[#9d4300] focus:ring-2 focus:ring-[#f97316]/10 transition-all"
                                        required
                                    />
                                    <button
                                        type="button"
                                        onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                                        className="absolute right-3 top-1/2 -translate-y-1/2 text-[#8c7164] hover:text-[#0d1c2e] transition-colors"
                                    >
                                        {showConfirmPassword ? '👁️' : '👁️‍🗨️'}
                                    </button>
                                </div>

                                {confirmPassword && (
                                    <div className="text-xs">
                                        {newPassword === confirmPassword ? (
                                            <p className="text-green-600">✓ Mật khẩu khớp</p>
                                        ) : (
                                            <p className="text-red-600">✗ Mật khẩu không khớp</p>
                                        )}
                                    </div>
                                )}
                            </div>

                            <button
                                type="submit"
                                disabled={isLoading || !newPassword || !confirmPassword}
                                className="w-full py-3 px-6 bg-gradient-to-r from-[#9d4300] to-[#f97316] text-white font-bold rounded-xl hover:opacity-90 active:scale-95 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                {isLoading ? 'Đang xử lý...' : 'Đặt lại Mật khẩu'}
                            </button>
                        </form>
                    )}

                    {!success && (
                        <div className="pt-6 border-t border-[#e0c0b1]/20">
                            <p className="text-center text-[#584237] text-sm">
                                Nhớ mật khẩu của bạn?{' '}
                                <Link href="/login" className="text-[#f97316] hover:text-[#9d4300] font-semibold">
                                    Quay lại Đăng nhập
                                </Link>
                            </p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
