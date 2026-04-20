# PHÂN TÍCH CẤU TRÚC FRONTEND - TỪ GÓAT NHÌ KỸ SƯ CHUYÊN NGHIỆP

## 1. ĐÁNH GIÁ TỔNG QUÁT

### ✅ Điểm Mạnh (Đã Làm Tốt)

#### 1.1 **Stack Công Nghệ Hiện Đại**
- Next.js 16.2.4 (App Router) - Tốt, có SSR/SSG capabilities
- TypeScript strict mode - Tốt, type-safety cao
- Tailwind CSS v4 với postcss - Tốt, performance tốt
- Radix UI components - Tốt, accessibility focus
- React 19 - Tốt, features mới

#### 1.2 **Cấu Trúc Thư Mục Hợp Lý**
```
✓ Tách biệt concerns: components, services, hooks, types
✓ Path aliases (@/*) cấu hình tốt
✓ Design tokens centralized
✓ Type definitions riêng
```

#### 1.3 **API Service Layer**
- ✓ Custom error types (ApiError, NetworkError, TimeoutError)
- ✓ Retry logic với exponential backoff
- ✓ Timeout handling
- ✓ Auth token management
- ✓ Response wrapper handling

#### 1.4 **Authentication Service**
- ✓ Centralized auth logic
- ✓ Token management (access + refresh)
- ✓ LoginRequest/Response types định nghĩa rõ

#### 1.5 **Context API & Hooks**
- ✓ AuthProvider cho global state
- ✓ useApi hook có loading/error/data states
- ✓ Custom hooks pattern

---

## 2. ĐIỂM YẾU CẦN CẢI THIỆN 🔴

### 2.1 **Thiếu State Management cho Complex App**
**Problem:**
- Chỉ dùng Context API + useState
- Không có caching mechanism
- Mỗi lần navigate lại fetch dữ liệu
- Không có offline support

**Impact:** 
- ❌ UX kém (loading liên tục)
- ❌ Network request dư thừa
- ❌ Backend bị stress

**Solution Cần:**
- ➜ React Query (TanStack Query) cho server state
- ➜ Zustand/Redux cho client state
- ➜ Caching strategy

### 2.2 **Thiếu Middleware/Interceptor Pattern**
**Problem:**
```typescript
// Hiện tại: raw fetch mà không có centralized middleware
// Mỗi service tự xử lý error
```

**Cần:**
- ➜ Request middleware (add header, transform request)
- ➜ Response middleware (transform response, normalize data)
- ➜ Error middleware (centralized error handling)

### 2.3 **Error Handling Chưa Toàn Cục**
**Problem:**
- ❌ Không có Error Boundary
- ❌ Không có 401/403 handling toàn cục
- ❌ Không có fallback UI
- ❌ API errors không được log tập trung

**Solution Cần:**
- ➜ Error Boundary component
- ➜ Error interceptor
- ➜ Logger service
- ➜ Error tracking (Sentry/LogRocket)

### 2.4 **Environment Configuration Không Chuẩn**
**Problem:**
```typescript
// Hiện tại: hardcode, không pattern chuẩn
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'
```

**Cần:**
- ➜ Config file chuẩn (config/environment.ts)
- ➜ Validation environment variables
- ➜ Support multi-environment (dev, staging, prod)

### 2.5 **Upload/Download File - Pattern Không Chuẩn**
**Problem:**
```typescript
// documentService.ts - mix api instance & raw fetch
// ❌ Không consistent
// ❌ Không error handling đúng
const response = await fetch(`${api.baseUrl}/documents/upload`, {
    method: 'POST',
    headers: {
        'Authorization': `Bearer ${localStorage.getItem('auth_token') || ''}`,
    },
    body: formData,
})
```

**Cần:**
- ➜ Unified upload/download service
- ➜ Progress tracking
- ➜ Chunked upload support

### 2.6 **Types Không Toàn Diện**
**Problem:**
- ❌ Thiếu API response types (success/error cases)
- ❌ Thiếu request payload types cho một số endpoints
- ❌ Không có discriminated union types
- ❌ Paginated response type có nhưng không dùng consistent

### 2.7 **Testing Infrastructure**
**Problem:**
- ❌ Không thấy test setup
- ❌ Không mock API
- ❌ Không viết unit/integration tests

