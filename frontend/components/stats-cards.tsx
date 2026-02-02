'use client';

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { TrendingUp, FileText, CheckCircle, Users } from 'lucide-react';

interface StatCard {
  title: string;
  value: string;
  change: string;
  icon: React.ReactNode;
  color: string;
}

export function StatsCards() {
  const stats: StatCard[] = [
    {
      title: 'Total Documents',
      value: '156',
      change: '+12 this month',
      icon: <FileText className="w-6 h-6" />,
      color: 'text-blue-500',
    },
    {
      title: 'Total Queries',
      value: '2,847',
      change: '+23% from last month',
      icon: <TrendingUp className="w-6 h-6" />,
      color: 'text-green-500',
    },
    {
      title: 'Success Rate',
      value: '94.2%',
      change: '+2.1% from last month',
      icon: <CheckCircle className="w-6 h-6" />,
      color: 'text-emerald-500',
    },
    {
      title: 'Active Users',
      value: '324',
      change: '+18 this week',
      icon: <Users className="w-6 h-6" />,
      color: 'text-purple-500',
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {stats.map((stat, idx) => (
        <Card key={idx}>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">{stat.title}</CardTitle>
            <div className={stat.color}>{stat.icon}</div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stat.value}</div>
            <p className="text-xs text-muted-foreground mt-1">{stat.change}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
