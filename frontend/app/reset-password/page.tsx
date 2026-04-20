'use client';

import { Suspense } from 'react';
import ResetPasswordContent from './content';

export default function ResetPasswordPage() {
    return (
        <Suspense fallback={<ResetPasswordLoadingFallback />}>
            <ResetPasswordContent />
        </Suspense>
    );
}

function ResetPasswordLoadingFallback() {
    return (
        <div className="min-h-screen bg-gradient-to-br from-[#f8f9ff] to-[#eff4ff] flex items-center justify-center">
            <div className="animate-pulse">
                <div className="w-96 h-96 bg-gray-200 rounded-3xl"></div>
            </div>
        </div>
    );
}
