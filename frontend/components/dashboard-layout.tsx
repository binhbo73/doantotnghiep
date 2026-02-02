'use client';

import React, { useState } from 'react';
import { Sidebar } from './sidebar';
import { ThemeToggle } from './theme-toggle';

interface DashboardLayoutProps {
  children: React.ReactNode;
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
  return (
    <div className="min-h-screen bg-background flex">
      <Sidebar />
      <main className="flex-1 flex flex-col md:ml-64 transition-all duration-300">
        <div className="sticky top-0 flex items-center justify-between p-3 md:p-4 border-b border-border bg-background/95 backdrop-blur">
          <div className="text-sm text-muted-foreground md:hidden">
            Dashboard
          </div>
          <ThemeToggle />
        </div>
        <div className="flex-1 overflow-y-auto p-3 md:p-6">
          {children}
        </div>
      </main>
    </div>
  );
}
