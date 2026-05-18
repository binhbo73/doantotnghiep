'use client'

import React, { useEffect, useRef, useState } from 'react'
import { Document, Page, pdfjs } from 'react-pdf'
import 'react-pdf/dist/Page/TextLayer.css'
import 'react-pdf/dist/Page/AnnotationLayer.css'

type PDFDocumentProxy = any

interface PDFViewerProps {
    fileUrl: string
    onLoadSuccess: (numPages: number) => void
    onLoadError: (error: Error) => void
    onPageChange?: (page: number) => void
    initialPage?: number
    searchText?: string
    chunkText?: string
    answerContext?: string
    citationTarget?: CitationTarget
    assetImage?: AssetImageHint
}

type CitationTarget = {
    documentId?: string
    chunkId?: string
    page?: number
    chunkIndex?: number
    startChar?: number
    endChar?: number
    lineStart?: number
    lineEnd?: number
}

type AssetImageHint = {
    id?: string
    pageNumber?: number
    position?: Record<string, unknown>
    imageEndpoint?: string
    caption?: string
    contextText?: string
}

type MatchSource = 'answer_context' | 'citation_chunk'

type PdfMatch = {
    pageNumber: number
    matches: string[]
    score: number
    source?: MatchSource
    itemStart?: number
    itemEnd?: number
}

type ItemRange = {
    start: number
    end: number
}

const initWorker = () => {
    if (typeof window !== 'undefined') {
        pdfjs.GlobalWorkerOptions.workerSrc = new URL('pdfjs-dist/build/pdf.worker.min.mjs', import.meta.url).toString()
    }
}

initWorker()

const normalizeText = (value: string) =>
    value
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .replace(/\u0111/g, 'd')
        .replace(/\u0110/g, 'd')
        .toLowerCase()

const SEARCH_STOPWORDS = new Set([
    'nguon', 'source', 'trang', 'chunk', 'dong', 'cua', 'cho', 'va', 'cac', 'nhung',
    'trong', 'voi', 'duoc', 'khong', 'co', 'la', 'de', 'mot', 'nay', 'do', 'da',
    'se', 'khi', 'chi', 'thi', 'ra', 'vao', 'nhu', 'nen', 'qua', 'rat', 'hay',
    'con', 'the', 'this', 'that', 'from', 'with', 'your', 'have', 'are', 'nguoi',
    'viec', 'tai', 'sau', 'tren', 'can', 'phai', 'theo', 'dia', 'ty',
])

const stripCitationMarkup = (text?: string) =>
    (text || '')
        .replace(/\[(?:Ngu[^\]:]*|Source):[^\]]+\]\s*\[\d{1,3}\]/gi, ' ')
        .replace(/\[\d{1,3}\]/g, ' ')
        .replace(/\s+/g, ' ')
        .trim()

const getReferenceTokens = (text?: string) => {
    const words = normalizeText(stripCitationMarkup(text))
        .split(/[^a-z0-9]+/i)
        .filter((word) => {
            if (!word) return false
            if (/^\d+$/.test(word)) return true
            return word.length >= 3 && !SEARCH_STOPWORDS.has(word)
        })

    return Array.from(new Set(words))
}

const getNumber = (value: unknown): number | undefined => {
    return typeof value === 'number' && Number.isFinite(value) ? value : undefined
}

const getAssetPdfBoxStyle = (assetImage: AssetImageHint | undefined, pageNumber: number): React.CSSProperties | undefined => {
    if (!assetImage || assetImage.pageNumber !== pageNumber) return undefined

    const position = assetImage.position || {}
    const bbox = position.pdf_bbox
    if (!Array.isArray(bbox) || bbox.length < 4) return undefined

    const [x0, y0, x1, y1] = bbox.map(getNumber)
    const pageWidth = getNumber(position.pdf_page_width)
    const pageHeight = getNumber(position.pdf_page_height)
    if (
        x0 === undefined ||
        y0 === undefined ||
        x1 === undefined ||
        y1 === undefined ||
        !pageWidth ||
        !pageHeight ||
        x1 <= x0 ||
        y1 <= y0
    ) {
        return undefined
    }

    return {
        left: `${(x0 / pageWidth) * 100}%`,
        top: `${(y0 / pageHeight) * 100}%`,
        width: `${((x1 - x0) / pageWidth) * 100}%`,
        height: `${((y1 - y0) / pageHeight) * 100}%`,
    }
}

