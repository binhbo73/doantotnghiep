'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { BrandingSection, LoginCard } from '@/components/auth';
import { login } from '@/services/auth';
import { logger } from '@/services/logger';
import type { LoginRequest } from '@/types/api';

const BRANDING_DATA = {
    title: 'Trí Thức Doanh nghiệp',
    subtitle: 'Hệ điều hành tri thức doanh nghiệp',
    heading: 'Kiến tạo không gian trị tuệ số của bạn.',
    description:
        'Hệ điều hành trí thức giúp doanh nghiệp quản trị, kết nối và khai phóng tiềm năng từ một nguồn dữ liệu liên kết.',
    features: [
        {
            icon: '✓',
            title: 'BAO MẬT ĐA LỚP',
            subtitle: '"Dữ liệu của bạn được bảo vệ bởi tiêu chuẩn mã hóa tốt nhất hiện nay"',
        },
    ],
};

export default function LoginPage() {
    const router = useRouter();
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setIsLoading(true);

        try {
            // Prepare credentials
            const credentials: LoginRequest = {
                email: email.trim(),
                password,
            };

            // Validate input
            if (!credentials.email || !credentials.password) {
                setError('Vui lòng nhập email và mật khẩu');
                setIsLoading(false);
                return;
            }

            // Call auth service
            logger.info('Submitting login form', { email: credentials.email });
            const loginData = await login(credentials);

            // Success - user data is stored by auth service
            logger.info('Login successful', { userId: loginData.user.id });

            // Redirect to dashboard
            router.push('/dashboard');
        } catch (err) {
            // Handle different error types
            let errorMessage = 'Đã xảy ra lỗi. Vui lòng thử lại.';

            if (err instanceof Error) {
                errorMessage = err.message;
                logger.error('Login error', { error: err.message });
            } else {
                logger.error('Login error', { error: String(err) });
            }

            setError(errorMessage);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-white flex">
            {/* Left side - Branding */}
            <BrandingSection {...BRANDING_DATA} />

            {/* Right side - Login Form */}
            <div className="w-full lg:w-1/2 flex items-center justify-center px-6 py-12 lg:py-0">
                <LoginCard
                    email={email}
                    password={password}
                    error={error}
                    isLoading={isLoading}
                    onEmailChange={setEmail}
                    onPasswordChange={setPassword}
                    onSubmit={handleSubmit}
                />
            </div>
        </div>
    );
}
