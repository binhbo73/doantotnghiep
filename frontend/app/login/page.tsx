'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { BrandingSection, LoginCard } from '@/components/auth';

const BRANDING_DATA = {
    title: 'Trí Thức Doanh nghiệp',
    subtitle: 'Enterprise Knowledge Operating System',
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
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ email, password }),
            });

            if (!response.ok) {
                const data = await response.json();
                setError(data.message || 'Đăng nhập thất bại');
                return;
            }

            router.push('/dashboard');
        } catch (err) {
            setError('Đã xảy ra lỗi. Vui lòng thử lại.');
            console.error(err);
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
