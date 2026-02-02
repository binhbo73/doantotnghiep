'use client';

import React, { useState } from 'react';
import { DashboardLayout } from '@/components/dashboard-layout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';

export default function SettingsPage() {
  const [settings, setSettings] = useState({
    email: 'john@example.com',
    notifications: true,
    emailAlerts: true,
    language: 'en',
    autoIndex: true,
  });

  const handleSave = () => {
    console.log('Settings saved:', settings);
  };

  return (
    <DashboardLayout>
      <div className="max-w-2xl mx-auto space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-2xl md:text-3xl font-bold">Settings</h1>
          <p className="text-sm md:text-base text-muted-foreground mt-1">
            Manage your account and system preferences
          </p>
        </div>

        {/* Account Settings */}
        <Card>
          <CardHeader>
            <CardTitle>Account Settings</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="email">Email Address</Label>
              <Input
                id="email"
                type="email"
                value={settings.email}
                onChange={(e) =>
                  setSettings({ ...settings, email: e.target.value })
                }
                className="mt-1"
              />
            </div>
            <div>
              <Label htmlFor="language">Language</Label>
              <Select value={settings.language}>
                <SelectTrigger className="mt-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="en">English</SelectItem>
                  <SelectItem value="es">Español</SelectItem>
                  <SelectItem value="fr">Français</SelectItem>
                  <SelectItem value="de">Deutsch</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* Notification Settings */}
        <Card>
          <CardHeader>
            <CardTitle>Notifications</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">In-App Notifications</p>
                <p className="text-sm text-muted-foreground">
                  Receive notifications within the app
                </p>
              </div>
              <Switch
                checked={settings.notifications}
                onCheckedChange={(checked) =>
                  setSettings({ ...settings, notifications: checked })
                }
              />
            </div>
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Email Alerts</p>
                <p className="text-sm text-muted-foreground">
                  Receive email notifications about system events
                </p>
              </div>
              <Switch
                checked={settings.emailAlerts}
                onCheckedChange={(checked) =>
                  setSettings({ ...settings, emailAlerts: checked })
                }
              />
            </div>
          </CardContent>
        </Card>

        {/* System Settings */}
        <Card>
          <CardHeader>
            <CardTitle>System Settings</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Auto-Indexing</p>
                <p className="text-sm text-muted-foreground">
                  Automatically index new documents
                </p>
              </div>
              <Switch
                checked={settings.autoIndex}
                onCheckedChange={(checked) =>
                  setSettings({ ...settings, autoIndex: checked })
                }
              />
            </div>
          </CardContent>
        </Card>

        {/* Actions */}
        <div className="flex gap-3 justify-end">
          <Button variant="outline">Cancel</Button>
          <Button onClick={handleSave}>Save Settings</Button>
        </div>
      </div>
    </DashboardLayout>
  );
}
