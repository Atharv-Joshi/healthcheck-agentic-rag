import { useEffect, useRef, useState } from 'react'

type ToolCall = { name: string; arguments: string }
type Message =
  | { role: 'user'; text: string }
  | { role: 'assistant'; text: string; toolCalls: ToolCall[]; error?: boolean }

const EXAMPLES = [
  'What are the top 3 actions required for Globex Corporate Site?',
  'How many checks failed for Initech Support Portal?',
  'Why does two-factor authentication matter?',
  'Is SSO enabled for Acme Retail - Web, and why does it matter?',
]

async function askApi(question: string) {
  const res = await fetch('/api/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  })
  const body = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(body.detail ?? `Request failed (${res.status})`)
  return body as { answer: string; tool_calls: ToolCall[] }
}

// Tool badge colour shows which retrieval path answered: SQL (report data) vs vector search (docs).
function ToolChip({ call }: { call: ToolCall }) {
  const isDocs = call.name === 'search_docs'
  return (
    <span
      title={call.arguments}
      className={`rounded-full px-2 py-0.5 text-xs font-medium ${
        isDocs ? 'bg-violet-100 text-violet-800' : 'bg-sky-100 text-sky-800'
      }`}
    >
      {isDocs ? 'docs' : 'sql'} · {call.name}
    </span>
  )
}

export default function App() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottom = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  async function send(question: string) {
    const q = question.trim()
    if (!q || loading) return
    setInput('')
    setMessages((m) => [...m, { role: 'user', text: q }])
    setLoading(true)
    try {
      const r = await askApi(q)
      setMessages((m) => [...m, { role: 'assistant', text: r.answer, toolCalls: r.tool_calls }])
    } catch (e) {
      setMessages((m) => [...m, { role: 'assistant', text: (e as Error).message, toolCalls: [], error: true }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto flex h-screen max-w-3xl flex-col px-4 py-4">
      <header className="pb-3">
        <h1 className="text-xl font-semibold text-slate-900">Healthcheck Report Q&amp;A</h1>
        <p className="text-sm text-slate-500">
          Ask about a Contentstack Healthcheck audit. Demo runs on synthetic mock data.
        </p>
      </header>

      <main className="flex-1 space-y-4 overflow-y-auto rounded-lg border border-slate-200 bg-white p-4">
        {messages.length === 0 && (
          <div className="space-y-2">
            <p className="text-sm text-slate-500">Try a question:</p>
            {EXAMPLES.map((ex) => (
              <button
                key={ex}
                onClick={() => send(ex)}
                className="block w-full rounded-md border border-slate-200 px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-50"
              >
                {ex}
              </button>
            ))}
          </div>
        )}
        {messages.map((m, i) =>
          m.role === 'user' ? (
            <div key={i} className="flex justify-end">
              <div className="max-w-[85%] rounded-2xl bg-slate-900 px-4 py-2 text-sm text-white">{m.text}</div>
            </div>
          ) : (
            <div key={i} className="max-w-[90%] space-y-2">
              <div
                className={`whitespace-pre-wrap rounded-2xl px-4 py-2 text-sm ${
                  m.error ? 'bg-red-50 text-red-800' : 'bg-slate-100 text-slate-900'
                }`}
              >
                {m.text}
              </div>
              {m.toolCalls.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {m.toolCalls.map((c, j) => (
                    <ToolChip key={j} call={c} />
                  ))}
                </div>
              )}
            </div>
          ),
        )}
        {loading && <p className="text-sm text-slate-400">Thinking…</p>}
        <div ref={bottom} />
      </main>

      <form
        className="flex gap-2 pt-3"
        onSubmit={(e) => {
          e.preventDefault()
          send(input)
        }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about a stack, a check, or a recommendation…"
          maxLength={1000}
          className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-500"
        />
        <button
          disabled={loading || !input.trim()}
          className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
        >
          Ask
        </button>
      </form>
    </div>
  )
}
