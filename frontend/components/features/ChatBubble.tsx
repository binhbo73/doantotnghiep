// components/features/ChatBubble.tsx - Chat message bubbles with citation
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Body, Small } from '@/components/ui/text'
import { HTMLAttributes } from 'react'

interface Citation {
    documentId: string
    documentName: string
    chapter?: string
}

interface ChatBubbleProps extends HTMLAttributes<HTMLDivElement> {
    /**
     * Message content
     */
    content: string

    /**
     * Message sender
     */
    sender: 'user' | 'ai'

    /**
     * Source documents for AI responses
     */
    citations?: Citation[]

    /**
     * Timestamp
     */
    timestamp?: string
}

/**
 * ChatBubble - Display chat message with styling based on sender
 *
 * Design: Linear-inspired chat interface
 * - User messages: Purple bubble (right-aligned)
 * - AI messages: Dark card with border (left-aligned)
 * - Citations: Inline badge links to source documents
 *
 * @example
 * // User message
 * <ChatBubble sender="user" content="What's in the budget?" />
 *
 * // AI response with citations
 * <ChatBubble
 *   sender="ai"
 *   content="Based on the 2026 budget..."
 *   citations={[{ documentId: '1', documentName: 'Budget 2026' }]}
 * />
 */
export const ChatBubble = ({
    content,
    sender,
    citations,
    timestamp,
    ...props
}: ChatBubbleProps) => {
    return (
        <div
            className={`flex ${sender === 'user' ? 'justify-end' : 'justify-start'} mb-4`}
            {...props}
        >
            {sender === 'user' ? (
                // User message: Purple bubble, right-aligned
                <div className="max-w-[70%]">
                    <div
                        className={`
              bg-primary text-primary-foreground rounded-[12px] px-4 py-3
              ${sender === 'user' && 'rounded-br-[4px]'}
            `}
                    >
                        <Body variant="base" className="text-primary-foreground">
                            {content}
                        </Body>
                    </div>
                    {timestamp && (
                        <Small className="text-muted-foreground mt-1 text-right">
                            {new Date(timestamp).toLocaleTimeString('en-US', {
                                hour: '2-digit',
                                minute: '2-digit',
                                hour12: false,
                            })}
                        </Small>
                    )}
                </div>
            ) : (
                // AI message: Card with border, left-aligned
                <div className="max-w-[70%]">
                    <Card
                        elevation="base"
                        padding="md"
                        className="bg-card rounded-[12px] rounded-bl-[4px]"
                    >
                        <Body variant="base" className="text-foreground mb-3">
                            {content}
                        </Body>

                        {/* Citations */}
                        {citations && citations.length > 0 && (
                            <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-border">
                                {citations.map((citation, idx) => (
                                    <Badge
                                        key={idx}
                                        variant="primary"
                                        size="sm"
                                        shape="rounded"
                                        className="cursor-pointer hover:opacity-80 transition-opacity"
                                        title={`View: ${citation.documentName}${citation.chapter ? ` - ${citation.chapter}` : ''}`}
                                    >
                                        📄 {citation.documentName}
                                    </Badge>
                                ))}
                            </div>
                        )}
                    </Card>

                    {timestamp && (
                        <Small className="text-muted-foreground mt-1">
                            {new Date(timestamp).toLocaleTimeString('en-US', {
                                hour: '2-digit',
                                minute: '2-digit',
                                hour12: false,
                            })}
                        </Small>
                    )}
                </div>
            )}
        </div>
    )
}

export default ChatBubble
