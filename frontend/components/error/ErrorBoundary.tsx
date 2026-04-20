/**
 * Error Boundary Component
 * Catches React rendering errors and displays fallback UI
 */

'use client'

import React, { ReactNode } from 'react'
import { logger } from '@/services/logger'
import { AlertCircle, RefreshCw, Home } from 'lucide-react'

interface Props {
    children: ReactNode
    fallback?: (error: Error, reset: () => void) => ReactNode
}

interface State {
    hasError: boolean
    error: Error | null
    errorCount: number
}

export class ErrorBoundary extends React.Component<Props, State> {
    private resetTimeout: NodeJS.Timeout | null = null

    constructor(props: Props) {
        super(props)
        this.state = {
            hasError: false,
            error: null,
            errorCount: 0,
        }
    }

    static getDerivedStateFromError(error: Error): State {
        return {
            hasError: true,
            error,
            errorCount: 0,
        }
    }

    componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
        // Log error with stack trace
        logger.error('React Error Boundary caught:', {
            error: error.message,
            stack: error.stack,
            componentStack: errorInfo.componentStack,
        })

        // Optional: Send to error tracking service (e.g., Sentry)
        // Sentry.captureException(error, { contexts: { react: errorInfo } })
    }

    handleReset = () => {
        this.setState({
            hasError: false,
            error: null,
            errorCount: 0,
        })
    }

    handleReload = () => {
        if (typeof window !== 'undefined') {
            window.location.reload()
        }
    }

    handleGoHome = () => {
        if (typeof window !== 'undefined') {
            window.location.href = '/'
        }
    }

    render() {
        if (this.state.hasError && this.state.error) {
            // Use custom fallback if provided
            if (this.props.fallback) {
                return this.props.fallback(this.state.error, this.handleReset)
            }

            // Default error UI
            return (
                <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
                    <div className="max-w-md w-full space-y-6 bg-white rounded-lg shadow-lg p-8">
                        {/* Icon */}
                        <div className="flex justify-center">
                            <AlertCircle className="h-16 w-16 text-red-600" />
                        </div>

                        {/* Title */}
                        <div className="text-center">
                            <h1 className="text-2xl font-bold text-gray-900">
                                Oops! Something went wrong
                            </h1>
                            <p className="mt-2 text-gray-600">
                                We encountered an unexpected error. Don't worry, our team has been
                                notified.
                            </p>
                        </div>

                        {/* Error Details (development only) */}
                        {process.env.NODE_ENV === 'development' && (
                            <div className="bg-red-50 border border-red-200 rounded p-4">
                                <p className="text-sm font-mono text-red-900">
                                    {this.state.error.message}
                                </p>
                                {this.state.error.stack && (
                                    <pre className="mt-2 text-xs text-red-800 overflow-auto max-h-32">
                                        {this.state.error.stack}
                                    </pre>
                                )}
                            </div>
                        )}

                        {/* Error ID */}
                        <div className="bg-gray-50 border border-gray-200 rounded p-4">
                            <p className="text-xs text-gray-500 font-mono break-all">
                                Error ID: {Math.random().toString(36).substr(2, 9)}
                            </p>
                        </div>

                        {/* Actions */}
                        <div className="space-y-3">
                            <button
                                onClick={this.handleReset}
                                className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                            >
                                <RefreshCw className="h-4 w-4" />
                                Try Again
                            </button>

                            <button
                                onClick={this.handleReload}
                                className="w-full px-4 py-2 bg-gray-200 text-gray-900 rounded-lg hover:bg-gray-300 transition-colors"
                            >
                                Reload Page
                            </button>

                            <button
                                onClick={this.handleGoHome}
                                className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-gray-100 text-gray-900 rounded-lg hover:bg-gray-200 transition-colors"
                            >
                                <Home className="h-4 w-4" />
                                Go Home
                            </button>
                        </div>

                        {/* Support */}
                        <div className="text-center text-sm text-gray-600">
                            <p>If the problem persists, please contact support.</p>
                        </div>
                    </div>
                </div>
            )
        }

        return this.props.children
    }
}
