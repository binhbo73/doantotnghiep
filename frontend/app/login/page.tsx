'use client';

import { Suspense } from 'react';
import { BrandingSection } from '@/components/auth';
import { LoginContent } from './_components/LoginContent';

const BRANDING_DATA = {
    title: 'Trí Thức Doanh nghiệp',
    subtitle: 'Hệ điều hành tri thức doanh nghiệp',
    heading: 'Kiến tạo không gian trí tuệ số của bạn.',
    description:
        'Hệ điều hành trí thức giúp doanh nghiệp quản trị, kết nối và khai phóng tiềm năng từ một nguồn dữ liệu liên kết.',
    features: [
        {
            icon: '✓',
            title: 'BẢO MẬT ĐA LỚP',
            subtitle: '"Dữ liệu của bạn được bảo vệ bởi tiêu chuẩn mã hóa tốt nhất hiện nay"',
        },
    ],
};

export default function LoginPage() {
    return (
        <div className="min-h-screen bg-white flex">
            {/* Left side - Branding */}
            <BrandingSection {...BRANDING_DATA} />

            {/* Right side - Login Form */}
            <div className="w-full lg:w-1/2 flex items-center justify-center px-6 py-12 lg:py-0">
                <Suspense fallback={<div>Carregando...</div>}>
                    <LoginContent />
                </Suspense>
            </div>
        </div>
    );
}
