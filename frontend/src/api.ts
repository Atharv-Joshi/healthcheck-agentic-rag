export type ToolCall = { name: string; arguments: string }
export type Retry = {
  tool: string
  kind: 'vector_retry' | 'db_fallback'
  reason: string
  retry_query?: string
  outcome: string
}
export type Verification = { status: 'supported' | 'unsupported' | 'skipped'; reason: string }
export type Refusal = 'off_topic' | 'other_stack'
export type Answer = {
  answer: string
  tool_calls: ToolCall[]
  retries: Retry[]
  verification: Verification | null
  off_topic?: boolean
  refusal?: Refusal | null
}
export type StackCard = {
  id: number
  name: string
  entries_count: number
  assets_count: number
  run_date: string
  checks: { total: number; passed: number; failed: number; skipped: number }
  actions_required: number
  areas_of_opportunity: number
}
export type HistoryMessage = { role: 'user' | 'assistant'; content: string }

const ASK_TIMEOUT_MS = 60_000
// The free-tier server sleeps when idle; the first request after that can take about a minute.
const LIST_TIMEOUT_MS = 90_000

async function request<T>(path: string, init: RequestInit, timeoutMs: number): Promise<T> {
  let res: Response
  try {
    res = await fetch(path, { ...init, signal: AbortSignal.timeout(timeoutMs) })
  } catch (e) {
    if (e instanceof DOMException && e.name === 'TimeoutError') {
      throw new Error('The request timed out. Please try again.')
    }
    throw new Error('Could not reach the server.')
  }
  const body = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(typeof body.detail === 'string' ? body.detail : `Request failed (${res.status})`)
  return body as T
}

export const fetchStacks = () => request<StackCard[]>('/api/stacks', {}, LIST_TIMEOUT_MS)

export const askStack = (stackId: number, question: string, history: HistoryMessage[]) =>
  request<Answer>(
    `/api/stacks/${stackId}/ask`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, history }),
    },
    ASK_TIMEOUT_MS,
  )
