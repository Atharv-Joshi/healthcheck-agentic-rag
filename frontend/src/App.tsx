import { useCallback, useEffect, useState } from 'react'
import { askStack, fetchStacks, type HistoryMessage, type StackCard } from './api'
import { ChatView } from './components/ChatView'
import { Dashboard } from './components/Dashboard'
import type { Message } from './components/MessageBubble'
import { useStackRoute } from './useStackRoute'

/** What the server remembers about the conversation: earlier turns of THIS stack's chat (errors are not turns). */
function toHistory(messages: Message[]): HistoryMessage[] {
  return messages.flatMap<HistoryMessage>((m) => {
    if (m.role === 'user') return [{ role: 'user', content: m.text }]
    return m.error ? [] : [{ role: 'assistant', content: m.text }]
  })
}

export default function App() {
  const stackId = useStackRoute()
  const [stacks, setStacks] = useState<StackCard[] | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  // One conversation per stack, kept while you browse (in memory only; a page reload starts fresh).
  const [chats, setChats] = useState<Record<number, Message[]>>({})
  const [loading, setLoading] = useState(false)

  const loadStacks = useCallback(() => {
    setLoadError(null)
    setStacks(null)
    fetchStacks()
      .then(setStacks)
      .catch((e: Error) => setLoadError(e.message))
  }, [])

  useEffect(loadStacks, [loadStacks])

  if (stackId === null) return <Dashboard stacks={stacks} error={loadError} onRetry={loadStacks} />

  const stack = stacks?.find((s) => s.id === stackId)
  if (!stack) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-8 text-sm text-slate-600">
        {loadError ? (
          <>
            <p role="alert" className="text-red-700">{loadError}</p>
            <button onClick={loadStacks} className="mt-2 rounded-md border border-slate-300 px-3 py-1.5">
              Try again
            </button>
          </>
        ) : stacks ? (
          <p>That stack doesn’t exist.</p>
        ) : (
          <p>Loading…</p>
        )}
        <a href="#/" className="mt-4 inline-block text-slate-700 underline">
          ← All stacks
        </a>
      </div>
    )
  }

  const messages = chats[stack.id] ?? []
  const setMessages = (update: (m: Message[]) => Message[]) =>
    setChats((c) => ({ ...c, [stack.id]: update(c[stack.id] ?? []) }))

  async function send(question: string) {
    if (loading) return
    const history = toHistory(messages) // the turns BEFORE this question
    setMessages((m) => [...m, { role: 'user', text: question }])
    setLoading(true)
    try {
      const r = await askStack(stack!.id, question, history)
      setMessages((m) => [
        ...m,
        {
          role: 'assistant',
          text: r.answer,
          toolCalls: r.tool_calls,
          retries: r.retries,
          verification: r.verification,
          refusal: r.refusal,
        },
      ])
    } catch (e) {
      setMessages((m) => [...m, { role: 'assistant', text: (e as Error).message, toolCalls: [], error: true }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <ChatView
      key={stack.id} // a different stack is a different chat: no state carries over
      stack={stack}
      messages={messages}
      loading={loading}
      onSend={send}
      onReset={() => setMessages(() => [])}
    />
  )
}
