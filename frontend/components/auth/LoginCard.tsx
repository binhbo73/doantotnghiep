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
                
            </div>
        </div>
    );
};