### 2.8 **Logging & Monitoring**
**Problem:**
- ❌ Không có logger service
- ❌ Không track user actions
- ❌ Không track performance
- ❌ Không error tracking

---

## 3. FLOW CHUẨN NHẤT - GỌI API TỪ BACKEND

### 📊 Kiến Trúc Flow Đề Xuất

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND (Next.js)                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────┐       ┌──────────────────┐            │
│  │   Components     │──────→│    Custom Hooks  │            │
│  │  (UI + Logic)    │       │  (useDocument,   │            │
│  │                  │       │   useChat, etc)  │            │
│  └──────────────────┘       └────────┬─────────┘            │
│                                      │                       │
│                            ┌─────────▼─────────┐            │
│                            │  React Query      │            │
│                            │  (Server State)   │            │
│                            └────────┬──────────┘            │
│                                     │                       │
│                    ┌────────────────▼────────────────┐      │
│                    │  API Service Layer              │      │
│                    │  ┌──────────────────────────┐   │      │
│                    │  │ Request Middleware:      │   │      │
│                    │  │ - Add Auth Token         │   │      │
│                    │  │ - Add Headers            │   │      │
│                    │  │ - Transform Request      │   │      │
│                    │  └──────────┬───────────────┘   │      │
│                    │             │                   │      │
│                    │  ┌──────────▼───────────────┐   │      │
│                    │  │ HTTP Client              │   │      │
│                    │  │ - Fetch API             │   │      │
│                    │  │ - Timeout Handling       │   │      │
│                    │  │ - Retry Logic            │   │      │
│                    │  └──────────┬───────────────┘   │      │
│                    │             │                   │      │
│                    │  ┌──────────▼───────────────┐   │      │
│                    │  │ Response Middleware:     │   │      │
│                    │  │ - Parse Response         │   │      │
│                    │  │ - Normalize Data         │   │      │
│                    │  │ - Handle Errors          │   │      │
│                    │  └──────────┬───────────────┘   │      │
│                    └────────────┬────────────────────┘      │
│                                 │                           │
│                    ┌────────────▼──────────────┐            │
│                    │  Error Boundary          │            │
│                    │  + Error Tracking        │            │
│                    │  + Retry Handler         │            │
│                    └────────────┬──────────────┘            │
│                                 │                           │
│                    ┌────────────▼──────────────┐            │
│                    │  Logger Service          │            │
│                    │  (Development/Prod)      │            │
│                    └──────────────────────────┘            │
│                                                               │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │ HTTPS
                              │
                    ┌─────────▼──────────┐
                    │  BACKEND (Django)  │
                    │  REST API          │
                    └────────────────────┘
```

---

## 4. CẤU TRÚC CÓ THỂ CẬP NHẬT

### 4.1 **Folder Structure Đề Xuất**

```
frontend/
├── app/                              # Next.js app directory
│   ├── layout.tsx
│   ├── page.tsx
│   ├── (auth)/                      # Route group
│   │   ├── login/
│   │   ├── register/
│   │   └── forgot-password/
│   ├── (dashboard)/                 # Protected routes
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   └── ...
│   └── api/                         # API routes (optional)
│
├── components/
│   ├── common/                      # Reusable components
│   ├── features/                    # Feature-specific
│   ├── ui/                          # UI primitives
│   ├── layout/
│   ├── error/
│   │   ├── ErrorBoundary.tsx       # ✨ New
│   │   ├── ErrorFallback.tsx       # ✨ New
│   │   └── ErrorPage.tsx
│   └── loading/                     # ✨ New
│
├── services/
│   ├── api/                         # ✨ New folder
│   │   ├── client.ts               # HTTP client
│   │   ├── interceptors.ts         # Middleware
│   │   └── types.ts
│   ├── auth.ts
│   ├── document.ts
│   ├── chat.ts
│   ├── department.ts               # ✨ New
│   ├── logger.ts                   # ✨ New
│   └── upload.ts                   # ✨ New (unified)
│
├── hooks/
│   ├── useApi.ts                   # ✨ Update
│   ├── useAuth.ts
│   ├── useAsync.ts                 # ✨ New
│   ├── useDebounce.ts              # ✨ New
│   └── useLocalStorage.ts          # ✨ New
│
├── context/
│   ├── AuthContext.tsx
│   ├── ThemeContext.tsx
│   ├── AppContext.tsx              # ✨ New (global state)
│   └── providers.tsx
│
├── lib/
│   ├── queryClient.ts              # ✨ New
│   ├── zodSchemas.ts               # ✨ New
│   └── utils.ts
│
├── config/
│   ├── environment.ts              # ✨ New (chuẩn hơn)
│   ├── design-tokens.ts
│   └── site.ts
│
├── constants/
│   ├── api.ts
│   ├── routes.ts                   # ✨ New
│   └── error-messages.ts           # ✨ New
│
├── types/
│   ├── index.ts
│   ├── api.ts                      # ✨ New (API-specific)
│   ├── domain.ts                   # ✨ New (business logic)
│   └── forms.ts                    # ✨ New
│
├── styles/
│   └── globals.css
│
├── middleware.ts                   # ✨ New (Next.js middleware)
├── tsconfig.json                   # ✨ Update
├── next.config.mjs
├── tailwind.config.js
├── package.json                    # ✨ Add packages
└── ...
```

---

## 5. FLOW CHI TIẾT - GỌI API TỪ COMPONENT

### 📝 Ví dụ Hoàn Chỉnh: Fetch Documents

#### **Step 1: Type Definitions** (types/api.ts)
```typescript
// ✨ Strongly typed API contracts
import { z } from 'zod'

