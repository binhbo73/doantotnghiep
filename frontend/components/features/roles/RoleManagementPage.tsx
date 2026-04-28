'use client'

import React, { useState, useMemo } from 'react'
import { RoleCarousel } from './RoleCarousel'
import { PermissionMatrix } from './PermissionMatrix'
import { CreateRoleDialog, RoleDetailDialog } from './dialogs'
import { CreatePermissionDialog } from './dialogs'
import { createPermission } from '@/services/iam'
import { useRoles } from '@/hooks/useRoles'
import { useUpdateRole } from '@/hooks/useUpdateRole'
import { useDeleteRole } from '@/hooks/useDeleteRole'
import { useRolePermissions } from '@/hooks/useRolePermissions'

export function RoleManagementPage() {
  const [selectedRoleId, setSelectedRoleId] = useState<string>('')
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false)
  const [isCreatePermissionDialogOpen, setIsCreatePermissionDialogOpen] = useState(false)
  const [detailRoleId, setDetailRoleId] = useState<string | null>(null)
  const [editRoleId, setEditRoleId] = useState<string | null>(null)
  const [permissionRefreshKey, setPermissionRefreshKey] = useState(0)

  const { roles, loading: rolesLoading, error: rolesError, useFallback: rolesUseFallback, refetch: refetchRoles } = useRoles({
    page: 1,
    page_size: 100,
  })

  const { updateRole } = useUpdateRole()
  const { deleteRole } = useDeleteRole()

  // Fetch current permissions for edit mode
  const { permissions: editRolePermissions, loading: editPermissionsLoading } = useRolePermissions(editRoleId || '')

  // Set first role as selected when roles load
  React.useEffect(() => {
    if (roles.length > 0 && !selectedRoleId) {
      setSelectedRoleId(roles[0].id)
    }
  }, [roles, selectedRoleId])

  const handleCreateRole = (data: {
    code: string
    displayName: string
    description: string
    permissions: Array<{ id: string; name: string; checked: boolean }>
  }) => {
    console.log('Creating role:', data)
    setIsCreateDialogOpen(false)
    refetchRoles()
  }

  const handleCreatePermission = async (data: {
    code: string
    name: string
    resource: string
    action: string
    description: string
  }) => {
    try {
      await createPermission({
        code: data.code.trim().toLowerCase(),
        name: data.name.trim(),
        resource: data.resource.trim(),
        action: data.action.trim(),
        description: data.description.trim(),
      })

      setIsCreatePermissionDialogOpen(false)
      // trigger permission matrix to refresh
      setPermissionRefreshKey((k) => k + 1)
    } catch (error) {
      console.error('Failed to create permission:', error)
      throw error
    }
  }

  const handleEditRole = (roleId: string) => {
    setEditRoleId(roleId)
    setDetailRoleId(null)
  }

  const handleUpdateRole = async (data: {
    code: string
    displayName: string
    description: string
    permissions: Array<{ id: string; name: string; checked: boolean }>
  }) => {
    if (!editRoleId) return

    try {
      const permissionIds = data.permissions
        .filter((p) => p.checked)
        .map((p) => p.id)

      await updateRole(editRoleId, {
        name: data.displayName,
        description: data.description,
        permission_ids: permissionIds,
      })

      setEditRoleId(null)
      await refetchRoles()

      console.log('✅ Cập nhật vai trò thành công')
    } catch (error) {
      console.error('❌ Lỗi cập nhật vai trò:', error)
      throw error
    }
  }

  const handleDeleteRole = async (roleId: string) => {
    try {
      await deleteRole(roleId)
      await refetchRoles()

      console.log('✅ Xóa vai trò thành công')
    } catch (error) {
      console.error('❌ Lỗi xóa vai trò:', error)
      throw error
    }
  }

  const selectedRole = roles.find((r) => r.id === selectedRoleId) || null
  const detailRole = roles.find((r) => r.id === detailRoleId) || null
  const editRole = roles.find((r) => r.id === editRoleId) || null

  // Build initialData for edit mode with current permissions
  const editRoleInitialData = useMemo(() => {
    if (!editRole || editPermissionsLoading) {
      return undefined
    }

    return {
      code: editRole.code,
      displayName: editRole.name,
      description: editRole.description || '',
      permissions: editRolePermissions.map((perm) => ({
        ...perm,
        name: perm.code, // Map 'code' to 'name' for Permission interface
        checked: true,
      })) as any[],
    }
  }, [editRole, editRolePermissions, editPermissionsLoading])

  return (
    <div className="min-h-screen" style={{ backgroundColor: '#f9f9ff' }}>
      {/* Header Section */}
      <div className="px-3 lg:px-4 py-2 border-b" style={{ borderColor: '#dce2f3', backgroundColor: '#ffffff' }}>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <h1 className="text-lg font-bold mb-0.5" style={{ color: '#151c27' }}>
              Cấu hình Quyền hạn Hệ thống
            </h1>
            <p className="text-xs" style={{ color: '#727785' }}>
              Xây dựng kiến trúc bảo mật và phân tầng truy cập cho doanh nghiệp của bạn.
            </p>
          </div>
          <div className="flex items-center ml-4 gap-2">
            <button
              type="button"
              onClick={() => setIsCreatePermissionDialogOpen(true)}
              className="px-3 py-1.5 rounded-lg font-medium text-xs transition whitespace-nowrap flex items-center gap-1"
              style={{
                backgroundColor: '#ffffff',
                color: '#0058be',
                border: '1px solid #0058be',
              }}
            >
              <span>🔐</span> Tạo quyền hạn mới
            </button>

            <button
              onClick={() => setIsCreateDialogOpen(true)}
              className="px-3 py-1.5 rounded-lg font-medium text-xs text-white transition whitespace-nowrap flex items-center gap-1"
              style={{ backgroundColor: '#b75b00' }}
            >
              <span>➕</span> Tạo vai trò mới
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="px-3 lg:px-4 py-2 space-y-2">
        {/* Current Roles Section */}
        <div>
          <h2 className="text-base font-bold mb-2 flex items-center gap-1.5" style={{ color: '#151c27' }}>
            <span>Vai trò hiện tại ({roles.length})</span>
            {rolesUseFallback && (
              <span className="text-xs px-1.5 py-0.5 rounded" style={{ color: '#f57c00', backgroundColor: '#fff3e0' }}>
                Demo Data
              </span>
            )}
          </h2>
          {rolesLoading && !rolesUseFallback ? (
            <div className="text-center py-8" style={{ color: '#727785' }}>
              Đang tải vai trò...
            </div>
          ) : rolesError && !rolesUseFallback ? (
            <div className="text-center py-8 text-red-600">
              Lỗi tải vai trò: {rolesError.message}
            </div>
          ) : (
            <RoleCarousel
              roles={roles}
              selectedRoleId={selectedRoleId}
              onSelectRole={setSelectedRoleId}
              onViewDetails={(roleId) => setDetailRoleId(roleId)}
              onEditRole={handleEditRole}
            />
          )}
        </div>

        {/* Permission Matrix Section */}
        <div>
          <h2 className="text-base font-bold mb-2" style={{ color: '#151c27' }}>
            Danh mục Quyền hạn Hệ thống
          </h2>
          {/* pass permission refresh key so matrix can refetch when new permission created */}
          <PermissionMatrix selectedRoleId={selectedRoleId} refreshKey={permissionRefreshKey} />
        </div>
      </div>

      {/* Create/Edit Role Dialog */}
      <CreateRoleDialog
        isOpen={isCreateDialogOpen || !!editRoleId}
        isEdit={!!editRoleId}
        initialData={editRoleInitialData}
        onClose={() => {
          setIsCreateDialogOpen(false)
          setEditRoleId(null)
        }}
        onSubmit={editRoleId ? handleUpdateRole : handleCreateRole}
      />

      <CreatePermissionDialog
        isOpen={isCreatePermissionDialogOpen}
        onClose={() => setIsCreatePermissionDialogOpen(false)}
        onSubmit={handleCreatePermission}
      />

      {/* Role Detail Dialog */}
      <RoleDetailDialog
        isOpen={!!detailRoleId}
        role={detailRole}
        onClose={() => setDetailRoleId(null)}
        onEdit={(roleId) => handleEditRole(roleId)}
        onDelete={handleDeleteRole}
      />
    </div>
  )
}
