/**
 * Custom API Error Classes
 */

export class ApiError extends Error {
    constructor(
        public statusCode: number,
        message: string,
        public data?: unknown,
        public requestId?: string
    ) {
        super(message)
        this.name = 'ApiError'
        Object.setPrototypeOf(this, ApiError.prototype)
    }
}

export class NetworkError extends Error {
    constructor(message: string) {
        super(message)
        this.name = 'NetworkError'
        Object.setPrototypeOf(this, NetworkError.prototype)
    }
}

export class TimeoutError extends Error {
    constructor(message: string) {
        super(message)
        this.name = 'TimeoutError'
        Object.setPrototypeOf(this, TimeoutError.prototype)
    }
}

export class ValidationError extends Error {
    constructor(message: string, public errors?: Record<string, string[]>) {
        super(message)
        this.name = 'ValidationError'
        Object.setPrototypeOf(this, ValidationError.prototype)
    }
}
