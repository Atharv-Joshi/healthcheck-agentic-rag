export type ToolCall = { name: string; arguments: string }
export type Retry = {
  tool: string
  kind: 'vector_retry' | 'db_fallback'
  reason: string
  retry_query?: string
  outcome: string
}
export type Verification = { status: 'supported' | 'unsupported' | 'skipped'; reason: string }
export type Answer = {
  answer: string
  tool_calls: ToolCall[]
  retries: Retry[]
  verification: Verification | null
}

const TIMEOUT_MS = 60_000

export async function askApi(question: string): Promise<Answer> {
  let res: Response
  try {
    res = await fetch('/api/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
      signal: AbortSignal.timeout(TIMEOUT_MS),
    })
  } catch (e) {
    if (e instanceof DOMException && e.name === 'TimeoutError') {
      throw new Error('The request timed out. Please try again.')
    }
    throw new Error('Could not reach the server.')
  }
  const body = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(body.detail ?? `Request failed (${res.status})`)
  return body as Answer
}
