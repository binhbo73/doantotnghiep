'use client'

import { Display, Heading, Body, Small } from '@/components/ui/text'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { DocumentCard } from '@/components/features/DocumentCard'
import { ChatBubble } from '@/components/features/ChatBubble'
import { UserAvatar } from '@/components/features/UserAvatar'
import { cn } from '@/lib/cn'

export default function DashboardPage() {
    const mockDocuments = [
        {
            id: '1',
            name: 'Budget 2026',
            size: 2.5,
            uploadedAt: '2026-04-16',
            accessLevel: 'internal' as const,
        },
        {
            id: '2',
            name: 'Annual Report',
            size: 5.8,
            uploadedAt: '2026-04-15',
            accessLevel: 'public' as const,
        },
        {
            id: '3',
            name: 'Confidential Data',
            size: 1.2,
            uploadedAt: '2026-04-14',
            accessLevel: 'restricted' as const,
        },
    ]

    const mockMessages = [
        {
            id: '1',
            sender: 'user' as const,
            content: "What's in the 2026 budget?",
            timestamp: '2026-04-16T10:30:00',
            citations: undefined,
        },
        {
            id: '2',
            sender: 'ai' as const,
            content:
                'The 2026 budget allocates $5M for technology, $3M for marketing, and $2M for operations. This is primarily focused on scaling our AI infrastructure.',
            citations: [{ documentId: '1', documentName: 'Budget 2026', chapter: 'Executive Summary' }],
            timestamp: '2026-04-16T10:30:05',
        },
    ]

    return (
        <main className="min-h-screen bg-[var(--color-panel-dark)]">
            {/* Header */}
            <header className="border-b border-[rgba(255,255,255,0.08)] p-6">
                <div className="max-w-6xl mx-auto flex items-center justify-between">
                    <Display level="base" className="text-[#f7f8f8]">
                        Dashboard
                    </Display>
                    <div className="flex items-center gap-4">
                        <UserAvatar initial="JD" role="admin" size="md" />
                        <Button variant="ghost" size="md">
                            Logout
                        </Button>
                    </div>
                </div>
            </header>

            <div className="max-w-6xl mx-auto p-6 space-y-12">
                {/* Welcome Section */}
                <Card elevation="elevated" padding="lg" className="border-l-4 border-l-[#5e6ad2]">
                    <Heading level={1} className="text-[#f7f8f8] mb-2">
                        📊 Dashboard
                    </Heading>
                    <Body className="text-[#d0d6e0] mb-3">
                        Welcome to your RAG System Dashboard with Linear-inspired design.
                    </Body>
                    <ul className="space-y-2">
                        <li className="flex items-start gap-2">
                            <span className="text-[#10b981]">✓</span>
                            <Body className="text-[#d0d6e0]">Modern design system integrated</Body>
                        </li>
                        <li className="flex items-start gap-2">
                            <span className="text-[#10b981]">✓</span>
                            <Body className="text-[#d0d6e0]">Document management with access control</Body>
                        </li>
                        <li className="flex items-start gap-2">
                            <span className="text-[#10b981]">✓</span>
                            <Body className="text-[#d0d6e0]">AI-powered chat with citations</Body>
                        </li>
                    </ul>
                </Card>

                {/* Documents Section */}
                <section className="space-y-4">
                    <Heading level={1}>Your Documents</Heading>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {mockDocuments.map((doc) => (
                            <DocumentCard
                                key={doc.id}
                                document={doc}
                                onPreview={() => console.log('Preview:', doc.name)}
                                onDelete={() => console.log('Delete:', doc.name)}
                            />
                        ))}
                    </div>
                </section>

                {/* Chat Section */}
                <section className="space-y-4">
                    <Heading level={1}>Chat Assistant</Heading>
                    <Card elevation="base" padding="lg" className="max-w-2xl">
                        <div className="space-y-4 mb-4">
                            {mockMessages.map((msg) => (
                                <ChatBubble key={msg.id} {...msg} />
                            ))}
                        </div>
                    </Card>
                </section>
            </div>
        </main>
    )
}
