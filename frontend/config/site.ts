// config/site.ts - Site configuration
export const siteConfig = {
    name: 'RAG System',
    description: 'Retrieval-Augmented Generation System',
    url: process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000',
    apiUrl: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1',
    links: {
        github: 'https://github.com',
        docs: 'https://docs.example.com',
    },
}
