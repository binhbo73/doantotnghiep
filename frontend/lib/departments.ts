/**
 * Department Management Utilities
 * Helper functions for department operations
 */

export interface Department {
    id: string
    name: string
    description: string
    memberCount: number
    leadName: string
    leadEmail: string
    bgColor?: string
}

/**
 * Color palette for department cards
 */
export const departmentColors = [
    '#ffeaa7', // Yellow
    '#74b9ff', // Blue
    '#dfe6e9', // Gray
    '#fab1a0', // Orange
    '#55efc4', // Green
    '#fd79a8', // Pink
    '#fdcb6e', // Gold
    '#6c5ce7', // Purple
]

/**
 * Get a random color for a department
 */
export function getRandomDepartmentColor(): string {
    return departmentColors[Math.floor(Math.random() * departmentColors.length)]
}

/**
 * Validate department form data
 */
export function validateDepartmentData(data: {
    name?: string
    description?: string
    leadName?: string
    leadEmail?: string
}): Record<string, string> {
    const errors: Record<string, string> = {}

    if (!data.name?.trim()) {
        errors.name = 'Tên phòng ban là bắt buộc'
    } else if (data.name.length < 3) {
        errors.name = 'Tên phòng ban phải có ít nhất 3 ký tự'
    }

    if (!data.description?.trim()) {
        errors.description = 'Mô tả là bắt buộc'
    }

    if (!data.leadName?.trim()) {
        errors.leadName = 'Tên trưởng phòng là bắt buộc'
    }

    if (!data.leadEmail?.trim()) {
        errors.leadEmail = 'Email trưởng phòng là bắt buộc'
    } else if (!isValidEmail(data.leadEmail)) {
        errors.leadEmail = 'Email không hợp lệ'
    }

    return errors
}

/**
 * Validate email format
 */
export function isValidEmail(email: string): boolean {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    return emailRegex.test(email)
}

/**
 * Format department data for export
 */
export function formatDepartmentsForExport(
    departments: Department[]
): string {
    const headers = ['ID', 'Tên', 'Mô tả', 'Thành viên', 'Trưởng phòng', 'Email']
    const rows = departments.map((dept) => [
        dept.id,
        dept.name,
        dept.description,
        dept.memberCount,
        dept.leadName,
        dept.leadEmail,
    ])

    const csv = [
        headers.join(','),
        ...rows.map((row) =>
            row
                .map((cell) =>
                    typeof cell === 'string' && cell.includes(',')
                        ? `"${cell}"`
                        : cell
                )
                .join(',')
        ),
    ].join('\n')

    return csv
}

/**
 * Export departments as CSV file
 */
export function exportDepartmentsAsCSV(departments: Department[]): void {
    const csv = formatDepartmentsForExport(departments)
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    const url = URL.createObjectURL(blob)

    link.setAttribute('href', url)
    link.setAttribute('download', `departments_${new Date().toISOString().split('T')[0]}.csv`)
    link.style.visibility = 'hidden'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
}

/**
 * Sort departments by property
 */
export function sortDepartments(
    departments: Department[],
    sortBy: 'name' | 'members' | 'recent'
): Department[] {
    const sorted = [...departments]

    switch (sortBy) {
        case 'name':
            return sorted.sort((a, b) => a.name.localeCompare(b.name, 'vi'))
        case 'members':
            return sorted.sort((a, b) => b.memberCount - a.memberCount)
        case 'recent':
            return sorted.reverse()
        default:
            return sorted
    }
}

/**
 * Filter departments by search query
 */
export function filterDepartmentsByQuery(
    departments: Department[],
    query: string
): Department[] {
    if (!query.trim()) return departments

    const lowerQuery = query.toLowerCase()
    return departments.filter(
        (dept) =>
            dept.name.toLowerCase().includes(lowerQuery) ||
            dept.description.toLowerCase().includes(lowerQuery) ||
            dept.leadName.toLowerCase().includes(lowerQuery)
    )
}

/**
 * Calculate department statistics
 */
export function calculateDepartmentStats(departments: Department[]) {
    return {
        totalDepartments: departments.length,
        totalMembers: departments.reduce((sum, dept) => sum + dept.memberCount, 0),
        avgMembersPerDepartment:
            departments.length > 0
                ? Math.round(
                      (departments.reduce((sum, dept) => sum + dept.memberCount, 0) /
                          departments.length) *
                          100
                  ) / 100
                : 0,
        largestDepartment:
            departments.length > 0
                ? departments.reduce((max, dept) =>
                      dept.memberCount > max.memberCount ? dept : max
                  )
                : null,
        smallestDepartment:
            departments.length > 0
                ? departments.reduce((min, dept) =>
                      dept.memberCount < min.memberCount ? dept : min
                  )
                : null,
    }
}