const getSearchPhrases = (text?: string) => {
    if (!text) return []

    const rawPhrases = stripCitationMarkup(text)
        .split(/\n+/)
        .map((line) => line.replace(/^[-+*\u2022\d]+[.)]?\s*/, '').trim())
        .flatMap((line) => {
            const sentenceParts = line.split(/[.!?\u2026]\s+/)
            return sentenceParts.flatMap((sentence) => {
                const commaParts = sentence.split(/[,;]\s+/).filter((part) => part.trim().length >= 24)
                return [sentence, ...commaParts]
            })
        })
        .map((line) => line.trim())
        .filter((line) => line.length >= 16)

    return Array.from(new Set(rawPhrases))
        .sort((a, b) => b.length - a.length)
        .slice(0, 8)
}

const getTextLayerSpans = (pageEl: HTMLElement) =>
    Array.from(
        pageEl.querySelectorAll([
            '.react-pdf__Page__textContent span',
            '.react-pdf__Page__textContent > span',
            '.textLayer span',
            '[data-text-layer] span',
            '.react-pdf__Page canvas + div span',
        ].join(', '))
    ) as HTMLElement[]

const clearSpanHighlight = (span: HTMLElement) => {
    span.classList.remove('citation-pdf-highlight')
    span.style.backgroundColor = ''
    span.style.color = ''
    span.style.borderRadius = ''
    span.style.boxShadow = ''
}

const getVisualSpanItems = (spans: HTMLElement[]) =>
    spans
        .map((span) => ({
            span,
            text: span.textContent || '',
            rect: span.getBoundingClientRect(),
        }))
        .filter((item) => item.text.trim())
        .sort((a, b) => {
            const topDelta = a.rect.top - b.rect.top
            if (Math.abs(topDelta) > 3) return topDelta
            return a.rect.left - b.rect.left
        })

const findBestWindowInTexts = (
    normalizedTexts: string[],
    referenceText: string,
    source: MatchSource,
    itemRange?: ItemRange,
): (ItemRange & { score: number }) | null => {
    const referenceTokens = getReferenceTokens(referenceText)
    const phrases = getSearchPhrases(referenceText).map((phrase) => normalizeText(phrase))
    if (!referenceTokens.length && !phrases.length) return null

    const rangeStart = itemRange ? Math.max(0, itemRange.start) : 0
    const rangeEnd = itemRange ? Math.min(normalizedTexts.length - 1, itemRange.end) : normalizedTexts.length - 1
    if (rangeStart > rangeEnd) return null

    const searchableText = normalizedTexts.slice(rangeStart, rangeEnd + 1).join(' ')
    const textTokenSet = new Set(searchableText.split(/[^a-z0-9]+/i).filter(Boolean))
    const pageHits = referenceTokens.filter((token) => textTokenSet.has(token) || searchableText.includes(token))
    const strongestPhraseHit = phrases.some((phrase) => phrase.length >= 24 && searchableText.includes(phrase))
    const minHits = Math.min(4, Math.max(2, Math.ceil(referenceTokens.length * 0.35)))
    if (!strongestPhraseHit && pageHits.length < minHits) return null

    let bestWindow = { start: -1, end: -1, score: 0, hits: 0 }
    const maxWindow = source === 'answer_context' ? 18 : 42

    for (let start = rangeStart; start <= rangeEnd; start += 1) {
        let combined = ''
        for (let end = start; end <= Math.min(rangeEnd, start + maxWindow - 1); end += 1) {
            combined = `${combined} ${normalizedTexts[end]}`.trim()
            if (combined.length < 8) continue

            const combinedTokenSet = new Set(combined.split(/[^a-z0-9]+/i).filter(Boolean))
            const hitCount = referenceTokens.filter((token) => combinedTokenSet.has(token) || combined.includes(token)).length
            const windowCoverage = referenceTokens.length ? hitCount / referenceTokens.length : 0
            const phraseBonus = phrases.some((phrase) => phrase.length >= 24 && combined.includes(phrase)) ? 20 : 0
            const score = (hitCount * 6) + (windowCoverage * 20) + phraseBonus

            if (score > bestWindow.score) {
                bestWindow = { start, end, score, hits: hitCount }
            }
        }
    }

    if (bestWindow.start < 0 || (!strongestPhraseHit && bestWindow.hits < minHits)) return null
    return bestWindow
}

