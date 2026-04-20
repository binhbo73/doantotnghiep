// context/index.tsx - Global App Context Providers
'use client'

import React, { createContext, useContext, useState, useEffect } from 'react'
import { authService } from '@/services/auth'
import type { User } from '@/types'

interface AuthContextType {
    user: User | null
    isLoading: boolean
    isAuthenticated: boolean
    logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const [user, setUser] = useState<User | null>(null)
    const [isLoading, setIsLoading] = useState(true)

    // Initialize auth state on mount
    useEffect(() => {
        const initAuth = async () => {
            try {
                if (authService.isAuthenticated()) {
                    // In a real app, fetch user from /users/profile endpoint
                    // For now, just mark as loaded
                    setUser({ id: '', email: '', name: '', role: 'user' })
                }
            } catch (error) {
                console.error('Auth init error:', error)
                authService.logout()
            } finally {
                setIsLoading(false)
            }
        }

        initAuth()
    }, [])

    const logout = async () => {
        setIsLoading(true)
        try {
            await authService.logout()
            setUser(null)
        } finally {
            setIsLoading(false)
        }
    }

    const value: AuthContextType = {
        user,
        isLoading,
        isAuthenticated: authService.isAuthenticated(),
        logout,
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

