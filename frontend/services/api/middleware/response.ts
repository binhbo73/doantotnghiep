/**
 * Response Middleware - Normalize response data
 * Parse JSON/text based on content-type
 */

export async function responseMiddleware(response: Response): Promise<unknown> {
    // 204/205 responses intentionally have no body. Attempting response.json()
    // would throw "Unexpected end of JSON input" after a successful delete.
    if (response.status === 204 || response.status === 205) {
        return undefined
    }

    const contentType = response.headers.get('content-type')
    const contentLength = response.headers.get('content-length')
    const isJson = contentType?.includes('application/json')
    const isText = contentType?.includes('text/') || !contentType

    if (contentLength === '0') {
        return undefined
    }

    try {
        if (isJson) {
            const text = await response.text()
            return text ? JSON.parse(text) : undefined
        }

        if (isText) {
            return await response.text()
        }

        // For other types, try JSON first, fallback to text
        try {
            return await response.json()
        } catch {
            return await response.text()
        }
    } catch (err) {
        console.error('Error parsing response:', err)
        throw err
    }
}
