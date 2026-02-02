'use client';

import React from 'react';
import { DashboardLayout } from '@/components/dashboard-layout';
import { FileUpload } from '@/components/file-upload';
import { FileTable } from '@/components/file-table';

export default function KnowledgeBasePage() {
  const handleUpload = (files: File[]) => {
    console.log('Files uploaded:', files);
    // Handle file upload logic here
  };

  return (
    <DashboardLayout>
      <div className="max-w-6xl mx-auto space-y-6 md:space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-2xl md:text-3xl font-bold">Knowledge Base</h1>
          <p className="text-sm md:text-base text-muted-foreground mt-1">
            Manage your organization's documents and resources
          </p>
        </div>

        {/* Upload Section */}
        <div>
          <h2 className="text-lg font-semibold mb-3 md:mb-4">Upload Documents</h2>
          <FileUpload onUpload={handleUpload} />
        </div>

        {/* Documents Table */}
        <div>
          <h2 className="text-lg font-semibold mb-3 md:mb-4">Your Documents</h2>
          <FileTable />
        </div>
      </div>
    </DashboardLayout>
  );
}
