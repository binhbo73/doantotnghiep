'use client'

import React, { useState, useEffect, useRef } from 'react'
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
}

// Initialize PDF worker
const initWorker = () => {
    if (typeof window !== 'undefined') {
        // Use the worker bundled with pdfjs-dist so Next doesn't need a public asset.
        pdfjs.GlobalWorkerOptions.workerSrc = new URL('pdfjs-dist/build/pdf.worker.min.mjs', import.meta.url).toString()
    }
}

initWorker()

const normalizeText = (value: string) =>
    value
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .replace(/đ/g, 'd')
        .replace(/Đ/g, 'd')
        .toLowerCase()

const getHighlightTerms = (text?: string) => {
    if (!text) return []
    const words = normalizeText(text)
        .split(/[^a-z0-9]+/i)
        .filter((word) => word.length >= 4)

    return Array.from(new Set(words)).slice(0, 18)
}

const getSearchPhrases = (text?: string) => {
    if (!text) return []

    const phrases = text
        .split(/\n+/)
        .map((line) => line.replace(/^[-+*•\s]+/, '').trim())
        .flatMap((line) => line.split(/(?<=[.!?])\s+/))
        .map((line) => line.trim())
        .filter((line) => line.length >= 24)

    return Array.from(new Set(phrases)).slice(0, 8)
}

