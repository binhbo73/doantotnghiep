'use client'

import React, { useState, useEffect, useRef } from 'react'
import { api } from '@/services/api/client'
import DOMPurify from 'dompurify'
import { logger } from '@/services/logger'

interface WordViewerProps {
    fileUrl: string
    searchText?: string
    chunkText?: string
    answerContext?: string
    assetImage?: {
        id?: string
        paragraphIndex?: number
        imageIndex?: number
        position?: Record<string, number>
        imageEndpoint?: string
        caption?: string
        contextText?: string
    }
    citationTarget?: {
        documentId?: string
        chunkId?: string
        page?: number
        chunkIndex?: number
        startChar?: number
        endChar?: number
        lineStart?: number
        lineEnd?: number
    }
    onLoadSuccess: () => void
    onLoadError: (error: Error) => void
    onScrollStatsChange?: (currentPage: number, totalPages: number) => void
}

const SEARCH_STOPWORDS = new Set([
    'nguon', 'source', 'trang', 'chunk', 'dong', 'cua', 'cho', 'va', 'cac', 'nhung',
    'trong', 'voi', 'duoc', 'khong', 'co', 'la', 'de', 'mot', 'nay', 'do', 'da',
    'se', 'khi', 'chi', 'thi', 'ra', 'vao', 'nhu', 'nen', 'qua', 'rat', 'hay',
    'con', 'the', 'this', 'that', 'from', 'with', 'your', 'have', 'are', 'nguoi',
    'viec', 'tai', 'sau', 'tren', 'can', 'phai', 'theo', 'dia', 'ty',
])

function normalizeText(value: string) {
    return value
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .replace(/\u0111/g, 'd')
        .replace(/\u0110/g, 'd')
        .toLowerCase()
}

function normalizeTextWithMap(value: string) {
    let normalized = ''
    const map: number[] = []

    Array.from(value).forEach((char, index) => {
        const normalizedChar = normalizeText(char)
        Array.from(normalizedChar).forEach((part) => {
            normalized += part
            map.push(index)
        })
    })

    return { normalized, map }
}

function stripCitationMarkup(text?: string) {
    return (text || '')
        .replace(/\[(?:Ngu[^\]]*|Source):[^\]]+\]\s*\[\d{1,3}\]/gi, ' ')
        .replace(/\[\d{1,3}\]/g, ' ')
        .replace(/\s+/g, ' ')
        .trim()
}

function getReferenceTokens(text?: string) {
    const words = normalizeText(stripCitationMarkup(text))
        .split(/[^a-z0-9]+/i)
        .filter((word) => {
            if (!word) return false
            if (/^\d+$/.test(word)) return true
            return word.length >= 3 && !SEARCH_STOPWORDS.has(word)
        })

    return Array.from(new Set(words))
}

function getSearchPhrases(searchText?: string): string[] {
    const cleaned = (searchText || '')
        .replace(/\[Nguon:[^\]]+\]/gi, ' ')
        .replace(/\[[0-9]+\]/g, ' ')
        .replace(/\s+/g, ' ')
        .trim()

    if (!cleaned) return []

    // Tach bang nhieu loai ranh gioi: dau cau, xuong dong, dau cham phay
    const chunks = cleaned
        .split(/(?:[.!?\u2026]\s+|\n+|;\s+)/)
        .map((part) => part.replace(/^[-*\d]+[.)]?\s*/, '').trim())
        .filter((part) => part.length >= 10)

    return Array.from(new Set(chunks))
        .sort((a, b) => b.length - a.length)
        .slice(0, 10)
}

function findBestPreviewBlock(root: HTMLElement, referenceText?: string): HTMLElement | null {
    const referenceTokens = getReferenceTokens(referenceText)
    if (!referenceTokens.length) return null

    const phrases = getSearchPhrases(referenceText).map((phrase) => normalizeText(phrase))
    const candidates = Array.from(
        root.querySelectorAll('p, li, td, th, h1, h2, h3, h4, h5, h6, blockquote, pre, div, section, article')
    ) as HTMLElement[]

    let best: { element: HTMLElement; score: number } | null = null

    for (const element of candidates) {
        const text = normalizeText(element.textContent || '')
        if (text.length < 20 || text.length > 800) continue

        if (element.querySelector('p, li, td, th, h1, h2, h3, h4, h5, h6, blockquote, pre, section, article')) {
            continue
        }

        const tokenSet = new Set(text.split(/[^a-z0-9]+/i).filter(Boolean))
        const hitCount = referenceTokens.filter((token) => tokenSet.has(token) || text.includes(token)).length
        const phraseBonus = phrases.some((phrase) => phrase.length >= 24 && text.includes(phrase)) ? 10 : 0
        const score = (hitCount * 5) + phraseBonus

        if (score > 0 && (!best || score > best.score)) {
            best = { element, score }
        }
    }

    return best?.element || null
}

