// components/features/ChatBubble.tsx - Chat message bubbles with citation + asset support
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Body, Small } from '@/components/ui/text'
import { HTMLAttributes } from 'react'
import { AssetThumbnail, DocumentAsset } from './AssetThumbnail'

interface Citation {
    documentId: string
    documentName: string
    chapter?: string
    /** Asset citation - nếu có, hiển thị thumbnail ảnh */
    asset?: DocumentAsset
}

interface ChatBubbleProps extends HTMLAttributes<HTMLDivElement> {
    content: string
    sender: 'user' | 'ai'
    citations?: Citation[]
    timestamp?: string
    onViewDocument?: (documentId: string) => void
}

/**
 * ChatBubble - Display chat message with styling based on sender.
 *
 * Hỗ trợ 2 loại citation:
 * - Document citation: badge link tới tài liệu
 * - Asset citation: thumbnail ảnh từ OCR/VL pipeline
 */
export const ChatBubble = ({
    content,
    sender,
    citations,
    timestamp,
    onViewDocument,
    ...props
}: ChatBubbleProps) => {
    return (
        <div
            className={`flex ${sender === 'user' ? 'justify-end' : 'justify-start'} mb-4`}
            {...props}
        >
            {sender === 'user' ? (
                <div className="max-w-[70%]">
                    <div className="bg-primary text-primary-foreground rounded-[12px] rounded-br-[4px] px-4 py-3">
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
                            <div className="flex flex-col gap-3 mt-3 pt-3 border-t border-border">
                                {/* Asset thumbnails */}
                                {citations.some(c => c.asset) && (
                                    <div className="flex flex-wrap gap-2">
                                        {citations
                                            .filter(c => c.asset)
                                            .map((citation, idx) => (
                                                <AssetThumbnail
                                                    key={`asset-${idx}`}
                                                    asset={citation.asset!}
                                                    onViewDocument={onViewDocument}
                                                />
                                            ))}
                                    </div>
                                )}

                                {/* Document badges */}
                                {citations.some(c => !c.asset) && (
                                    <div className="flex flex-wrap gap-2">
                                        {citations
                                            .filter(c => !c.asset)
                                            .map((citation, idx) => (
                                                <Badge
                                                    key={`doc-${idx}`}
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
