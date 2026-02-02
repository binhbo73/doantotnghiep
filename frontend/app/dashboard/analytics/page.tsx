'use client';

import React from 'react';
import { DashboardLayout } from '@/components/dashboard-layout';
import { StatsCards } from '@/components/stats-cards';
import { AnalyticsCharts } from '@/components/analytics-charts';

export default function AnalyticsPage() {
  return (
    <DashboardLayout>
      <div className="max-w-7xl mx-auto space-y-6 md:space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-2xl md:text-3xl font-bold">Analytics</h1>
          <p className="text-sm md:text-base text-muted-foreground mt-1">
            Monitor your AI knowledge system performance
          </p>
        </div>

        {/* Stats Cards */}
        <StatsCards />

        {/* Charts */}
        <AnalyticsCharts />
      </div>
    </DashboardLayout>
  );
}