function getDatasetNumber(element: HTMLElement, key: string): number | null {
    const value = element.dataset[key]
    if (value === undefined) return null
    const parsed = Number(value)
    return Number.isFinite(parsed) ? parsed : null
}

function findMetadataAnchor(
    root: HTMLElement,
    citationTarget?: WordViewerProps['citationTarget'],
): HTMLElement | null {
    if (!citationTarget) return null

    if (typeof citationTarget.startChar === 'number' || typeof citationTarget.endChar === 'number') {
        const targetStart = citationTarget.startChar ?? citationTarget.endChar ?? 0
        const targetEnd = citationTarget.endChar ?? citationTarget.startChar ?? targetStart
        const candidates = Array.from(root.querySelectorAll('[data-docx-char-start][data-docx-char-end]')) as HTMLElement[]
        let best: { element: HTMLElement; score: number; distance: number } | null = null

        for (const element of candidates) {
            const start = getDatasetNumber(element, 'docxCharStart')
            const end = getDatasetNumber(element, 'docxCharEnd')
            if (start === null || end === null) continue

            const overlap = Math.max(0, Math.min(end, targetEnd) - Math.max(start, targetStart))
            const contains = start <= targetStart && end >= targetStart ? 8 : 0
            const distance = Math.min(Math.abs(start - targetStart), Math.abs(end - targetStart))
            const score = overlap + contains - Math.min(distance / 1000, 4)

            if (!best || score > best.score || (score === best.score && distance < best.distance)) {
                best = { element, score, distance }
            }
        }

        if (best && (best.score > 0 || best.distance < 600)) {
            return best.element
        }
    }

    if (typeof citationTarget.lineStart === 'number') {
        const blockIndex = Math.max(0, citationTarget.lineStart - 1)
        const byLine = root.querySelector(`[data-docx-block-index="${blockIndex}"], [data-docx-paragraph-index="${blockIndex}"]`) as HTMLElement | null
        if (byLine) return byLine
    }

    return null
}

function highlightPreviewHtml(html: string, searchText?: string, chunkText?: string, answerContext?: string): string {
    if (typeof window === 'undefined') return html

    const referenceText = answerContext || searchText || chunkText || ''
    const phrases = getSearchPhrases(referenceText)
    if (phrases.length === 0) return html

    const parser = new DOMParser()
    const document = parser.parseFromString(`<div>${html}</div>`, 'text/html')
    const root = document.body.firstElementChild
    if (!root) return html

    const textNodes: Text[] = []
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
        acceptNode(node) {
            const parentName = node.parentElement?.tagName.toLowerCase()
            if (!node.nodeValue?.trim() || parentName === 'style' || parentName === 'script' || parentName === 'mark') {
                return NodeFilter.FILTER_REJECT
            }
            return NodeFilter.FILTER_ACCEPT
        },
    })

    let currentNode = walker.nextNode()
    while (currentNode) {
        textNodes.push(currentNode as Text)
        currentNode = walker.nextNode()
    }

    textNodes.forEach((node) => {
        const text = node.nodeValue || ''
        const normalizedNode = normalizeTextWithMap(text)
        const matches: { start: number; end: number }[] = []

        phrases.forEach((phrase) => {
            const needle = normalizeText(phrase)
            let index = normalizedNode.normalized.indexOf(needle)
            while (index !== -1) {
                const originalStart = normalizedNode.map[index] ?? 0
                const originalEnd = (normalizedNode.map[index + needle.length - 1] ?? originalStart) + 1
                matches.push({ start: originalStart, end: originalEnd })
                index = normalizedNode.normalized.indexOf(needle, index + Math.max(needle.length, 1))
            }
        })

        if (matches.length === 0) return

        const merged = matches
            .sort((a, b) => a.start - b.start || b.end - a.end)
            .reduce<{ start: number; end: number }[]>((items, match) => {
                const previous = items[items.length - 1]
                if (previous && match.start <= previous.end) {
                    previous.end = Math.max(previous.end, match.end)
                    return items
                }
                items.push({ ...match })
                return items
            }, [])

        const fragment = document.createDocumentFragment()
        let cursor = 0
        merged.forEach((match) => {
            if (match.start > cursor) {
                fragment.appendChild(document.createTextNode(text.slice(cursor, match.start)))
            }
            const mark = document.createElement('mark')
            mark.className = 'citation-preview-highlight'
            mark.textContent = text.slice(match.start, match.end)
            fragment.appendChild(mark)
            cursor = match.end
        })

        if (cursor < text.length) {
            fragment.appendChild(document.createTextNode(text.slice(cursor)))
        }

        node.parentNode?.replaceChild(fragment, node)
    })

    if (!root.querySelector('.citation-preview-highlight')) {
        const bestBlock = findBestPreviewBlock(root as HTMLElement, referenceText)
        if (bestBlock) {
            bestBlock.classList.add('citation-preview-block-highlight')
        }
    }

    return root.innerHTML
}

