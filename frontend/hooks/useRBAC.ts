'use client'

import { useAuthContext } from '@/context'

export type ObjectPerm = 'delete' | 'write' | 'read' | 'none'

const PERM_WEIGHT: Record<ObjectPerm, number> = {
    delete: 3,
    write: 2,
    read: 1,
    none: 0,
}

const ACTION_LEVEL_PATTERNS: Array<{ pattern: RegExp; level: ObjectPerm }> = [
    { pattern: /(^|_)(read|view|list|download|search)$/, level: 'read' },
    { pattern: /(^|_)(create|add|new|upload|update|edit|write|manage|assign|approve|reject|send|sync|generate|export|import|change_status|change_role)$/, level: 'write' },
    { pattern: /(^|_)(delete|remove|destroy|purge|revoke)$/, level: 'delete' },
    { pattern: /(^|_)system_admin$/, level: 'delete' },
    { pattern: /(^|_)(permission_manage|role_manage)$/, level: 'delete' },
]

const normalizePermission = (value: string) => value.trim().toLowerCase()

const inferPermissionLevel = (permissionString: string): ObjectPerm => {
    const normalized = normalizePermission(permissionString)

    for (const { pattern, level } of ACTION_LEVEL_PATTERNS) {
        if (pattern.test(normalized)) return level
    }

    return 'none'
}

/**
 * useRBAC Hook - Centralized logic for Role-Based Access Control
 * Handles both Global Roles (Admin, Manager, Employee) and 
 * Permission strings from backend (e.g., "document_create", "user_delete").
 * 
 * Role codes are matched case-insensitively and support both
 * object format {code: 'admin'} and string format 'admin'.
 */
