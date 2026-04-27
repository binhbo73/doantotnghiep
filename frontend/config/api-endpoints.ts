/**
 * API Endpoints Configuration
 * Centralized definition of all API endpoints
 */

import { env } from './environment'

const BASE_URL = env.apiUrl

export const API_ENDPOINTS = Object.freeze({
    // Auth Endpoints
    AUTH: {
        LOGIN: '/auth/login/',
        LOGOUT: '/auth/logout/',
        REFRESH: '/auth/refresh/',
        ME: '/auth/me/',
    },

    // Chat Endpoints - RAG System
    CHAT: {
        // Conversations
        CONVERSATIONS: `${BASE_URL}/chat/conversations`,
        CONVERSATION_DETAIL: (id: string) => `${BASE_URL}/chat/conversations/${id}`,
        CONVERSATION_MESSAGES: (id: string) => `${BASE_URL}/chat/conversations/${id}/messages`,

        // Messages
        MESSAGES: `${BASE_URL}/chat/messages`,
        MESSAGE_DETAIL: (id: string) => `${BASE_URL}/chat/messages/${id}`,
        MESSAGE_FEEDBACK: (id: string) => `${BASE_URL}/chat/messages/${id}/feedback`,
    },

    // Document Endpoints
    DOCUMENTS: {
        LIST: `${BASE_URL}/documents`,
        DETAIL: (id: string) => `${BASE_URL}/documents/${id}`,
        UPLOAD: `${BASE_URL}/documents/upload`,
        DELETE: (id: string) => `${BASE_URL}/documents/${id}`,
        SEARCH: `${BASE_URL}/documents/search`,
    },

    // User Endpoints
    USERS: {
        PROFILE: `${BASE_URL}/users/profile`,
        UPDATE_PROFILE: `${BASE_URL}/users/profile/update`,
        AVATAR: `${BASE_URL}/users/avatar`,
    },

    // Department Endpoints
    DEPARTMENTS: {
        LIST: `${BASE_URL}/departments`,
        DETAIL: (id: string) => `${BASE_URL}/departments/${id}`,
    },

    // Role Endpoints
    ROLES: {
        LIST: `${BASE_URL}/roles`,
        DETAIL: (id: string) => `${BASE_URL}/roles/${id}`,
    },
})
