'use client'

import React, { useState, useEffect, useRef } from 'react'
import { Document, Page, pdfjs } from 'react-pdf'
import 'react-pdf/dist/Page/TextLayer.css'
import 'react-pdf/dist/Page/AnnotationLayer.css'

interface PDFViewerProps {
    fileUrl: string
    onLoadSuccess: (numPages: number) => void
    onLoadError: (error: Error) => void
    onPageChange?: (page: number) => void
}

// Initialize PDF worker
const initWorker = () => {
    if (typeof window !== 'undefined') {
        // Use the worker bundled with pdfjs-dist so Next doesn't need a public asset.
        pdfjs.GlobalWorkerOptions.workerSrc = new URL('pdfjs-dist/build/pdf.worker.min.mjs', import.meta.url).toString()
    }
}

initWorker()

export function PDFViewer({ fileUrl, onLoadSuccess, onLoadError, onPageChange }: PDFViewerProps) {
    const [containerWidth, setContainerWidth] = useState<number>(0)
    const [numPages, setNumPages] = useState<number>(0)
    const [currentPage, setCurrentPage] = useState<number>(1)
    const containerRef = useRef<HTMLDivElement | null>(null)
    const pageRefs = useRef<Array<HTMLDivElement | null>>([])
    const onPageChangeRef = useRef<PDFViewerProps['onPageChange']>(onPageChange)
    const currentPageRef = useRef<number>(1)

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

    const handleSuccess = ({ numPages }: { numPages: number }) => {
        console.log('PDF loaded, pages:', numPages)
        setNumPages(numPages)
        setCurrentPage(1)
        currentPageRef.current = 1
        onPageChangeRef.current?.(1)
        onLoadSuccess(numPages)
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
                                onLoadSuccess={() => console.log(`Page ${pageNumber} loaded`)}
                                onLoadError={(error) => console.error(`Page ${pageNumber} error:`, error)}
                            />
                        </div>
                    ))}
                </div>
            </Document>
        </div>
    )
}
