# Backend Communication Setup

## 🏗️ Architecture

```
Frontend (Next.js)
    ↓
API Client (services/api.ts)
    ↓
Specialized Services (services/auth.ts, chat.ts, document.ts)
    ↓
Hooks (useApi.ts, useAuth.ts)
    ↓
Components
    ↓
Backend (Django - http://localhost:8000/api/v1)
```

## 🔧 Configuration

### Environment Variables

```bash
# .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_SITE_URL=http://localhost:3000
```

### Docker Compose Settings

Backend service:
- **Port**: 8000
- **CORS**: Configured for `http://localhost:3000`
- **API Base**: `/api/v1`

Frontend service:
- **Port**: 3000
- **API Base**: `http://localhost:8000/api/v1`

## 📡 API Client Architecture

### Core Features

✅ **Error Handling**
- Custom error types: `ApiError`, `NetworkError`, `TimeoutError`
- Proper error messages from backend

✅ **Retry Logic**
- Exponential backoff (1s → 2s → 4s)
- Configurable retry count
- Skips retries on 4xx errors

✅ **Authentication**
- Automatic bearer token injection
- Token stored in localStorage
- Refreshable tokens support

✅ **Timeout Handling**
- Default: 30 seconds
- Upload: 120 seconds
- Configurable per request

✅ **Request Methods**
```typescript
api.get(endpoint, options)
api.post(endpoint, data, options)
api.put(endpoint, data, options)
api.patch(endpoint, data, options)
api.delete(endpoint, options)
```

## 🔐 Authentication Flow

### Login/Register

```typescript
import { authService } from '@/services/auth'

// Login
const response = await authService.login({
  email: 'user@example.com',
  password: 'password'
})
// Token stored automatically in localStorage

// Register
const response = await authService.register({
  email: 'user@example.com',
  password: 'password',
  name: 'User Name'
})
```

### Using Authentication in Hooks

```typescript
'use client'

import { useAuth } from '@/hooks/useAuth'

export function LoginForm() {
  const { login, loading, error } = useAuth()

  const handleLogin = async (email: string, password: string) => {
    try {
      await login({ email, password })
    } catch (err) {
      console.error('Login failed:', err)
    }
  }

  return (
    // ...
  )
}
```

## 📊 Service Usage Examples

### Chat Service

```typescript
import { chatService } from '@/services/chat'

// Get messages
const messages = await chatService.getMessages('conversation-id')

// Send message
const newMessage = await chatService.sendMessage(
  'conversation-id',
  'Hello!'
)

// Create conversation
const conv = await chatService.createConversation('My Chat')
```

### Document Service

```typescript
import { documentService } from '@/services/document'

// List documents
const docs = await documentService.listDocuments()

// Upload document
const file = new File(['content'], 'doc.pdf')
const doc = await documentService.uploadDocument(file)

// Delete document
await documentService.deleteDocument('doc-id')
```

## 🎯 Component Integration

### Using useApi Hook

```typescript
'use client'

import { useApi } from '@/hooks/useApi'

export function MyComponent() {
  const { request, loading, error, data } = useApi({
    onSuccess: (data) => console.log('Success:', data),
    onError: (error) => console.error('Error:', error),
    timeout: 60000, // 60 seconds
  })

  const fetchData = async () => {
    try {
      const result = await request('/endpoint', 'GET')
    } catch (err) {
      // Error already in state
    }
  }

  return (
    <div>
      {loading && <p>Loading...</p>}
      {error && <p>Error: {error.message}</p>}
      <button onClick={fetchData}>Fetch</button>
    </div>
  )
}
```

### Using Specialized Services

```typescript
'use client'

import { useState } from 'react'
import { authService } from '@/services/auth'

export function ProtectedComponent() {
  const [user, setUser] = useState(null)

  const getUser = async () => {
    try {
      // Get token from auth service
      const token = authService.getToken()
      if (token) {
        setUser(authService.isAuthenticated())
      }
    } catch (error) {
      console.error('Failed to get user')
    }
  }

  return (
    // ...
  )
}
```

## 🚨 Error Handling

### Error Types

```typescript
import { ApiError, NetworkError, TimeoutError } from '@/services/api'

try {
  await api.get('/endpoint')
} catch (error) {
  if (error instanceof ApiError) {
    console.error('API Error:', error.status, error.message, error.data)
  } else if (error instanceof NetworkError) {
    console.error('Network Error:', error.message)
  } else if (error instanceof TimeoutError) {
    console.error('Timeout:', error.message)
  }
}
```

## 📝 API Response Format

All responses follow Django REST Framework convention:

```typescript
interface ApiResponse<T> {
  data: T                    // Actual data
  message?: string          // Optional message
  success: boolean          // Success status
  error?: string           // Error message if failed
}
```

### Backend Response Example

```json
{
  "data": {
    "id": "123",
    "email": "user@example.com",
    "name": "User Name"
  },
  "message": "User created successfully",
  "success": true
}
```

## ⚙️ Advanced Configuration

### Custom Timeouts

```typescript
// Per-request timeout
await api.get('/slow-endpoint', { timeout: 120000 })

// Disable retries
await api.post('/endpoint', data, { retries: 0 })
```

### CORS Configuration

Backend Django settings already configured:
- **Origins**: `http://localhost:3000`
- **Credentials**: Enabled
- **Methods**: GET, POST, PUT, PATCH, DELETE, OPTIONS
- **Max Age**: 600 seconds

### Authentication Headers

Automatically added:
```
Authorization: Bearer {token}
Content-Type: application/json
```

## 🔍 Debugging

### Enable Request Logging

```typescript
// Add to services/api.ts for development
if (process.env.NODE_ENV === 'development') {
  console.log('API Request:', method, url)
  console.log('Headers:', headers)
  console.log('Body:', data)
}
```

### Check Token

```typescript
import { authService } from '@/services/auth'

console.log('Token:', authService.getToken())
console.log('Is Authenticated:', authService.isAuthenticated())
```

## 🚀 Production Checklist

- [ ] Update `NEXT_PUBLIC_API_URL` to production backend URL
- [ ] Set `DEBUG=false` in backend
- [ ] Update `ALLOWED_HOSTS` in backend Django settings
- [ ] Configure CORS origins for production domain
- [ ] Enable HTTPS for all requests
- [ ] Implement token refresh logic
- [ ] Add request logging for monitoring
- [ ] Test error scenarios
- [ ] Set appropriate timeouts based on expected latency