export function WordViewer({ fileUrl, searchText, chunkText, answerContext, assetImage, citationTarget, onLoadSuccess, onLoadError, onScrollStatsChange }: WordViewerProps) {
    const [htmlContent, setHtmlContent] = useState<string>('')
    const [isLoading, setIsLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [progress, setProgress] = useState<string>('Initializing...')
    const containerRef = useRef<HTMLDivElement | null>(null)
    const onLoadSuccessRef = useRef(onLoadSuccess)
    const onLoadErrorRef = useRef(onLoadError)
    const onScrollStatsChangeRef = useRef(onScrollStatsChange)

    useEffect(() => {
        onLoadSuccessRef.current = onLoadSuccess
    }, [onLoadSuccess])

    useEffect(() => {
        onLoadErrorRef.current = onLoadError
    }, [onLoadError])

    useEffect(() => {
        onScrollStatsChangeRef.current = onScrollStatsChange
    }, [onScrollStatsChange])

    useEffect(() => {
        let cancelled = false

        const loadWord = async () => {
            setIsLoading(true)
            setError(null)
            setProgress('Tải preview...')
            try {
                logger.debug('Loading Word preview from', { fileUrl })
                setProgress('Fetching preview HTML...')

                const response = await api.get<any>(fileUrl)
                if (cancelled) return

                const htmlBody = response?.data?.html ?? response?.html ?? response?.data
                if (typeof htmlBody !== 'string' || !htmlBody.trim()) {
                    throw new Error('Invalid preview response')
                }

                const inlineStyles = `
                    <style>
                        .docx-preview { width: 100%; color: #0f172a; font-size: 14px; line-height: 1.7; }
                        .docx-preview table { width: 100%; border-collapse: collapse; margin-bottom: 1rem; }
                        .docx-preview th,
                        .docx-preview td { border: 1px solid #d1d5db; padding: 0.55rem; vertical-align: top; }
                        .docx-preview p { margin: 0 0 1rem; }
                        .docx-preview h1,
                        .docx-preview h2,
                        .docx-preview h3,
                        .docx-preview h4 { margin: 1rem 0 0.75rem; }
                        .docx-preview ul,
                        .docx-preview ol { margin: 0 0 1rem 1.5rem; }
                        .docx-preview img { max-width: 100%; height: auto; }
                        .docx-preview blockquote { margin: 0 0 1rem; padding-left: 1rem; border-left: 3px solid #cbd5e1; color: #475569; }
                        .docx-preview .citation-preview-highlight { background: #fde68a; color: inherit; border-radius: 4px; padding: 0 2px; box-shadow: 0 0 0 1px rgba(245, 158, 11, 0.16); }
                        .docx-preview .citation-preview-block-highlight { background: #fef3c7; outline: 2px solid rgba(245, 158, 11, 0.25); outline-offset: 4px; border-radius: 8px; }
                        .docx-preview .citation-preview-anchor-highlight { background: #fef3c7; outline: 3px solid rgba(245, 158, 11, 0.34); outline-offset: 4px; border-radius: 8px; }
                        .docx-preview .citation-asset-image-highlight { outline: 4px solid rgb(34 211 238); outline-offset: 6px; border-radius: 8px; box-shadow: 0 0 0 8px rgba(34, 211, 238, 0.16); }
                    </style>
                `

                const highlighted = highlightPreviewHtml(htmlBody, searchText, chunkText, answerContext)

                // Sanitize highlighted HTML to prevent XSS while allowing our injected <mark> highlights and classes
                const safe = DOMPurify.sanitize(highlighted, {
                    ADD_TAGS: ['mark'],
                    ADD_ATTR: ['class'],
                    FORBID_TAGS: ['script', 'style', 'iframe'],
                    FORBID_ATTR: ['onerror', 'onload', 'onclick', 'onmouseover', 'onfocus'],
                    ALLOWED_URI_REGEXP: /^(?:(?:https?|mailto|ftp):|[^a-z]|[a-z+.-]+:)/i,
                })

                setHtmlContent(inlineStyles + safe)
                setProgress('Done')
                onLoadSuccessRef.current()
            } catch (err) {
                const error = err instanceof Error ? err : new Error(String(err))
                logger.error('Word loading error', error)
                setError(`Error: ${error.message}`)
                onLoadErrorRef.current(error)
            } finally {
                if (!cancelled) {
                    setIsLoading(false)
                }
            }
        }

        if (fileUrl) {
            loadWord()
        }

        return () => {
            cancelled = true
        }
    }, [fileUrl, searchText, chunkText, answerContext])

    useEffect(() => {
        const container = containerRef.current
        if (!container || isLoading || error || !htmlContent) return

        const metadataTarget = findMetadataAnchor(container, citationTarget)
        const firstHighlight = container.querySelector('.citation-preview-highlight, .citation-preview-block-highlight') as HTMLElement | null
        const assetTarget = (() => {
            if (!assetImage) return null
            const imageIndex = typeof assetImage.imageIndex === 'number'
                ? assetImage.imageIndex
                : typeof assetImage.position?.image_index === 'number'
                    ? assetImage.position.image_index
                    : undefined
            if (typeof imageIndex === 'number') {
                const indexed = container.querySelector(`[data-docx-image-index="${imageIndex}"]`) as HTMLElement | null
                if (indexed) return indexed
                const images = Array.from(container.querySelectorAll('.docx-preview img')) as HTMLElement[]
                if (images[imageIndex]) return images[imageIndex]
            }
            if (typeof assetImage.paragraphIndex !== 'number') return null
            const indexed = container.querySelector(`[data-docx-paragraph-index="${assetImage.paragraphIndex}"] img`) as HTMLElement | null
            if (indexed) return indexed
            return null
        })()

        if (assetTarget) {
            assetTarget.classList.add('citation-asset-image-highlight')
            window.setTimeout(() => {
                assetTarget.scrollIntoView({ block: 'center', behavior: 'smooth' })
            }, 100)
        } else if (metadataTarget) {
            metadataTarget.classList.add('citation-preview-anchor-highlight')
            window.setTimeout(() => {
                metadataTarget.scrollIntoView({ block: 'center', behavior: 'smooth' })
            }, 100)
        } else if (firstHighlight) {
            window.setTimeout(() => {
                firstHighlight.scrollIntoView({ block: 'center', behavior: 'smooth' })
            }, 100)
        }

        const updateStats = () => {
            const containerTop = container.getBoundingClientRect().top
            const threshold = containerTop + 140
            const pageHeight = Math.max(container.clientHeight, 1)
            const totalPages = Math.max(1, Math.ceil(container.scrollHeight / pageHeight))
            const currentPage = Math.min(totalPages, Math.max(1, Math.floor((container.scrollTop + threshold - containerTop) / pageHeight) + 1))
            onScrollStatsChangeRef.current?.(currentPage, totalPages)
        }

        updateStats()
        container.addEventListener('scroll', updateStats, { passive: true })
        window.addEventListener('resize', updateStats)

        return () => {
            container.removeEventListener('scroll', updateStats)
            window.removeEventListener('resize', updateStats)
        }
    }, [htmlContent, isLoading, error, assetImage, citationTarget])

    if (isLoading) {
        return (
            <div className="flex flex-col items-center justify-center gap-4 h-full">
                <div className="w-12 h-12 rounded-full border-4 border-slate-300 border-t-slate-600 animate-spin"></div>
                <p className="text-slate-400 text-sm">Đang xử lý file...</p>
                <p className="text-slate-500 text-xs">{progress}</p>
            </div>
        )
    }

    if (error) {
        return (
            <div className="flex flex-col items-center justify-center gap-3 h-full p-6">
                <span className="material-symbols-outlined text-5xl text-red-400">error</span>
                <p className="text-red-400 text-sm text-center">{error}</p>
            </div>
        )
    }

    return (
        <div ref={containerRef} className="w-full h-full overflow-auto bg-slate-100 p-6">
            <div className="max-w-full mx-auto mb-4 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-xs text-slate-600">
                Xem trước Word hiển thị theo luồng nội dung gốc. Nếu cần đúng tuyệt đối, hãy tải xuống file gốc.
            </div>
            <div className="max-w-full mx-auto text-slate-900 font-serif leading-relaxed" style={{ fontSize: '14px' }}>
                <div className="mb-4 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-xs text-slate-600">
                    Xem trước có thể không giữ được 100% định dạng gốc. Nếu cần chính xác, hãy tải xuống file gốc.
                </div>
                <div
                    className="docx-preview bg-white rounded-lg p-6 text-slate-900"
                    style={{ lineHeight: '1.7' }}
                    dangerouslySetInnerHTML={{ __html: htmlContent }}
                />
            </div>
        </div>
    )
}