// Request types
export const ListDocumentsRequestSchema = z.object({
  limit: z.number().default(20),
  offset: z.number().default(0),
  folderId: z.string().optional(),
})
export type ListDocumentsRequest = z.infer<typeof ListDocumentsRequestSchema>

// Response types
export const DocumentSchema = z.object({
  id: z.string(),
  name: z.string(),
  type: z.string(),
  size: z.number(),
  uploadedAt: z.string().datetime(),
  url: z.string().optional(),
})
export type Document = z.infer<typeof DocumentSchema>

export const ListDocumentsResponseSchema = z.object({
  data: z.array(DocumentSchema),
  total: z.number(),
  page: z.number(),
  limit: z.number(),
  pages: z.number(),
})
export type ListDocumentsResponse = z.infer<typeof ListDocumentsResponseSchema>

// API Error response
export const ApiErrorSchema = z.object({
  error: z.string(),
  message: z.string(),
  status: z.number(),
  details: z.unknown().optional(),
})
export type ApiError = z.infer<typeof ApiErrorSchema>
```

#### **Step 2: API Service** (services/document.ts)
```typescript
// ✨ Clean service layer
import { api } from '@/services/api/client'
import type { 
  Document, 
  ListDocumentsRequest, 
  ListDocumentsResponse 
} from '@/types/api'

export const documentService = {
  async listDocuments(params: ListDocumentsRequest): Promise<ListDocumentsResponse> {
    const queryString = new URLSearchParams({
      limit: params.limit.toString(),
      offset: params.offset.toString(),
      ...(params.folderId && { folder_id: params.folderId }),
    }).toString()

    return api.get<ListDocumentsResponse>(`/documents?${queryString}`, {
      cache: 'force-cache',  // Browser cache
      tags: ['documents'],    // For ISR/revalidation
    })
  },

  async uploadDocument(
    file: File, 
    folderId?: string,
    onProgress?: (progress: number) => void
  ): Promise<Document> {
    const formData = new FormData()
    formData.append('file', file)
    if (folderId) {
      formData.append('folder_id', folderId)
    }

    return api.upload<Document>(
      '/documents/upload',
      formData,
      { onProgress }
    )
  },

  async deleteDocument(documentId: string): Promise<void> {
    return api.delete(`/documents/${documentId}`, {
      tags: ['documents'],
    })
  },

  async getDocumentDetails(documentId: string): Promise<Document> {
    return api.get<Document>(`/documents/${documentId}`)
  },
}
```

#### **Step 3: React Query Hook** (hooks/useDocument.ts)
```typescript
// ✨ Server state management
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { documentService } from '@/services/document'
import type { ListDocumentsRequest } from '@/types/api'

const QUERY_KEYS = {
  all: ['documents'] as const,
  lists: () => [...QUERY_KEYS.all, 'list'] as const,
  list: (params: ListDocumentsRequest) => [...QUERY_KEYS.lists(), params] as const,
  details: () => [...QUERY_KEYS.all, 'detail'] as const,
  detail: (id: string) => [...QUERY_KEYS.details(), id] as const,
}

