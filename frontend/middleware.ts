import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

// Routes không cần xác thực
const PUBLIC_ROUTES = ['/login', '/register', '/forgot-password', '/reset-password', '/']

// Routes cần xác thực
const PROTECTED_ROUTES = ['/dashboard']

export function middleware(request: NextRequest) {
    const pathname = request.nextUrl.pathname
    const token = request.cookies.get('auth_token')?.value ||
        request.headers.get('x-auth-token') ||
        // Fallback: check localStorage via header (if sent by client)
        null

    // Kiểm tra localStorage token từ client-side
    const cookieToken = request.cookies.get('auth_token')?.value

    // Check if trying to access protected route
    const isProtectedRoute = PROTECTED_ROUTES.some(route =>
        pathname.startsWith(route)
    )

    // Check if it's a public route
    const isPublicRoute = PUBLIC_ROUTES.includes(pathname)

    // Nếu không có token và cố truy cập protected route -> redirect to login
    if (isProtectedRoute && !cookieToken) {
        const loginUrl = new URL('/login', request.url)
        loginUrl.searchParams.set('redirect', pathname)
        return NextResponse.redirect(loginUrl)
    }

    // Nếu đã đăng nhập và truy cập login/register -> redirect to dashboard
    if ((pathname === '/login' || pathname === '/register') && cookieToken) {
        return NextResponse.redirect(new URL('/dashboard', request.url))
    }

    return NextResponse.next()
}

export const config = {
    // Apply middleware to all routes except static files and API
    matcher: [
        '/((?!api|_next/static|_next/image|favicon.ico).*)',
    ],
}
