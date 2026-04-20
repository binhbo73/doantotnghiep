/**
 * Logger Service - Centralized logging for development and production
 * Sends logs to backend in production, console in development
 */

type LogLevel = 'debug' | 'info' | 'warn' | 'error'

interface LogEntry {
    timestamp: string
    level: LogLevel
    message: string
    data?: unknown
    [key: string]: unknown
}

interface LogRequest {
    level: LogLevel
    message: string
    data?: unknown
    context?: string
    url?: string
    userAgent?: string
}

class Logger {
    private isDev = process.env.NODE_ENV === 'development'
    private isProd = process.env.NODE_ENV === 'production'
    private logs: LogEntry[] = []
    private maxLogs = 100 // Keep last 100 logs in memory

    private createEntry(level: LogLevel, message: string, data?: unknown): LogEntry {
        const entry: LogEntry = {
            timestamp: new Date().toISOString(),
            level,
            message,
        }

        // Only add data if it's provided and not null/undefined
        if (data !== null && data !== undefined) {
            return { ...entry, data }
        }

        return entry
    }

    /**
     * Log debug message
     */
    debug(message: string, data?: unknown) {
        if (this.isDev) {
            this.log('debug', message, data)
        }
    }

    /**
     * Log info message
     */
    info(message: string, data?: unknown) {
        this.log('info', message, data)
    }

    /**
     * Log warning message
     */
    warn(message: string, data?: unknown) {
        this.log('warn', message, data)
    }

    /**
     * Log error message (most important)
     */
    error(messageOrError: string | Error | object, data?: unknown) {
        let message = 'Unknown error'
        let errorData: unknown = data

        if (typeof messageOrError === 'string') {
            message = messageOrError
            errorData = data
        } else if (messageOrError instanceof Error) {
            message = messageOrError.message
            errorData = {
                name: messageOrError.name,
                stack: messageOrError.stack,
                ...(typeof data === 'object' && data !== null ? data : {}),
            }
        } else {
            message = 'Error'
            errorData = messageOrError
        }

        this.log('error', message, errorData)
    }

    /**
     * Internal log function
     */
    private log(level: LogLevel, message: string, data?: unknown) {
        const entry = this.createEntry(level, message, data)
        this.addToBuffer(entry)

        // Log to console in development
        if (this.isDev) {
            const method = level === 'debug' ? 'log' : level
            const style = this.getConsoleStyle(level)

            // Direct console call without type assertion
            if (method === 'log') {
                console.log(`%c[${level.toUpperCase()}]`, style, entry.message, entry.data || '')
            } else if (method === 'info') {
                console.info(`%c[${level.toUpperCase()}]`, style, entry.message, entry.data || '')
            } else if (method === 'warn') {
                console.warn(`%c[${level.toUpperCase()}]`, style, entry.message, entry.data || '')
            } else if (method === 'error') {
                console.error(`%c[${level.toUpperCase()}]`, style, entry.message, entry.data || '')
            }
        }

        // Send to backend in production
        if (this.isProd && (level === 'error' || level === 'warn')) {
            this.sendToBackend(entry)
        }
    }

    /**
     * Add entry to in-memory buffer
     */
    private addToBuffer(entry: LogEntry) {
        this.logs.push(entry)
        if (this.logs.length > this.maxLogs) {
            this.logs = this.logs.slice(-this.maxLogs)
        }
    }

    /**
     * Get console style based on log level
     */
    private getConsoleStyle(level: LogLevel): string {
        const styles: Record<LogLevel, string> = {
            debug: 'color: #999; font-weight: bold;',
            info: 'color: #0066cc; font-weight: bold;',
            warn: 'color: #ff9900; font-weight: bold;',
            error: 'color: #cc0000; font-weight: bold;',
        }
        return styles[level]
    }

    /**
     * Send error/warn logs to backend API
     */
    private async sendToBackend(entry: LogEntry) {
        try {
            const logRequest: LogRequest = {
                level: entry.level,
                message: entry.message,
                data: entry.data,
                context: this.getPageContext(),
                url: typeof window !== 'undefined' ? window.location.href : undefined,
                userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : undefined,
            }

            await fetch(
                `${process.env.NEXT_PUBLIC_API_URL}/logs`,
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${this.getAuthToken() || ''}`,
                    },
                    body: JSON.stringify(logRequest),
                }
            ).catch(() => {
                // Fail silently - don't crash if logging fails
            })
        } catch (err) {
            // Fail silently
        }
    }

    /**
     * Get current page context
     */
    private getPageContext(): string {
        if (typeof window !== 'undefined') {
            return window.location.pathname
        }
        return 'server'
    }

    /**
     * Get auth token from localStorage
     */
    private getAuthToken(): string | null {
        if (typeof window !== 'undefined') {
            return localStorage.getItem('auth_token')
        }
        return null
    }

    /**
     * Get all buffered logs
     */
    getLogs(): LogEntry[] {
        return [...this.logs]
    }

    /**
     * Clear buffered logs
     */
    clearLogs() {
        this.logs = []
    }

    /**
     * Export logs as JSON (for debugging)
     */
    exportLogs(): string {
        return JSON.stringify(this.logs, null, 2)
    }

    /**
     * Get last N logs
     */
    getLastLogs(count: number = 10): LogEntry[] {
        return this.logs.slice(-count)
    }

    /**
     * Filter logs by level
     */
    getLogsByLevel(level: LogLevel): LogEntry[] {
        return this.logs.filter((log) => log.level === level)
    }

    /**
     * Get error logs
     */
    getErrorLogs(): LogEntry[] {
        return this.getLogsByLevel('error')
    }
}

// Export singleton instance
export const logger = new Logger()

// Also export type for use in components
export type { LogEntry, LogLevel }
