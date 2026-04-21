'use client'

import React from 'react'
import { Building2, Users, TrendingUp, AlertCircle } from 'lucide-react'

interface DepartmentStatsProps {
    totalDepartments: number
    totalMembers: number
    activeDepartments: number
    avgMembersPerDepartment: number
}

export function DepartmentStats({
    totalDepartments,
    totalMembers,
    activeDepartments,
    avgMembersPerDepartment,
}: DepartmentStatsProps) {
    const stats = [
        {
            icon: Building2,
            label: 'Tổng phòng ban',
            value: totalDepartments,
            bgColor: '#ffeaa7',
            color: '#d35400',
        },
        {
            icon: Users,
            label: 'Tổng thành viên',
            value: totalMembers,
            bgColor: '#74b9ff',
            color: '#0984e3',
        },
        {
            icon: TrendingUp,
            label: 'Phòng ban hoạt động',
            value: activeDepartments,
            bgColor: '#55efc4',
            color: '#00b894',
        },
        {
            icon: AlertCircle,
            label: 'Trung bình thành viên',
            value: avgMembersPerDepartment.toFixed(0),
            bgColor: '#fab1a0',
            color: '#e17055',
        },
    ]

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            {stats.map((stat, index) => {
                const Icon = stat.icon
                return (
                    <div
                        key={index}
                        className="rounded-lg p-4 transition-all hover:shadow-md"
                        style={{
                            backgroundColor: '#ffffff',
                            border: '1px solid #f0f0f0',
                        }}
                    >
                        <div className="flex items-start justify-between">
                            <div className="flex-1">
                                <p
                                    className="text-xs font-medium mb-1"
                                    style={{ color: '#727785' }}
                                >
                                    {stat.label}
                                </p>
                                <h3
                                    className="text-2xl font-bold"
                                    style={{ color: stat.color }}
                                >
                                    {stat.value}
                                </h3>
                            </div>
                            <div
                                className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0"
                                style={{
                                    backgroundColor: stat.bgColor,
                                }}
                            >
                                <Icon
                                    className="w-5 h-5"
                                    style={{ color: stat.color }}
                                />
                            </div>
                        </div>
                    </div>
                )
            })}
        </div>
    )
}