export function useDocuments(params: ListDocumentsRequest) {
  return useQuery({
    queryKey: QUERY_KEYS.list(params),
    queryFn: () => documentService.listDocuments(params),
    staleTime: 1000 * 60 * 5,        // 5 minutes
    gcTime: 1000 * 60 * 10,          // 10 minutes (garbage collection)
    retry: 2,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  })
}

export function useDocumentDetail(documentId: string) {
  return useQuery({
    queryKey: QUERY_KEYS.detail(documentId),
    queryFn: () => documentService.getDocumentDetails(documentId),
    enabled: !!documentId,
  })
}

export function useUploadDocument() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (vars: { file: File; folderId?: string; onProgress?: (p: number) => void }) =>
      documentService.uploadDocument(vars.file, vars.folderId, vars.onProgress),
    
    onSuccess: () => {
      // Revalidate documents list
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.lists() })
    },
    
    onError: (error: Error) => {
      // Error handling centralized in middleware
      console.error('Upload failed:', error)
    },
  })
}

export function useDeleteDocument() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (documentId: string) => documentService.deleteDocument(documentId),
    
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.lists() })
    },
  })
}
```

#### **Step 4: Component Usage** (app/documents/page.tsx)
```typescript
// ✨ Clean component code
'use client'

import { useState } from 'react'
import { useDocuments, useDeleteDocument } from '@/hooks/useDocument'
import { LoadingSpinner } from '@/components/loading'
import { ErrorAlert } from '@/components/error'
import { DocumentCard } from '@/components/features/DocumentCard'

export default function DocumentsPage() {
  const [page, setPage] = useState(1)
  const limit = 20

  // Fetch documents
  const { 
    data: response, 
    isLoading, 
    error 
  } = useDocuments({
    limit,
    offset: (page - 1) * limit,
  })

  // Delete mutation
  const { mutate: deleteDocument, isPending } = useDeleteDocument()

  if (isLoading) return <LoadingSpinner />
  if (error) return <ErrorAlert error={error} />

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Documents</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {response?.data.map((doc) => (
          <DocumentCard
            key={doc.id}
            document={doc}
            onDelete={() => deleteDocument(doc.id)}
            isDeleting={isPending}
          />
        ))}
      </div>

      {/* Pagination */}
      <div className="flex justify-center gap-2">
        {Array.from({ length: response?.pages || 1 }, (_, i) => i + 1).map((p) => (
          <button
            key={p}
            onClick={() => setPage(p)}
            className={p === page ? 'btn btn-active' : 'btn'}
          >
            {p}
          </button>
        ))}
      </div>
    </div>
  )
}
```

---

## 6. API CLIENT - IMPLEMENTATION CHUẨN

### services/api/client.ts
```typescript
// ✨ Centralized HTTP client
import { requestMiddleware } from './middleware/request'
import { responseMiddleware } from './middleware/response'
import { errorMiddleware } from './middleware/error'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

interface RequestOptions extends RequestInit {
  timeout?: number
  retries?: number
  tags?: string[]
  onProgress?: (progress: number) => void
}

class ApiClient {
  private baseUrl: string

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl
  }

  async request<T>(
    method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH',
    endpoint: string,
    data?: unknown,
    options?: RequestOptions
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`
    let request = new Request(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
    })

    // Request middleware
    request = await requestMiddleware(request, data)

    // Execute with retry logic
    const response = await this.fetchWithRetry(request, options)

    // Response middleware
    const processedResponse = await responseMiddleware(response)

    // Handle errors
    if (!response.ok) {
      await errorMiddleware(response, processedResponse)
    }

    return processedResponse as T
  }

  private async fetchWithRetry(
    request: Request,
    options?: RequestOptions,
    attempt = 0
  ): Promise<Response> {
    const timeout = options?.timeout ?? 30000
    const retries = options?.retries ?? 3

    try {
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), timeout)

      const response = await fetch(request, {
        signal: controller.signal,
      })

      clearTimeout(timeoutId)
      return response
    } catch (error) {
      if (attempt < retries && (error instanceof TypeError || error.name === 'AbortError')) {
        const delay = Math.min(1000 * Math.pow(2, attempt), 10000)
        await new Promise(resolve => setTimeout(resolve, delay))
        return this.fetchWithRetry(request, options, attempt + 1)
      }
      throw error
    }
  }

  async get<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    return this.request<T>('GET', endpoint, undefined, options)
  }

  async post<T>(endpoint: string, data?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>('POST', endpoint, data, options)
  }

  async upload<T>(
    endpoint: string,
    formData: FormData,
    options?: RequestOptions
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`
    const request = new Request(url, { method: 'POST', body: formData })

    // Add auth to request
    const token = getAuthToken()
    if (token) {
      request.headers.set('Authorization', `Bearer ${token}`)
    }

    return this.request<T>('POST', endpoint, formData, options)
  }

  async delete<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    return this.request<T>('DELETE', endpoint, undefined, options)
  }

  // ... put, patch methods
}

