import React from 'react';
import Link from 'next/link';
import { Card } from '@/components/ui/card';
import { LoginForm } from './LoginForm';

interface LoginCardProps {
    email: string;
    password: string;
    error: string;
    isLoading: boolean;
    onEmailChange: (value: string) => void;
    onPasswordChange: (value: string) => void;
    onSubmit: (e: React.FormEvent) => void;
}

export const LoginCard: React.FC<LoginCardProps> = (props) => {
    return (
        <div className="w-full max-w-md">
            <div className="space-y-8">
                {/* Header */}
                <div>
                    <h3 className="text-3xl font-bold text-gray-900">Chào mừng trở lại</h3>
                    <p className="text-gray-600 mt-2 text-sm leading-relaxed">
                        Vui lòng đăng nhập để truy cập kho trí thức.
                    </p>
                </div>

                {/* Form */}
                <LoginForm {...props} />

                {/* Footer */}
                <div className="pt-4 border-t border-gray-200">
                    <p className="text-center text-gray-600 text-xs">
                        Chưa có tài khoản?{' '}
                        <Link
                            href="/request-access"
                            className="text-amber-600 hover:text-amber-700 font-semibold"
                        >
                            Yêu cầu quyền truy cập
                        </Link>
                    </p>
                </div>
            </div>
        </div>
    );
};