export function PDFViewer({
    fileUrl,
    onLoadSuccess,
    onLoadError,
    onPageChange,
    initialPage,
    searchText,
    chunkText,
    answerContext,
    citationTarget,
    assetImage,
}: PDFViewerProps) {
    const [containerWidth, setContainerWidth] = useState<number>(0)
    const [numPages, setNumPages] = useState<number>(0)
    const [currentPage, setCurrentPage] = useState<number>(1)
    const containerRef = useRef<HTMLDivElement | null>(null)
    const pageRefs = useRef<Array<HTMLDivElement | null>>([])
    const onPageChangeRef = useRef<PDFViewerProps['onPageChange']>(onPageChange)
    const currentPageRef = useRef<number>(1)
    const didInitialScrollRef = useRef(false)
    const pdfRef = useRef<PDFDocumentProxy | null>(null)
    const matchedTextRef = useRef<string[]>([])
    const matchedPageRef = useRef<number | null>(null)
    const matchedRangeRef = useRef<{ start: number; end: number } | null>(null)
    const lastAnchorKeyRef = useRef<string>('')

    useEffect(() => {
        didInitialScrollRef.current = false
        matchedTextRef.current = []
        matchedPageRef.current = null
        matchedRangeRef.current = null
        lastAnchorKeyRef.current = ''
    }, [fileUrl])

    useEffect(() => {
        if (!containerRef.current) return

        const updateWidth = () => {
            setContainerWidth(containerRef.current?.clientWidth ?? 0)
        }

        updateWidth()

        const observer = new ResizeObserver(() => updateWidth())
        observer.observe(containerRef.current)

        return () => observer.disconnect()
    }, [])

    useEffect(() => {
        onPageChangeRef.current = onPageChange
    }, [onPageChange])

    useEffect(() => {
        currentPageRef.current = currentPage
    }, [currentPage])

    const adjustedWidth = Math.max(0, Math.min(containerWidth - 24, 900))

    const scrollContainerToElement = (element: Element, block: 'start' | 'center' = 'start', behavior: ScrollBehavior = 'auto') => {
        const container = containerRef.current
        if (!container) {
            element.scrollIntoView({ block, behavior })
            return
        }

        const containerRect = container.getBoundingClientRect()
        const elementRect = element.getBoundingClientRect()
        const elementTop = elementRect.top - containerRect.top + container.scrollTop
        const targetTop = block === 'center'
            ? elementTop - (container.clientHeight / 2) + (elementRect.height / 2)
            : elementTop - 16

        container.scrollTo({
            top: Math.max(0, targetTop),
            behavior,
        })
    }

    async function anchorCitationInPdf(pdf: PDFDocumentProxy, pageCount: number) {
        const assetPage = assetImage?.pageNumber && assetImage.pageNumber > 0 ? assetImage.pageNumber : undefined
        const startPage = assetPage ? Math.min(assetPage, pageCount) : initialPage && initialPage > 0 ? Math.min(initialPage, pageCount) : 1
        const anchorKey = [
            fileUrl,
            startPage,
            citationTarget?.chunkId || '',
            citationTarget?.page || '',
            assetImage?.id || '',
            assetImage?.pageNumber || '',
            chunkText || '',
            searchText || '',
            answerContext || '',
        ].join('|')

        if (lastAnchorKeyRef.current === anchorKey) return
        lastAnchorKeyRef.current = anchorKey

        if (assetImage?.pageNumber) {
            const assetPageEl = pageRefs.current[Math.max(0, startPage - 1)]
            if (assetPageEl) {
                assetPageEl.classList.add('citation-pdf-asset-page-highlight')
                const scrollToAsset = (attempt = 0) => {
                    const assetHighlight = assetPageEl.querySelector('.citation-pdf-asset-highlight')
                    if (!assetHighlight && attempt < 16) {
                        window.setTimeout(() => scrollToAsset(attempt + 1), 250)
                        return
                    }
                    scrollContainerToElement(assetHighlight || assetPageEl, 'center', 'smooth')
                }
                window.setTimeout(() => scrollToAsset(), 250)
            }
            return
        }

        if (!(searchText || answerContext || citationTarget?.page)) return

        const match = await findBestPdfMatch(pdf, startPage, searchText || '', answerContext || '', chunkText || '', citationTarget)
        matchedTextRef.current = match.matches
        matchedPageRef.current = match.score > 0 ? match.pageNumber : null
        matchedRangeRef.current = (
            match.score > 0 &&
            typeof match.itemStart === 'number' &&
            typeof match.itemEnd === 'number'
        ) ? { start: match.itemStart, end: match.itemEnd } : null

        if (match.pageNumber && match.score > 0 && match.pageNumber !== startPage) {
            setCurrentPage(match.pageNumber)
            currentPageRef.current = match.pageNumber
            onPageChangeRef.current?.(match.pageNumber)
        }

        if (match.score <= 0) {
            const fallbackPage = match.pageNumber || citationTarget?.page || startPage
            const initialPageEl = pageRefs.current[Math.max(0, fallbackPage - 1)]
            if (initialPageEl) {
                if (assetImage?.pageNumber) {
                    initialPageEl.classList.add('citation-pdf-asset-page-highlight')
                }
                window.setTimeout(() => scrollContainerToElement(initialPageEl, 'start'), 250)
            }
            return
        }

        const bestPage = match.pageNumber

        const highlightMatchedPage = (pollAttempt = 0) => {
            if (pollAttempt >= 20) return

            const bestPageEl = pageRefs.current[bestPage - 1]
            if (!bestPageEl) {
                window.setTimeout(() => highlightMatchedPage(pollAttempt + 1), 250)
                return
            }

            pageRefs.current.forEach((pageEl) => {
                if (!pageEl) return
                getTextLayerSpans(pageEl).forEach(clearSpanHighlight)
            })

            const spans = getTextLayerSpans(bestPageEl)
            if (!spans.length) {
                window.setTimeout(() => highlightMatchedPage(pollAttempt + 1), 500)
                return
            }

            const highlighted = applyHighlightsToSpans(spans, bestPage)
            if (!highlighted && pollAttempt < 20) {
                window.setTimeout(() => highlightMatchedPage(pollAttempt + 1), 500)
                return
            }

            window.setTimeout(() => {
                const firstHighlight = bestPageEl.querySelector('.citation-pdf-highlight')
                scrollContainerToElement(firstHighlight || bestPageEl, firstHighlight ? 'center' : 'start', 'smooth')
            }, 100)
        }

        window.setTimeout(() => highlightMatchedPage(0), 500)
    }

    const handleSuccess = async (pdf: PDFDocumentProxy) => {
        const { numPages } = pdf
        pdfRef.current = pdf
        setNumPages(numPages)
        const assetPage = assetImage?.pageNumber && assetImage.pageNumber > 0 ? assetImage.pageNumber : undefined
        const startPage = assetPage ? Math.min(assetPage, numPages) : initialPage && initialPage > 0 ? Math.min(initialPage, numPages) : 1
        setCurrentPage(startPage)
        currentPageRef.current = startPage
        onPageChangeRef.current?.(startPage)
        onLoadSuccess(numPages)

        await anchorCitationInPdf(pdf, numPages)
    }

    const handleError = (error: Error) => {
        console.error('PDF Error:', error)
        onLoadError(error)
    }

    useEffect(() => {
        const container = containerRef.current
        if (!container || numPages === 0) return

        const updateCurrentPage = () => {
            const containerTop = container.getBoundingClientRect().top
            const threshold = containerTop + 120

            let activePage = 1

            for (let index = 0; index < pageRefs.current.length; index += 1) {
                const pageElement = pageRefs.current[index]
                if (!pageElement) continue

                const rect = pageElement.getBoundingClientRect()
                if (rect.top <= threshold) {
                    activePage = index + 1
                } else {
                    break
                }
            }

            if (activePage !== currentPageRef.current) {
                currentPageRef.current = activePage
                setCurrentPage(activePage)
                onPageChangeRef.current?.(activePage)
            }
        }

        updateCurrentPage()
        container.addEventListener('scroll', updateCurrentPage, { passive: true })
        window.addEventListener('resize', updateCurrentPage)

        return () => {
            container.removeEventListener('scroll', updateCurrentPage)
            window.removeEventListener('resize', updateCurrentPage)
        }
    }, [numPages])

    useEffect(() => {
        const container = containerRef.current
        if (!container || !numPages || didInitialScrollRef.current || matchedPageRef.current) return

        const page = initialPage && initialPage > 0 ? Math.min(initialPage, numPages) : 1
        const pageElement = pageRefs.current[page - 1]
        if (!pageElement) return

        didInitialScrollRef.current = true
        window.setTimeout(() => scrollContainerToElement(pageElement, 'start'), 250)
    }, [initialPage, numPages, searchText, chunkText, answerContext, citationTarget, assetImage])

    useEffect(() => {
        if (!pdfRef.current || !numPages) return
        void anchorCitationInPdf(pdfRef.current, numPages)
    }, [numPages, searchText, chunkText, answerContext, citationTarget, assetImage])

    async function getPdfPageMatch(
        pdf: PDFDocumentProxy,
        pageNumber: number,
        referenceText: string,
        source: MatchSource,
        itemRange?: ItemRange,
    ): Promise<PdfMatch> {
        try {
            const referenceTokens = getReferenceTokens(referenceText)
            const phrases = getSearchPhrases(referenceText).map((phrase) => normalizeText(phrase))
            if (!referenceTokens.length && !phrases.length) {
                return { pageNumber, matches: [], score: 0, source }
            }

            const page = await pdf.getPage(pageNumber)
            const textContent = await page.getTextContent()
            const items: string[] = textContent.items
                .map((item: { str?: unknown }) => String(item.str || '').trim())
                .filter(Boolean)

            if (!items.length) return { pageNumber, matches: [], score: 0, source }

            const normalizedItems = items.map((itemText: string) => normalizeText(itemText))
            const rangeStart = itemRange ? Math.max(0, itemRange.start) : 0
            const rangeEnd = itemRange ? Math.min(normalizedItems.length - 1, itemRange.end) : normalizedItems.length - 1
            const searchableItems = normalizedItems.slice(rangeStart, rangeEnd + 1)
            const normalizedSearchText = searchableItems.join(' ')
            const pageTokenSet = new Set(normalizedSearchText.split(/[^a-z0-9]+/i).filter(Boolean))
            const pageHits = referenceTokens.filter((token) => pageTokenSet.has(token) || normalizedSearchText.includes(token))
            const coverage = referenceTokens.length ? pageHits.length / referenceTokens.length : 0
            const strongestPhraseHit = phrases.some((phrase) => phrase.length >= 24 && normalizedSearchText.includes(phrase))

            const minHits = Math.min(4, Math.max(2, Math.ceil(referenceTokens.length * 0.35)))
            if (!strongestPhraseHit && pageHits.length < minHits) {
                return { pageNumber, matches: [], score: 0, source }
            }

            let bestWindow = { start: -1, end: -1, score: 0, hits: 0 }
            const maxWindow = source === 'answer_context' ? 18 : 42

            for (let start = rangeStart; start <= rangeEnd; start += 1) {
                let combined = ''
                for (let end = start; end <= Math.min(rangeEnd, start + maxWindow - 1); end += 1) {
                    combined = `${combined} ${normalizedItems[end]}`.trim()
                    if (combined.length < 8) continue

                    const combinedTokenSet = new Set(combined.split(/[^a-z0-9]+/i).filter(Boolean))
                    const hitCount = referenceTokens.filter((token) => combinedTokenSet.has(token) || combined.includes(token)).length
                    const windowCoverage = referenceTokens.length ? hitCount / referenceTokens.length : 0
                    const phraseBonus = phrases.some((phrase) => phrase.length >= 24 && combined.includes(phrase)) ? 20 : 0
                    const score = (hitCount * 6) + (windowCoverage * 20) + phraseBonus

                    if (score > bestWindow.score) {
                        bestWindow = { start, end, score, hits: hitCount }
                    }
                }
            }

            if (bestWindow.start < 0 || (!strongestPhraseHit && bestWindow.hits < minHits)) {
                return { pageNumber, matches: [], score: 0, source }
            }

            const matches = normalizedItems
                .slice(bestWindow.start, bestWindow.end + 1)
                .filter((item: string) => item.length >= 2)

            const sourceBonus = source === 'answer_context' ? 80 : 8
            const pageScore = bestWindow.score + (coverage * 50) + (strongestPhraseHit ? 30 : 0) + sourceBonus

            return {
                pageNumber,
                matches: Array.from(new Set<string>(matches)),
                score: pageScore,
                source,
                itemStart: bestWindow.start,
                itemEnd: bestWindow.end,
            }
        } catch (err) {
            console.warn('Failed to find PDF text matches:', err)
            return { pageNumber, matches: [], score: 0, source }
        }
    }

    async function findBestPdfMatch(
        pdf: PDFDocumentProxy,
        initialPageNumber: number,
        referenceText: string,
        contextText: string,
        chunkReferenceText: string,
        target?: CitationTarget,
    ): Promise<PdfMatch> {
        const targetPage = target?.page && target.page > 0 ? Math.min(target.page, pdf.numPages) : null
        const pagesToSearch = targetPage
            ? [targetPage]
            : Array.from({ length: pdf.numPages }, (_, index) => index + 1)

        let best: PdfMatch = { pageNumber: targetPage || initialPageNumber, matches: [], score: 0 }

        for (const pageNumber of pagesToSearch) {
            let chunkCandidate: PdfMatch | null = null
            if (chunkReferenceText) {
                chunkCandidate = await getPdfPageMatch(pdf, pageNumber, chunkReferenceText, 'citation_chunk')
            }

            const chunkRange = (
                chunkCandidate?.score &&
                typeof chunkCandidate.itemStart === 'number' &&
                typeof chunkCandidate.itemEnd === 'number'
            ) ? { start: chunkCandidate.itemStart, end: chunkCandidate.itemEnd } : undefined

            const references = [
                ...(referenceText ? [{ text: referenceText, source: 'citation_chunk' as const, bonus: 140 }] : []),
                ...(chunkReferenceText ? [{ text: chunkReferenceText, source: 'citation_chunk' as const, bonus: 80 }] : []),
                ...(contextText ? [{ text: contextText, source: 'answer_context' as const, bonus: 5 }] : []),
            ]

            for (const reference of references) {
                const candidate = await getPdfPageMatch(
                    pdf,
                    pageNumber,
                    reference.text,
                    reference.source,
                    chunkRange,
                )

                if (candidate.score > 0) {
                    const adjustedCandidate = {
                        ...candidate,
                        score: candidate.score + reference.bonus,
                    }
                    if (adjustedCandidate.score > best.score) {
                        best = adjustedCandidate
                    }
                }
            }

            if (best.score <= 0 && chunkCandidate && chunkCandidate.score > best.score) {
                best = chunkCandidate
            }

        }

        return best
    }

    function applyHighlightsToSpans(spans: HTMLElement[], pageNumber: number): number {
        const apiMatches = matchedTextRef.current
        if (!apiMatches.length || matchedPageRef.current !== pageNumber) return 0

        const visualSpanItems = getVisualSpanItems(spans)
        const normalizedSpanTexts = visualSpanItems.map((item) => normalizeText(item.text))
        const chunkRange = chunkText
            ? findBestWindowInTexts(normalizedSpanTexts, chunkText, 'citation_chunk')
            : null
        const sourceRange = searchText
            ? findBestWindowInTexts(normalizedSpanTexts, searchText, 'citation_chunk', chunkRange || undefined)
            : null
        const answerRange = answerContext
            ? findBestWindowInTexts(normalizedSpanTexts, answerContext, 'answer_context', sourceRange || chunkRange || undefined)
            : null
        const range = sourceRange || chunkRange || answerRange || matchedRangeRef.current
        if (range) {
            let highlightedCount = 0
            for (let index = range.start; index <= range.end && index < visualSpanItems.length; index += 1) {
                const span = visualSpanItems[index]?.span
                if (!span) continue
                highlightedCount += 1
                span.classList.add('citation-pdf-highlight')
                span.style.backgroundColor = 'rgba(253, 230, 138, 0.85)'
                span.style.color = 'rgb(15, 23, 42)'
                span.style.borderRadius = '2px'
                span.style.boxShadow = '0 0 0 2px rgba(253, 230, 138, 0.35)'
            }

            return highlightedCount
        }

        return 0
    }

    return (
        <div ref={containerRef} className="w-full h-full min-h-0 overflow-y-auto overflow-x-hidden">
            <Document
                file={fileUrl}
                onLoadSuccess={handleSuccess}
                onLoadError={handleError}
                loading={<p className="text-slate-500 text-center py-8">Dang tai PDF...</p>}
                error={<p className="text-red-500 text-center py-8">Loi tai PDF</p>}
            >
                <div className="flex flex-col gap-4 py-2 pb-14">
                    {Array.from({ length: numPages }, (_, index) => index + 1).map((pageNumber) => (
                        <div
                            key={pageNumber}
                            ref={(element) => {
                                pageRefs.current[pageNumber - 1] = element
                            }}
                            className="flex justify-center scroll-mt-6 rounded-md [&.citation-pdf-asset-page-highlight]:ring-4 [&.citation-pdf-asset-page-highlight]:ring-cyan-400 [&.citation-pdf-asset-page-highlight]:ring-offset-4 [&.citation-pdf-asset-page-highlight]:ring-offset-slate-100"
                        >
                            <div className="relative">
                                <Page
                                    pageNumber={pageNumber}
                                    width={adjustedWidth || undefined}
                                    className="shadow-sm"
                                    onLoadError={(error) => console.error(`Page ${pageNumber} error:`, error)}
                                />
                                {getAssetPdfBoxStyle(assetImage, pageNumber) && (
                                    <div
                                        className="citation-pdf-asset-highlight pointer-events-none absolute rounded-sm border-4 border-cyan-400 bg-cyan-300/20 shadow-[0_0_0_4px_rgba(255,255,255,0.9)]"
                                        style={getAssetPdfBoxStyle(assetImage, pageNumber)}
                                    />
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            </Document>
        </div>
    )
}
