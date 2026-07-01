'use client'

// context/index.tsx - Global App Context Providers


import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import { authService } from '@/services/auth'
import type { User } from '@/types'

interface AuthContextType {
    user: User | null
    isLoading: boolean
    isAuthenticated: boolean
    logout: () => Promise<void>
    updateUser: (user: User) => void  // ADD: Allow components to update user data
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

// Helper function to load user from storage
function loadUserFromStorage(): User | null {
    try {
        const currentUser = authService.getCurrentUser()
        if (!currentUser) return null

        return {
            id: currentUser.id,
            email: currentUser.email,
            name: `${currentUser.first_name} ${currentUser.last_name}`.trim(),
            username: currentUser.username,
            roles: currentUser.roles || [],
            department_id: currentUser.department_id || null,
            permissions: currentUser.permissions || []
        }
    } catch (error) {
        console.error('Error loading user from storage:', error)
        return null
    }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const [user, setUser] = useState<User | null>(null)
    const [isLoading, setIsLoading] = useState(true)
    const [lastAuthCheck, setLastAuthCheck] = useState(0)
    const router = useRouter()
    const pathname = usePathname()

    const isPublicRoute = pathname === '/login' || pathname === '/register' || pathname === '/forgot-password' || pathname === '/reset-password' || pathname === '/'

    const redirectToLogin = () => {
        if (!isPublicRoute) {
            router.push('/login')
        }
    }

    // Initialize auth state on mount
    useEffect(() => {
        const initAuth = async () => {
            try {
                // Check if already authenticated
                const isAuth = authService.isAuthenticated()
                console.log('🔍 [AuthProvider] Auth check on mount:', {
                    isAuthenticated: isAuth,
                    hasToken: !!authService.getAuthToken()
                })

                if (isAuth) {
                    const currentUser = loadUserFromStorage()
                    if (currentUser) {
                        console.log('👤 Authenticated user with RBAC:', {
                            id: currentUser.id,
                            roles: currentUser.roles?.map((r: any) => r.code),
                            dept: currentUser.department_id
                        })
                        setUser(currentUser)
                    }
                } else {
                    console.log('ℹ️ [AuthProvider] No authenticated user on mount')
                    await authService.logout()
                    redirectToLogin()
                }
            } catch (error) {
                console.error('Auth init error:', error)
                authService.logout()
                redirectToLogin()
            } finally {
                setIsLoading(false)
            }
        }

        initAuth()
    }, [])

    // Listen for storage changes (for account switching detection)
    useEffect(() => {
        const handleStorageChange = () => {
            console.log('📦 Storage change detected - checking auth status...')
            const now = Date.now()

            // Debounce: only check if at least 500ms have passed
            if (now - lastAuthCheck < 500) return
            setLastAuthCheck(now)

            if (authService.isAuthenticated()) {
                const newUser = loadUserFromStorage()
                if (newUser) {
                    console.log('🔄 User data refreshed from storage:', {
                        from: user?.id,
                        to: newUser.id,
                        permissionCount: newUser.permissions.length,
                    })
                    setUser(newUser)
                }
            } else if (!isPublicRoute) {
                void authService.logout().finally(() => {
                    setUser(null)
                    redirectToLogin()
                })
            }
        }

        window.addEventListener('storage', handleStorageChange)
        return () => window.removeEventListener('storage', handleStorageChange)
    }, [user?.id, lastAuthCheck])

    // Listen for explicit auth change events (fired from setAuthData)
    useEffect(() => {
        const handleAuthChange = () => {
            console.log('🔄 Auth change event detected - reloading user data...')

            if (authService.isAuthenticated()) {
                const newUser = loadUserFromStorage()
                if (newUser) {
                    console.log('✅ User context updated:', {
                        from: user?.id,
                        to: newUser.id,
                        permissionCount: newUser.permissions.length,
                    })
                    setUser(newUser)
                }
            } else if (!isPublicRoute) {
                void authService.logout().finally(() => {
                    setUser(null)
                    redirectToLogin()
                })
            }
        }

        window.addEventListener('auth:user-changed', handleAuthChange)
        return () => window.removeEventListener('auth:user-changed', handleAuthChange)
    }, []) // Empty dependency array - listener should stay active throughout component lifetime

    const logout = useCallback(async () => {
        setIsLoading(true)
        try {
            await authService.logout()
            setUser(null)
        } finally {
            setIsLoading(false)
        }
    }, [])

    // Update user data during session (e.g., after permission/role changes)
    const updateUser = useCallback((newUser: User) => {
        setUser((previousUser) => {
            const oldUserId = previousUser?.id
            console.log('👤 User data updated:', {
                from: oldUserId,
                to: newUser.id,
                roles: newUser.roles?.map((r: any) => r.code)
            })

            // If user ID changed, notify dashboard to clear cache
            if (oldUserId && oldUserId !== newUser.id) {
                window.dispatchEvent(new Event('auth:user-changed'))
            }
            return newUser
        })
    }, [])

    const value: AuthContextType = {
        user,
        isLoading,
        isAuthenticated: authService.isAuthenticated(),
        logout,
        updateUser,  // EXPORT: Allow components to update user
    }

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuthContext() {
    const context = useContext(AuthContext)
    if (context === undefined) {
        throw new Error('useAuthContext must be used within AuthProvider')
    }
    return context
}