export const api = new ApiClient(API_BASE_URL)
```

### services/api/middleware/request.ts
```typescript
// ✨ Request transformation
import { getAuthToken } from '@/services/auth'

export async function requestMiddleware(
  request: Request,
  data?: unknown
): Promise<Request> {
  // Add auth token
  const token = getAuthToken()
  if (token) {
    request.headers.set('Authorization', `Bearer ${token}`)
  }

  // Add request ID for tracking
  const requestId = crypto.randomUUID()
  request.headers.set('X-Request-ID', requestId)

  // Add version header
  request.headers.set('X-API-Version', '1.0')

  // Add body if needed
  if (data && request.method !== 'GET') {
    request = new Request(request, {
      body: JSON.stringify(data),
    })
  }

  return request
}
```

### services/api/middleware/response.ts
```typescript
// ✨ Response normalization
import { ApiError } from '@/services/api/errors'

export async function responseMiddleware(response: Response): Promise<unknown> {
  const contentType = response.headers.get('content-type')
  const isJson = contentType?.includes('application/json')

  if (isJson) {
    return response.json()
  }

  return response.text()
}
```

### services/api/middleware/error.ts
```typescript
// ✨ Centralized error handling
import { logger } from '@/services/logger'
import { ApiError } from '@/services/api/errors'

export async function errorMiddleware(response: Response, data: unknown): Promise<void> {
  const requestId = response.headers.get('X-Request-ID')
  const errorData = data as Record<string, unknown> | null

  // Log error
  logger.error({
    message: 'API Error',
    status: response.status,
    url: response.url,
    requestId,
    data: errorData,
  })

  // Handle specific status codes
  if (response.status === 401) {
    // Unauthorized - redirect to login
    window.location.href = '/login'
  }

  if (response.status === 403) {
    // Forbidden - redirect to dashboard
    window.location.href = '/dashboard'
  }

  throw new ApiError(
    response.status,
    errorData?.message as string || `HTTP ${response.status}`,
    errorData
  )
}
```

---

## 7. ERROR HANDLING - TOÀN CỤC

### components/error/ErrorBoundary.tsx
```typescript
'use client'

import React from 'react'
import { logger } from '@/services/logger'
import { ErrorFallback } from './ErrorFallback'

interface Props {
  children: React.ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    logger.error({
      message: 'React Error Boundary',
      error: error.message,
      componentStack: errorInfo.componentStack,
    })
  }

  render() {
    if (this.state.hasError && this.state.error) {
      return <ErrorFallback error={this.state.error} />
    }

    return this.props.children
  }
}
```

---

## 8. LOGGER SERVICE

### services/logger.ts
```typescript
type LogLevel = 'debug' | 'info' | 'warn' | 'error'

interface LogEntry {
  timestamp: string
  level: LogLevel
  message: string
  [key: string]: unknown
}

class Logger {
  private logs: LogEntry[] = []

  private createEntry(level: LogLevel, message: string, data?: unknown): LogEntry {
    return {
      timestamp: new Date().toISOString(),
      level,
      message,
      ...data,
    }
  }

  debug(message: string, data?: unknown) {
    this.log('debug', message, data)
  }

  info(message: string, data?: unknown) {
    this.log('info', message, data)
  }

  warn(message: string, data?: unknown) {
    this.log('warn', message, data)
  }

  error(message: string | object, data?: unknown) {
    this.log('error', typeof message === 'string' ? message : 'Error', 
      typeof message === 'string' ? data : message)
  }

  private log(level: LogLevel, message: string, data?: unknown) {
    const entry = this.createEntry(level, message, data)
    this.logs.push(entry)

    // In development, log to console
    if (process.env.NODE_ENV === 'development') {
      console[level === 'debug' ? 'log' : level](`[${level.toUpperCase()}]`, entry)
    }

    // In production, send to backend/Sentry
    if (process.env.NODE_ENV === 'production') {
      this.sendToBackend(entry)
    }
  }

