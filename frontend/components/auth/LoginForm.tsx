import React, { useState } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

interface LoginFormProps {
    email: string;
    password: string;
    error: string;
    isLoading: boolean;
    onEmailChange: (value: string) => void;
    onPasswordChange: (value: string) => void;
    onSubmit: (e: React.FormEvent) => void;
}

export const LoginForm: React.FC<LoginFormProps> = ({
    email,
    password,
    error,
    isLoading,
    onEmailChange,
    onPasswordChange,
    onSubmit,
}) => {
    const [showPassword, setShowPassword] = useState(false);
    const [rememberMe, setRememberMe] = useState(false);

    return (
        <form onSubmit={onSubmit} className="space-y-6">
            {/* Error Message */}
            {error && (
                <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                    <p className="text-red-600 text-sm">{error}</p>
                </div>
            )}





            {/* Email Field */}
            <div className="space-y-2">
                <label className="block text-xs font-semibold text-gray-700 uppercase">
                    Email doanh nghiệp
                </label>
                <div className="relative">
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">✉️</span>
                    <Input
                        type="email"
                        placeholder="email@company.com"
                        value={email}
                        onChange={(e) => onEmailChange(e.target.value)}
                        required
                        className="pl-10 border-gray-300"
                    />
                </div>
            </div>

            {/* Password Field */}
            <div className="space-y-2">
                <label className="block text-xs font-semibold text-gray-700 uppercase">
                    Mật khẩu
                </label>
                <div className="relative">
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">🔒</span>
                    <Input
                        type={showPassword ? 'text' : 'password'}
                        placeholder="••••••••"
                        value={password}
                        onChange={(e) => onPasswordChange(e.target.value)}
                        required
                        className="pl-10 pr-10 border-gray-300"
                    />
                    <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                    >
                        {showPassword ? '👁️' : '👁️‍🗨️'}
                    </button>
                </div>
            </div>

            {/* Remember Me & Forgot Password */}
            <div className="flex items-center justify-between">
                <label className="flex items-center gap-2 cursor-pointer">
                    <input
                        type="checkbox"
                        checked={rememberMe}
                        onChange={(e) => setRememberMe(e.target.checked)}
                        className="w-4 h-4 rounded border-gray-300"
                    />
                    <span className="text-sm text-gray-700">Ghi nhớ đăng nhập</span>
                </label>
                <Link
                    href="/forgot-password"
                    className="text-sm text-amber-600 hover:text-amber-700 font-semibold"
                >
                    Quên mật khẩu?
                </Link>
            </div>

            {/* Login Button */}
            <Button
                type="submit"
                disabled={isLoading}
                className="w-full bg-amber-600 hover:bg-amber-700 text-white font-bold h-12 rounded-full transition text-base flex items-center justify-center gap-2"
            >
                {isLoading ? 'Đang đăng nhập...' : 'Đăng nhập hệ thống →'}
            </Button>
        </form>
    );
};
