// constants/api.ts - API endpoints
export const API_ENDPOINTS = {
    // Auth
    AUTH_LOGIN: '/auth/login',
    AUTH_LOGOUT: '/auth/logout',
    AUTH_REGISTER: '/auth/register',
    AUTH_REFRESH: '/auth/refresh',
    AUTH_CHANGE_PASSWORD: '/auth/change-password',

    // Users
    USERS: '/users',
    USER_PROFILE: '/users/profile',
    USER_PROFILE_AVATAR: '/users/profile/avatar',

    // Documents
    DOCUMENTS: '/documents',
    DOCUMENT_UPLOAD: '/documents/upload',
    DOCUMENT_DELETE: '/documents/:id',
    DOCUMENT_DETAIL: '/documents/:id',

    // Chat
    CHAT_CONVERSATIONS: '/chat/conversations',
    CHAT_MESSAGES: '/chat/messages',
    CHAT_SEND: '/chat/send',

    // Departments
    DEPARTMENTS: '/departments',

    // Folders
    FOLDERS: '/folders',
    FOLDER_CREATE: '/folders',
    FOLDER_DELETE: '/folders/:id',

    // Permissions
    PERMISSIONS: '/permissions',
    ROLES: '/roles',

    // Health
    HEALTH: '/health',
} as const

export const API_TIMEOUTS = {
    DEFAULT: 30000,      // 30 seconds
    UPLOAD: 120000,      // 2 minutes
    DOWNLOAD: 120000,
    SHORT: 10000,        // 10 seconds
} as const

export const HTTP_STATUS = {
    OK: 200,
    CREATED: 201,
    ACCEPTED: 202,
    NO_CONTENT: 204,
    BAD_REQUEST: 400,
    UNAUTHORIZED: 401,
    FORBIDDEN: 403,
    NOT_FOUND: 404,
    CONFLICT: 409,
    INTERNAL_SERVER_ERROR: 500,
    SERVICE_UNAVAILABLE: 503,
} as const
