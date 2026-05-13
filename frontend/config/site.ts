// config/site.ts - Site configuration
import { getApiBaseUrl } from './api'

export const siteConfig = {
    name: 'RAG System',
    description: 'Retrieval-Augmented Generation System',
    url: process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000',
    apiUrl: getApiBaseUrl(),
    links: {
        github: 'https://github.com',
        docs: 'https://docs.example.com',
    },
}