export function PDFViewer({ fileUrl, onLoadSuccess, onLoadError, onPageChange, initialPage, searchText }: PDFViewerProps) {
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
    const highlightTerms = getHighlightTerms(searchText)
    const searchPhrases = getSearchPhrases(searchText)

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

    const handleSuccess = async (pdf: PDFDocumentProxy) => {
        const { numPages } = pdf
        pdfRef.current = pdf
        console.log('PDF loaded, pages:', numPages)
        setNumPages(numPages)
        const startPage = initialPage && initialPage > 0 ? Math.min(initialPage, numPages) : 1
        setCurrentPage(startPage)
        currentPageRef.current = startPage
        onPageChangeRef.current?.(startPage)
        onLoadSuccess(numPages)

        if (searchText) {
            const match = await findBestPdfMatch(pdf, startPage, searchText)
            matchedTextRef.current = match.matches
            if (match.pageNumber && match.pageNumber !== startPage) {
                setCurrentPage(match.pageNumber)
                currentPageRef.current = match.pageNumber
                onPageChangeRef.current?.(match.pageNumber)
                window.setTimeout(() => {
                    pageRefs.current[match.pageNumber - 1]?.scrollIntoView({ block: 'start' })
                }, 300)
            }
            window.setTimeout(() => applyTextLayerHighlights(match.pageNumber || startPage), 500)
        }
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
        if (!container || !numPages || didInitialScrollRef.current) return

        const page = initialPage && initialPage > 0 ? Math.min(initialPage, numPages) : 1
        const pageElement = pageRefs.current[page - 1]
        if (!pageElement) return

        didInitialScrollRef.current = true
        window.setTimeout(() => {
            pageElement.scrollIntoView({ block: 'start' })
            window.setTimeout(() => {
                const firstHighlight = pageElement.querySelector('.citation-pdf-highlight')
                if (firstHighlight) {
                    firstHighlight.scrollIntoView({ block: 'center' })
                }
            }, 900)
        }, 250)
    }, [initialPage, numPages, searchText])

    async function getPdfPageMatch(pdf: PDFDocumentProxy, pageNumber: number, referenceText: string) {
        try {
            const page = await pdf.getPage(pageNumber)
            const textContent = await page.getTextContent()
            const items = textContent.items
                .map((item: any) => String(item.str || '').trim())
                .filter(Boolean)

            if (!items.length) return { pageNumber, matches: [], score: 0 }

            const normalizedItems = items.map((itemText) => normalizeText(itemText))
            const findBestWindowForPhrase = (phrase: string) => {
                const normalizedPhrase = normalizeText(phrase)
                const phraseTerms = new Set(normalizedPhrase.split(/[^a-z0-9]+/i).filter((term) => term.length >= 4))
                let best = { start: -1, end: -1, score: 0 }

                for (let start = 0; start < normalizedItems.length; start += 1) {
                    let combined = ''
                    for (let end = start; end < Math.min(normalizedItems.length, start + 12); end += 1) {
                        combined = `${combined} ${normalizedItems[end]}`.trim()
                        if (combined.length < 8) continue

                        const combinedTerms = new Set(combined.split(/[^a-z0-9]+/i).filter((term) => term.length >= 4))
                        let termScore = 0
                        phraseTerms.forEach((term) => {
                            if (combinedTerms.has(term) || combined.includes(term)) termScore += 1
                        })

                        const containmentScore =
                            normalizedPhrase.includes(combined)
                                ? Math.min(10, Math.ceil(combined.length / 12))
                                : combined.includes(normalizedPhrase.slice(0, Math.min(48, normalizedPhrase.length)))
                                    ? 10
                                    : 0

                        const score = termScore + containmentScore
                        if (score > best.score) {
                            best = { start, end, score }
                        }
                    }
                }

                return best
            }

            const windows = searchPhrases
                .map(findBestWindowForPhrase)
                .filter((window) => window.score >= 3 && window.start >= 0)

            if (!windows.length) {
                return { pageNumber, matches: [], score: 0 }
            }

            const matchedIndexes = new Set<number>()
            let score = 0
            for (const window of windows) {
                score += window.score
                for (let index = window.start; index <= window.end; index += 1) {
                    matchedIndexes.add(index)
                }
            }

            const matches = Array.from(matchedIndexes)
                .sort((a, b) => a - b)
                .map((index) => normalizedItems[index])
                .filter((item) => item.length >= 2)

            return { pageNumber, matches: Array.from(new Set<string>(matches)), score }
        } catch (err) {
            console.warn('Failed to find PDF text matches:', err)
            return { pageNumber, matches: [], score: 0 }
        }
    }

    async function findBestPdfMatch(pdf: PDFDocumentProxy, initialPageNumber: number, referenceText: string) {
        const initial = await getPdfPageMatch(pdf, initialPageNumber, referenceText)
        if (initial.score > 0) return initial

        let best = initial
        for (let pageNumber = 1; pageNumber <= pdf.numPages; pageNumber += 1) {
            if (pageNumber === initialPageNumber) continue
            const candidate = await getPdfPageMatch(pdf, pageNumber, referenceText)
            if (candidate.score > best.score) {
                best = candidate
            }
        }

        return best
    }

    function applyTextLayerHighlights(pageNumber: number, attempt = 0) {
        if (!matchedTextRef.current.length) return

        window.setTimeout(() => {
            const pageElement = pageRefs.current[pageNumber - 1]
            if (!pageElement) return

            const spans = Array.from(
                pageElement.querySelectorAll('.react-pdf__Page__textContent span, .textLayer span')
            ) as HTMLElement[]

            if (!spans.length && attempt < 12) {
                applyTextLayerHighlights(pageNumber, attempt + 1)
                return
            }

            let highlightedCount = 0
            for (const span of spans) {
                const text = span.textContent || ''
                const normalized = normalizeText(text)
                const shouldHighlight = matchedTextRef.current.some((match) => normalized.includes(match) || match.includes(normalized))
                if (!shouldHighlight) continue

                highlightedCount += 1
                span.classList.add('citation-pdf-highlight')
                span.style.backgroundColor = 'rgba(253, 230, 138, 0.85)'
                span.style.color = 'rgb(15, 23, 42)'
                span.style.borderRadius = '2px'
                span.style.boxShadow = '0 0 0 2px rgba(253, 230, 138, 0.35)'
            }

            if (!highlightedCount && attempt < 12) {
                applyTextLayerHighlights(pageNumber, attempt + 1)
                return
            }

            if (pageNumber === (initialPage || 1)) {
                const firstHighlight = pageElement.querySelector('.citation-pdf-highlight')
                if (firstHighlight && didInitialScrollRef.current) {
                    window.setTimeout(() => firstHighlight.scrollIntoView({ block: 'center' }), 150)
                }
            }
        }, 250)
    }

    return (
        <div ref={containerRef} className="w-full h-full min-h-0 overflow-y-auto overflow-x-hidden">
            <Document
                file={fileUrl}
                onLoadSuccess={handleSuccess}
                onLoadError={handleError}
                loading={<p className="text-slate-500 text-center py-8">Đang tải PDF...</p>}
                error={<p className="text-red-500 text-center py-8">Lỗi tải PDF</p>}
            >
                <div className="flex flex-col gap-4 py-2 pb-14">
                    {Array.from({ length: numPages }, (_, index) => index + 1).map((pageNumber) => (
                        <div
                            key={pageNumber}
                            ref={(element) => {
                                pageRefs.current[pageNumber - 1] = element
                            }}
                            className="flex justify-center scroll-mt-6"
                        >
                            <Page
                                pageNumber={pageNumber}
                                width={adjustedWidth || undefined}
                                className="shadow-sm"
                                onLoadSuccess={() => {
                                    console.log(`Page ${pageNumber} loaded`)
                                    applyTextLayerHighlights(pageNumber)
                                }}
                                onLoadError={(error) => console.error(`Page ${pageNumber} error:`, error)}
                            />
                        </div>
                    ))}
                </div>
            </Document>
        </div>
    )
}
