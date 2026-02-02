'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Button } from '@/components/ui/button';
import {
  MessageSquare,
  BookOpen,
  BarChart3,
  Settings,
  Menu,
  X,
  Plus,
  LogOut,
  User,
} from 'lucide-react';

const navigationItems = [
  { icon: MessageSquare, label: 'Chat', href: '/dashboard' },
  { icon: BookOpen, label: 'Knowledge Base', href: '/dashboard/knowledge-base' },
  { icon: BarChart3, label: 'Analytics', href: '/dashboard/analytics' },
  { icon: Settings, label: 'Settings', href: '/dashboard/settings' },
];

const chatHistory = [
  { id: 1, title: 'HR Policy Questions' },
  { id: 2, title: 'Product Documentation' },
  { id: 3, title: 'Training Materials' },
];

export function Sidebar() {
  const pathname = usePathname();
  const [isOpen, setIsOpen] = useState(true);
  const [isMobileOpen, setIsMobileOpen] = useState(false);

  return (
    <>
      {/* Mobile Menu Button */}
      <button
        onClick={() => setIsMobileOpen(!isMobileOpen)}
        className="fixed top-4 left-4 z-40 md:hidden"
      >
        {isMobileOpen ? (
          <X className="w-6 h-6" />
        ) : (
          <Menu className="w-6 h-6" />
        )}
      </button>

      {/* Sidebar */}
      <aside
        className={`fixed left-0 top-0 h-screen bg-sidebar border-r border-sidebar-border transition-all duration-300 z-30 overflow-y-auto ${
          isOpen ? 'w-64' : 'w-20'
        } ${isMobileOpen ? 'translate-x-0 w-64' : '-translate-x-full md:translate-x-0'}`}
      >
        <div className="flex flex-col h-full p-4 space-y-6">
          {/* Logo */}
          <div className="flex items-center justify-between">
            <div className={`flex items-center gap-2 transition-all ${isOpen ? 'opacity-100' : 'opacity-0'}`}>
              <div className="w-8 h-8 bg-sidebar-primary rounded-lg flex items-center justify-center">
                <span className="text-sidebar-primary-foreground font-bold text-sm">AI</span>
              </div>
              {isOpen && <span className="font-semibold text-foreground">KnowHub</span>}
            </div>
          </div>

          {/* Navigation */}
          <nav className="space-y-2 flex-1">
            {navigationItems.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href;
              return (
                <Link key={item.href} href={item.href}>
                  <button
                    className={`w-full flex items-center gap-3 px-4 py-2 rounded-lg transition-colors ${
                      isActive
                        ? 'bg-sidebar-primary text-sidebar-primary-foreground'
                        : 'text-sidebar-foreground hover:bg-sidebar-accent'
                    }`}
                  >
                    <Icon className="w-5 h-5 flex-shrink-0" />
                    {isOpen && <span>{item.label}</span>}
                  </button>
                </Link>
              );
            })}
          </nav>

          {/* Chat History */}
          {isOpen && (
            <div className="border-t border-sidebar-border pt-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-xs font-semibold text-sidebar-foreground uppercase">
                  Chat History
                </h3>
                <Button
                  variant="ghost"
                  size="sm"
                  className="w-6 h-6 p-0"
                  title="New chat"
                >
                  <Plus className="w-4 h-4" />
                </Button>
              </div>
              <div className="space-y-2">
                {chatHistory.map((chat) => (
                  <button
                    key={chat.id}
                    className="w-full text-left text-sm px-3 py-2 rounded-lg text-sidebar-foreground hover:bg-sidebar-accent transition-colors truncate"
                  >
                    {chat.title}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* User Profile */}
          <div className="border-t border-sidebar-border pt-4 space-y-3">
            <div className={`flex items-center gap-3 ${isOpen ? 'opacity-100' : 'opacity-0'}`}>
              <div className="w-8 h-8 rounded-full bg-sidebar-primary/20 flex items-center justify-center flex-shrink-0">
                <User className="w-4 h-4 text-sidebar-primary" />
              </div>
              {isOpen && (
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-sidebar-foreground truncate">
                    John Doe
                  </p>
                  <p className="text-xs text-sidebar-foreground/60 truncate">
                    john@example.com
                  </p>
                </div>
              )}
            </div>
            <Button
              variant="outline"
              size="sm"
              className={`w-full ${isOpen ? '' : 'w-10 h-10 p-0'}`}
              title="Logout"
            >
              {isOpen && <LogOut className="w-4 h-4 mr-2" />}
              {isOpen ? 'Logout' : <LogOut className="w-4 h-4" />}
            </Button>
          </div>
        </div>
      </aside>

      {/* Mobile Overlay */}
      {isMobileOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-20 md:hidden"
          onClick={() => setIsMobileOpen(false)}
        />
      )}

      {/* Main Content Offset */}
      <div className={`transition-all duration-300 ${isOpen ? 'md:ml-64' : 'md:ml-20'}`} />
    </>
  );
}
