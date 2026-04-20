/**
 * Response Middleware - Normalize response data
 * Parse JSON/text based on content-type
 */

export async function responseMiddleware(response: Response): Promise<unknown> {
    const contentType = response.headers.get('content-type')
    const isJson = contentType?.includes('application/json')
    const isText = contentType?.includes('text/') || !contentType

    try {
        if (isJson) {
            return await response.json()
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
