'use client';

import { useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { LoginCard } from '@/components/auth';
import { login } from '@/services/auth';
import { logger } from '@/services/logger';
import type { LoginRequest } from '@/types/api';

export function LoginContent() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const redirectPath = searchParams.get('redirect') || '/dashboard';

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

            console.log('[LoginContent] Submitting login with:', { email: credentials.email });

            // Call auth service
            logger.info('Submitting login form', { email: credentials.email });
            const loginData = await login(credentials);

            console.log('[LoginContent] Login returned:', { userId: loginData.user.id, hasToken: !!loginData.access_token });

            // Success - user data is stored by auth service
            logger.info('Login successful', { userId: loginData.user.id });

            // Wait for localStorage and events to process
            await new Promise((resolve) => setTimeout(resolve, 200));

            console.log('[LoginContent] Redirecting to:', redirectPath);

            // Redirect to original page if provided, otherwise dashboard
            router.push(redirectPath);
        } catch (err) {
            // Handle different error types
            let errorMessage = 'Đã xảy ra lỗi. Vui lòng thử lại.';
            let fullError = err;

            if (err instanceof Error) {
                errorMessage = err.message;
                console.error('[LoginContent] Login error:', err.message, err.stack);
                logger.error('Login error', { error: err.message });
            } else {
                console.error('[LoginContent] Unknown error:', err);
                logger.error('Login error', { error: String(err) });
            }

            setError(errorMessage);
            logger.debug('Login error details', { error: fullError });
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <LoginCard
            email={email}
            password={password}
            error={error}
            isLoading={isLoading}
            onEmailChange={setEmail}
            onPasswordChange={setPassword}
            onSubmit={handleSubmit}
        />
    );
}