export function useRBAC() {
    const { user } = useAuthContext()

    // --- 1. Global Role Checks ---

    /**
     * Check if user has a specific role by code (case-insensitive)
     * Supports both {code: '...'} objects and plain strings
     */
    const hasRole = (roleCode: string): boolean => {
        if (!user || !user.roles || !Array.isArray(user.roles)) return false

        return user.roles.some((r: any) => {
            const code = typeof r === 'string' ? r : r?.code
            if (!code) return false
            return code.toLowerCase() === roleCode.toLowerCase()
        })
    }

    /**
     * Admin check - ADMIN or SUPERUSER role
     */
    const isAdmin = (): boolean => {
        return hasRole('admin') || hasRole('superuser')
    }

    /**
     * Manager check (Trưởng phòng) - MANAGER or TRUONG_PHONG role
     */
    const isTruongPhong = (): boolean => {
        return hasRole('truong_phong') || hasRole('manager')
    }

    /**
     * Employee check (Nhân viên) - USER, EMPLOYEE, or NHAN_VIEN role
     */
    const isNhanVien = (): boolean => {
        return hasRole('nhan_vien') || hasRole('user') || hasRole('employee')
    }

    // --- 2. Object-Level Permission Checks ---

    /**
     * Generic permission check: actual >= required
     * Example: can('write', 'admin') -> true
     */
    const can = (required: ObjectPerm, actual: ObjectPerm | undefined | null): boolean => {
        if (!actual) return false
        return PERM_WEIGHT[actual] >= PERM_WEIGHT[required]
    }

    // Shorthand helpers for specific actions
    const canRead = (perm: ObjectPerm | null | undefined) => can('read', perm)
    const canWrite = (perm: ObjectPerm | null | undefined) => can('write', perm)
    const canDelete = (perm: ObjectPerm | null | undefined) => can('delete', perm)
    const canShare = (perm: ObjectPerm | null | undefined) => can('delete', perm)

    // --- 3. Resource Context Checks ---

    /**
     * Check if user belongs to a specific department (exact match)
     * Does NOT check hierarchy - use isAccessibleDepartment() for hierarchy-aware check
     */
    const isInDepartment = (deptId: string | null | undefined) =>
        !!deptId && user?.department_id === deptId

    /**
     * Check if user can access content from a specific department
     * Supports department hierarchy:
     * - User in own department → accessible
     * - User in child department accessing parent department → accessible
     * - User in parent department accessing child department → NOT accessible (security)
     * 
     * Note: This is a simple check. Ideal implementation would use a departments list
     * from context/store to walk up the hierarchy. For now, we rely on backend to enforce.
     */
    const isAccessibleDepartment = (
        deptId: string | null | undefined,
        departmentList?: any[]
    ): boolean => {
        if (!deptId) return true // No department restriction
        if (isInDepartment(deptId)) return true // Same department

        // If no department list provided, assume it's inaccessible
        // (Frontend doesn't have hierarchy info, backend will enforce)
        return false
    }

    /**
     * Check if user is the uploader of a document (optional)
     */
    const isOwner = (uploaderId: string | null | undefined) =>
        !!uploaderId && user?.id === uploaderId

    /**
     * Get the user's highest role label for display
     */
    const getRoleBadge = (): { label: string; color: string; bgColor: string } => {
        if (isAdmin()) return { label: 'Quản trị viên', color: '#c62828', bgColor: '#ffebee' }
        if (isTruongPhong()) return { label: 'Trưởng phòng', color: '#e65100', bgColor: '#fff3e0' }
        return { label: 'Nhân viên', color: '#1565c0', bgColor: '#e3f2fd' }
    }

    // --- 4. Backend Permission String Parsing & Checking ---

    /**
     * Check if user has a specific backend permission string
     * Examples: "document_create", "user_delete", "system_admin"
     * 
     * This directly matches the permission strings returned by the backend in the login response.
     */
    const hasPermissionString = (permissionString: string): boolean => {
        if (!user || !Array.isArray(user.permissions)) return false
        return user.permissions.includes(permissionString)
    }

    /**
     * Parse backend permission string to extract resource and action
     * Backend format: "{resource}_{action}"
     * Examples:
     *   "document_create" → { resource: "document", action: "create" }
     *   "user_delete" → { resource: "user", action: "delete" }
     *   "system_admin" → { resource: "system", action: "admin" }
     */
    const parseBackendPermission = (p: string): { resource: string | null; action: string | null } => {
        if (!p || typeof p !== 'string') return { resource: null, action: null }

        const parts = p.split('_')
        if (parts.length < 2) return { resource: null, action: null }

        // Join first n-1 parts as resource, last part as action
        const action = parts[parts.length - 1]
        const resource = parts.slice(0, -1).join('_')

        return { resource, action }
    }

    /**
     * Get permission level (ObjectPerm) for a backend permission string
     * Maps backend permissions to permission hierarchy
     */
    const getPermissionLevel = (permissionString: string): ObjectPerm => {
        const exactLevel = inferPermissionLevel(permissionString)
        if (exactLevel !== 'none') return exactLevel

        const { action } = parseBackendPermission(permissionString)
        if (!action) return 'none'

        return inferPermissionLevel(action)
    }

    /**
     * Check if user has permission for a specific resource action
     * Examples:
     *   hasActionPermission('create', 'document') 
     *   hasActionPermission('update', 'user')
     *   hasActionPermission('delete', 'folder')
     */
    const hasActionPermission = (action: string, resource?: string): boolean => {
        if (!user || !Array.isArray(user.permissions)) return false

        const normalizedAction = normalizePermission(action)
        const normalizedResource = resource ? normalizePermission(resource) : undefined

        // Check exact permission string match: "{resource}_{action}"
        if (normalizedResource) {
            const permString = `${normalizedResource}_${normalizedAction}`
            if (user.permissions.some(perm => normalizePermission(perm) === permString)) return true
        }

        // Check just the action (might be system-wide)
        if (user.permissions.some(perm => normalizePermission(perm) === normalizedAction)) return true

        // Check system_admin (has everything)
        if (user.permissions.some(perm => normalizePermission(perm) === 'system_admin')) return true

        // Infer the required level from the action name itself
        const requiredLevel = inferPermissionLevel(normalizedAction) || inferPermissionLevel(resource ? `${normalizedResource}_${normalizedAction}` : normalizedAction)

        // FALLBACK: Nếu action không nằm trong bất kỳ pattern nào (requiredLevel = 'none')
        // thì tin tưởng backend: nếu permission string đó có trong user.permissions, cấp phép
        if (requiredLevel === 'none') {
            if (normalizedResource) {
                const permString = `${normalizedResource}_${normalizedAction}`
                const hasExactPerm = user.permissions.some(perm => normalizePermission(perm) === permString)
                if (hasExactPerm) return true
            }
            // Không có permission, return false
            return false
        }

        if (normalizedResource) {
            for (const perm of user.permissions) {
                const { resource: permResource, action: permAction } = parseBackendPermission(perm)
                if (permResource?.toLowerCase() === normalizedResource) {
                    const permLevel = getPermissionLevel(perm)
                    if (PERM_WEIGHT[permLevel] >= PERM_WEIGHT[requiredLevel]) {
                        return true
                    }
                }
            }
        }

        return false
    }

    /**
     * Legacy: Check whether the user has a global permission (for backward compatibility)
     * Now maps to backend permission strings
     * 
     * Examples:
     *   hasGlobalPermission('create', 'document') → checks "document_create"
     *   hasGlobalPermission('read', 'user') → checks "user_read"
     *   hasGlobalPermission('delete', 'folder') → checks "folder_delete"
     */
    const hasGlobalPermission = (action: string, resourceType?: string, scope?: string) => {
        // For action-based permission checks
        if (resourceType) {
            return hasActionPermission(action, resourceType)
        }

        // For system-wide permissions
        return hasActionPermission(action)
    }

    // --- 5. Effective Permission Computation (legacy object-level) ---

    /**
     * Parse object-level permission string (legacy format: 'resource:action' or 'resource:scope:action')
     * Returns tuple [resourceType|null, scope|null, action|null]
     */
    const parsePermissionString = (p: string): [string | null, string | null, ObjectPerm | null] => {
        if (!p || typeof p !== 'string') return [null, null, null]
        const parts = p.split(':')
        // common forms:
        //  - document:write
        //  - department:{id}:write
        //  - folder:delete
        //  - write (fallback)
        let resourceType: string | null = null
        let scope: string | null = null
        let action: ObjectPerm | null = null
        if (parts.length === 1) {
            action = (['delete', 'write', 'read', 'none'].includes(parts[0]) ? (parts[0] as ObjectPerm) : null)
        } else if (parts.length === 2) {
            resourceType = parts[0]
            action = (['delete', 'write', 'read', 'none'].includes(parts[1]) ? (parts[1] as ObjectPerm) : null)
        } else if (parts.length === 3) {
            resourceType = parts[0]
            scope = parts[1]
            action = (['delete', 'write', 'read', 'none'].includes(parts[2]) ? (parts[2] as ObjectPerm) : null)
        }
        return [resourceType, scope, action]
    }

    /**
     * Compute the effective object permission for a given resource.
     * Combines multiple permission sources:
     * 1. my_permission from the resource object
     * 2. Global permissions from backend (user.permissions)
     * 3. Ownership (uploader, creator)
     * 
     * resource may have fields: my_permission, department_id, uploader_id, created_by_id
     * resourceType is a short string like 'document' or 'folder'
     */
    const getEffectivePermission = (
        resource: { my_permission?: ObjectPerm | null; department_id?: string | null; uploader_id?: string | null; created_by_id?: string | null } | null | undefined,
        resourceType?: string,
    ): ObjectPerm => {
        // Admins get full rights
        if (isAdmin()) return 'delete'

        // 1️⃣ Start with my_permission from resource
        let best: ObjectPerm = resource?.my_permission ?? 'none'

        // 2️⃣ Check global permissions from backend (NEW)
        if (resourceType && Array.isArray(user?.permissions)) {
            // Check exact permission match: "{resource}_{action}"
            for (const perm of user.permissions) {
                const normalized = normalizePermission(perm)
                const normalizedResource = normalizePermission(resourceType)

                // Match "{resource}_*" pattern (any action on this resource)
                if (normalized.startsWith(normalizedResource + '_')) {
                    const permLevel = getPermissionLevel(normalized)
                    if (PERM_WEIGHT[permLevel] > PERM_WEIGHT[best]) {
                        best = permLevel
                    }
                }
            }
        }

        // 3️⃣ Check ownership (uploader or creator)
        // Owner gets at least write permission
        if ((resource?.uploader_id && user?.id === resource.uploader_id) || (resource?.created_by_id && user?.id === resource.created_by_id)) {
            if (PERM_WEIGHT['write'] > PERM_WEIGHT[best]) {
                best = 'write'
            }
        }

        return best
    }

    return {
        user,
        isAdmin,
        isTruongPhong,
        isNhanVien,
        hasRole,
        can,
        canRead,
        canWrite,
        canDelete,
        canShare,
        isInDepartment,
        isAccessibleDepartment,
        isOwner,
        getRoleBadge,
        getEffectivePermission,
        parsePermissionString,
        hasGlobalPermission,
        // NEW: Backend permission helpers
        hasPermissionString,
        parseBackendPermission,
        getPermissionLevel,
        hasActionPermission,
    }
}