  private async sendToBackend(entry: LogEntry) {
    try {
      await fetch('/api/logs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(entry),
      })
    } catch (err) {
      // Fail silently
    }
  }
}

export const logger = new Logger()
```

---

## 9. ENVIRONMENT CONFIGURATION

### config/environment.ts
```typescript
const requiredEnvVars = [
  'NEXT_PUBLIC_API_URL',
] as const

// Validate environment variables
Object.values(requiredEnvVars).forEach((envVar) => {
  if (!process.env[envVar]) {
    throw new Error(`Missing required environment variable: ${envVar}`)
  }
})

export const env = {
  apiUrl: process.env.NEXT_PUBLIC_API_URL!,
  environment: (process.env.NODE_ENV || 'development') as 'development' | 'production' | 'staging',
  isDevelopment: process.env.NODE_ENV === 'development',
  isProduction: process.env.NODE_ENV === 'production',
  logLevel: (process.env.NEXT_PUBLIC_LOG_LEVEL || 'info') as LogLevel,
} as const
```

### .env.local (example)
```
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_LOG_LEVEL=debug
```

---

## 10. PACKAGE.JSON - CẬP NHẬT CẦN THIẾT

```json
{
  "dependencies": {
    // Existing...
    "@tanstack/react-query": "^5.0.0",
    "@tanstack/react-query-devtools": "^5.0.0",
    "@hookform/resolvers": "^3.10.0",
    "@sentry/react": "^7.0.0",
    "@sentry/tracing": "^7.0.0",
    "axios": "^1.6.0",
    "zod": "^3.22.0",
    "zustand": "^4.4.0",
  },
  "devDependencies": {
    "@testing-library/react": "^14.0.0",
    "@testing-library/jest-dom": "^6.0.0",
    "msw": "^1.3.0",
    "@vitest/ui": "^1.0.0",
    "vitest": "^1.0.0",
  }
}
```

---

## 11. KIẾN NGHỊ ƯU TIÊN (Priority Order)

### 🔴 **CRITICAL (Week 1)**
1. Add React Query for server state management
2. Create Error Boundary component
3. Implement centralized error middleware
4. Add Logger service
5. Implement proper TypeScript types with Zod validation

### 🟠 **HIGH (Week 2)**
6. Add testing infrastructure (Vitest + MSW)
7. Create environment configuration structure
8. Implement file upload service (unified)
9. Add request/response interceptors
10. Implement error tracking (Sentry)

### 🟡 **MEDIUM (Week 3+)**
11. Add state management (Zustand)
12. Implement offline support
13. Add performance monitoring
14. Create API documentation (Swagger)
15. Add E2E tests (Playwright/Cypress)

---

## 12. TỔNG KẾT RATING

| Aspect | Rating | Comment |
|--------|--------|---------|
| **Stack Technology** | ⭐⭐⭐⭐⭐ | Modern, well-chosen |
| **Folder Structure** | ⭐⭐⭐⭐ | Good, can be enhanced |
| **API Layer** | ⭐⭐⭐⭐ | Solid foundation, needs middleware |
| **Error Handling** | ⭐⭐⭐ | Basic, needs global strategy |
| **State Management** | ⭐⭐⭐ | Basic Context API, needs React Query |
| **Type Safety** | ⭐⭐⭐⭐ | Good with TypeScript, needs Zod |
| **Testing** | ⭐ | Not visible |
| **Documentation** | ⭐⭐ | Basic |
| **Performance** | ⭐⭐⭐⭐ | Good but can optimize |
| **Overall** | ⭐⭐⭐⭐ | **Professional level**, ready for production with improvements |

---

## 13. NEXT STEPS

### Ngay lập tức cần làm:
1. ✅ Review báo cáo này với team
2. ✅ Prioritize improvements dựa trên business needs
3. ✅ Setup React Query + configure QueryClient
4. ✅ Create comprehensive type definitions
5. ✅ Implement Error Boundary
6. ✅ Add Logger service
7. ✅ Setup testing infrastructure

Cấu trúc frontend của bạn đã ở **mức chuyên nghiệp** rồi, nhưng cần thêm một số patterns chuẩn để thành **enterprise-grade** 🚀
