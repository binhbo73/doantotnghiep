'use client'

import React, { useState, useEffect } from 'react'
import { useRBAC } from '@/hooks/useRBAC'
import { SkeletonLoader } from './SkeletonLoader'

interface PermissionGateProps {
    /**
     * Required object-level permission (if checking against a specific resource)
     */
    permission?: 'delete' | 'write' | 'read'

    /**
     * The actual permission string from the resource (from API 'my_permission')
     */
    actualPermission?: 'delete' | 'write' | 'read' | 'none'

    /**
     * Action-based permission check (NEW)
     * Examples: 'create', 'read', 'update', 'delete'
     * Checks backend permission strings like "document_create", "user_delete"
     */
    action?: string

    /**
     * Resource type for action check (NEW)
     * Examples: 'document', 'user', 'folder'
     * Used with action: hasActionPermission(action, resourceType)
     */
    resourceType?: string

    /**
     * Exact backend permission string to check (NEW)
     * Examples: 'document_create', 'user_delete', 'system_admin'
     * This bypasses action/resourceType logic and does exact match
     */
    permission_string?: string

    children: React.ReactNode

    /** 
     * What to show if access is denied 
     */
    fallback?: React.ReactNode

    /**
     * Show loading skeleton while checking permissions
     */
    isLoading?: boolean

    /**
     * Custom loading fallback (default: SkeletonLoader)
     */
    loadingFallback?: React.ReactNode
}

/**
 * PermissionGate - conditionally render UI from backend permission codes.
 * 
 * Features:
 * - Object-level permission checks (delete, write, read, none)
 * - Backend permission string checks (e.g., "document_create")
 * - Action-based permission checks (create, read, update, delete)
 * - Loading states with skeleton loader
 * - Consistent fallback UI
 * 
 * Usage Examples:
 * // Exact permission string
 * <PermissionGate permission_string="document_create">
 *    <CreateDocumentButton />
 * </PermissionGate>
 * 
 * // Action-based
 * <PermissionGate action="delete" resourceType="user">
 *    <DeleteUserButton />
 * </PermissionGate>
 */
export function PermissionGate({
    permission,
    actualPermission,
    action,
    resourceType,
    permission_string,
    children,
    fallback = null,
    isLoading = false,
    loadingFallback = <SkeletonLoader lines={3} />,
}: PermissionGateProps) {
    const { can, hasActionPermission, hasPermissionString } = useRBAC()
    const [mounted, setMounted] = useState(false)

    // Prevent hydration mismatch
    useEffect(() => {
        setMounted(true)
    }, [])

    if (!mounted) {
        return <>{loadingFallback}</>
    }

    // Show loading state if explicitly requested
    if (isLoading) {
        return <>{loadingFallback}</>
    }

    // 1. system_admin permission always has access
    if (hasPermissionString('system_admin')) return <>{children}</>

    // 2. Check exact permission string (NEW)
    if (permission_string) {
        if (!hasPermissionString(permission_string)) {
            return <>{fallback}</>
        }
        // If exact match passes, continue to render
        return <>{children}</>
    }

    // 3. Check action-based permission (NEW)
    if (action) {
        if (!hasActionPermission(action, resourceType)) {
            return <>{fallback}</>
        }
        // If action check passes, continue to render
        return <>{children}</>
    }

    // 4. Check Object Permission (if provided)
    if (permission && actualPermission) {
        if (!can(permission, actualPermission)) {
            return <>{fallback}</>
        }
    }

    return <>{children}</>
}
