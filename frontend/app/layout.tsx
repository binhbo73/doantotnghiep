import type { Metadata } from 'next'
import '../styles/globals.css'
import { Providers } from './providers'

export const metadata: Metadata = {
    title: 'RAG System',
    description: 'Retrieval-Augmented Generation System',
}

export default function RootLayout({
    children,
}: {
    children: React.ReactNode
}) {
    return (
        <html lang="en" className="light" suppressHydrationWarning>
            <body className="min-h-screen bg-[#f9f9ff] text-[#151c27] antialiased" suppressHydrationWarning>
                <Providers>
                    {children}
                </Providers>
            </body>
        </html>
    )
}
