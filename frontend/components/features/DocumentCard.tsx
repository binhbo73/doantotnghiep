// components/features/DocumentCard.tsx - Document list card component
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Caption, Body } from '@/components/ui/text'
import { HTMLAttributes } from 'react'

interface DocumentCardProps extends HTMLAttributes<HTMLDivElement> {
    /**
     * Document data
     */
    document: {
        id: string
        name: string
        size: number
        uploadedAt: string
        accessLevel: 'public' | 'internal' | 'restricted' | 'personal'
    }

    /**
     * Callbacks for actions
     */
    onPreview?: () => void
    onShare?: () => void
    onDelete?: () => void
}

/**
 * DocumentCard - Display document with metadata and access level
 *
 * Design: Following Linear design for document management
 * - Card with hover state
 * - Permission badge (color-coded)
 * - Quick actions on hover
 * - Metadata: size, date
 *
 * @example
 * <DocumentCard
 *   document={{
 *     id: '1',
 *     name: 'Budget 2026',
 *     size: 2.5,
 *     uploadedAt: '2026-04-16',
 *     accessLevel: 'internal'
 *   }}
 *   onPreview={() => {}}
 *   onDelete={() => {}}
 * />
 */
export const DocumentCard = ({
    document,
    onPreview,
    onShare,
    onDelete,
    ...props
}: DocumentCardProps) => {
    const formatSize = (bytes: number): string => {
        if (bytes === 0) return '0 B'
        const k = 1024
        const sizes = ['B', 'KB', 'MB', 'GB']
        const i = Math.floor(Math.log(bytes) / Math.log(k))
        return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
    }

    const accessLevelConfig = {
        public: { color: 'success' as const, label: 'Public' },
        internal: { color: 'primary' as const, label: 'Internal' },
        restricted: { color: 'error' as const, label: 'Restricted' },
        personal: { color: 'subtle' as const, label: 'Personal' },
    }

    const config = accessLevelConfig[document.accessLevel]

    return (
        <Card elevation="base" padding="md" className="group" {...props}>
            <div className="flex items-start justify-between">
                <div className="flex-1">
                    <Body variant="medium" className="text-foreground mb-2">
                        📄 {document.name}
                    </Body>

                    <div className="flex items-center gap-3">
                        <Caption variant="base" className="text-muted-foreground">
                            {formatSize(document.size * 1024 * 1024)}
                        </Caption>
                        <span className="text-border">•</span>
                        <Caption variant="base" className="text-muted-foreground">
                            {new Date(document.uploadedAt).toLocaleDateString('vi-VN')}
                        </Caption>
                    </div>
                </div>

                <Badge variant={config.color} size="sm" shape="rounded" className="ml-3">
                    {config.label}
                </Badge>
            </div>

            {/* Quick actions - shown on hover */}
            <div className="flex gap-2 mt-3 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                <Button variant="subtle" size="sm" onClick={onPreview}>
                    Preview
                </Button>
                {onShare && (
                    <Button variant="subtle" size="sm" onClick={onShare}>
                        Share
                    </Button>
                )}
                {onDelete && (
                    <Button variant="danger" size="sm" onClick={onDelete}>
                        Delete
                    </Button>
                )}
            </div>
        </Card>
    )
}

export default DocumentCard
