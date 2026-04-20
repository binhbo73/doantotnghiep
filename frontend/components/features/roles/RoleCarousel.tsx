'use client'

import React from 'react'
import { RoleCard } from './RoleCard'
import { IamRole } from '@/types/api'

interface RoleCarouselProps {
    roles: IamRole[]
    selectedRoleId: string
    onSelectRole: (roleId: string) => void
    onViewDetails?: (roleId: string) => void
    onEditRole?: (roleId: string) => void
}

export function RoleCarousel({
    roles,
    selectedRoleId,
    onSelectRole,
    onViewDetails,
    onEditRole,
}: RoleCarouselProps) {
    const carouselRef = React.useRef<HTMLDivElement>(null)

    if (!roles || roles.length === 0) {
        return (
            <div className="text-center py-8" style={{ color: '#727785' }}>
                Không có vai trò nào
            </div>
        )
    }

    return (
        <div className="relative">
            {/* Carousel */}
            <div
                ref={carouselRef}
                className="overflow-x-auto scroll-smooth"
                style={{ scrollBehavior: 'smooth' }}
            >
                <div className="flex gap-3 pb-2">
                    {roles.map((role) => (
                        <div
                            key={role.id}
                            className="flex-shrink-0 w-64 cursor-pointer"
                            onClick={() => onSelectRole(role.id)}
                        >
                            <RoleCard
                                role={{
                                    id: role.id,
                                    name: role.name,
                                    code: role.code,
                                    description: role.description || '',
                                    memberCount: 0, // TODO: Get from API
                                    permissionCount: role.permission_count,
                                }}
                                isSelected={selectedRoleId === role.id}
                                onViewDetails={onViewDetails}
                                onEdit={onEditRole}
                            />
                        </div>
                    ))}
                </div>
            </div>
        </div>
    )
}
