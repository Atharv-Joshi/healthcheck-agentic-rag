import { useEffect, useRef, useState } from 'react'
import { askApi } from './api'
import { ChatInput } from './components/ChatInput'
import { ExampleQuestions } from './components/ExampleQuestions'
import { MessageBubble, type Message } from './components/MessageBubble'

export default function App() {
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(false)
  const bottom = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  async function send(question: string) {
    if (loading) return
    setMessages((m) => [...m, { role: 'user', text: question }])
    setLoading(true)
    try {
      const r = await askApi(question)
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

      <main role="log" aria-live="polite" aria-label="Conversation" className="flex-1 space-y-4 overflow-y-auto rounded-lg border border-slate-200 bg-white p-4">
        {messages.length === 0 && <ExampleQuestions onPick={send} />}
        {messages.map((m, i) => (
          <MessageBubble key={i} message={m} />
        ))}
        {loading && <p className="text-sm text-slate-400">Thinking…</p>}
        <div ref={bottom} />
      </main>

      <ChatInput disabled={loading} onSend={send} />
    </div>
  )
}
