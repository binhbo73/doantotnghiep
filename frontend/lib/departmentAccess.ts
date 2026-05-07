import type { Department } from '@/types/api'
import type { User } from '@/types'

function isManagedByUser(department: Department, userId: string) {
    if (department.manager_id === userId) return true
    return Array.isArray(department.manager_ids) && department.manager_ids.includes(userId)
}

function buildDepartmentLookup(departments: Department[]) {
    return new Map(departments.filter((department) => !department.is_deleted).map((department) => [department.id, department]))
}

function isDescendantOf(departmentsById: Map<string, Department>, targetId: string, ancestorId: string) {
    let current = departmentsById.get(targetId)
    let safety = 0

    while (current && safety < 50) {
        if (current.id === ancestorId) return true
        if (!current.parent_id) return false
        current = departmentsById.get(current.parent_id)
        safety += 1
    }

    return false
}

export function canAccessDepartmentDetail(params: {
    user: User | null | undefined
    targetDeptId: string
    departments: Department[]
    isAdmin: boolean
    isTruongPhong: boolean
}) {
    const { user, targetDeptId, departments, isAdmin, isTruongPhong } = params

    if (isAdmin) return true
    if (!user) return false
    if (user.department_id === targetDeptId) return true

    if (!isTruongPhong) return false

    const departmentsById = buildDepartmentLookup(departments)
    const managedDepartments = departments.filter((department) => isManagedByUser(department, user.id))

    return managedDepartments.some((managedDepartment) =>
        isDescendantOf(departmentsById, targetDeptId, managedDepartment.id)
    )
}

export function canEditDepartment(params: {
    user: User | null | undefined
    targetDeptId: string
    departments: Department[]
    isAdmin: boolean
    isTruongPhong: boolean
}) {
    const { user, targetDeptId, departments, isAdmin, isTruongPhong } = params

    if (isAdmin) return true
    if (!user || !isTruongPhong) return false

    return canAccessDepartmentDetail({
        user,
        targetDeptId,
        departments,
        isAdmin,
        isTruongPhong,
    })
}

export function filterVisibleDepartments(params: {
    user: User | null | undefined
    departments: Department[]
    isAdmin: boolean
    isTruongPhong: boolean
}) {
    const { user, departments, isAdmin, isTruongPhong } = params

    if (isAdmin) return departments
    if (!user) return []

    const targetIds = new Set<string>()

    if (isTruongPhong) {
        departments.forEach((department) => {
            if (
                department.manager_id === user.id ||
                (Array.isArray(department.manager_ids) && department.manager_ids.includes(user.id))
            ) {
                targetIds.add(department.id)
                departments.forEach((candidate) => {
                    if (isDescendantOf(buildDepartmentLookup(departments), candidate.id, department.id)) {
                        targetIds.add(candidate.id)
                    }
                })
            }
        })
        return departments.filter((department) => targetIds.has(department.id))
    }

    if (user.department_id) {
        const departmentById = buildDepartmentLookup(departments)
        const department = departmentById.get(user.department_id)
        if (department) return [department]
    }

    return []
}
