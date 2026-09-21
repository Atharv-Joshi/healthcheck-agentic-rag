import { useEffect, useRef } from 'react'
import type { StackCard } from '../api'
import { formatDate, formatNumber } from '../format'
import { ChatInput } from './ChatInput'
import { ExampleQuestions } from './ExampleQuestions'
import { MessageBubble, type Message } from './MessageBubble'

type Props = {
  stack: StackCard
  messages: Message[]
  loading: boolean
  onSend: (question: string) => void
  onReset: () => void
}

export function ChatView({ stack, messages, loading, onSend, onReset }: Props) {
  const bottom = useRef<HTMLDivElement>(null)
  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  return (
    <div className="mx-auto flex h-screen max-w-3xl flex-col px-4 py-4">
      <header className="pb-3">
        <a href="#/" className="text-sm text-slate-500 hover:text-slate-800 hover:underline">
          ← All stacks
        </a>
        <div className="mt-1 flex items-start justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold text-slate-900">{stack.name}</h1>
            <p className="text-sm text-slate-500">
              {formatNumber(stack.entries_count)} entries · {formatNumber(stack.assets_count)} assets · audited{' '}
              {formatDate(stack.run_date)}
            </p>
          </div>
          <button
            onClick={onReset}
            disabled={messages.length === 0 || loading}
            className="shrink-0 rounded-md border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-40"
          >
            New chat
          </button>
        </div>
        <p className="mt-2 rounded-md bg-slate-100 px-3 py-1.5 text-xs text-slate-600">
          This chat only covers <strong>{stack.name}</strong>. To ask about another stack, go back to all stacks and
          open it.
        </p>
      </header>

      <main
        role="log"
        aria-live="polite"
        aria-label="Conversation"
        className="flex-1 space-y-4 overflow-y-auto rounded-lg border border-slate-200 bg-white p-4"
      >
        {messages.length === 0 && <ExampleQuestions onPick={onSend} />}
        {messages.map((m, i) => (
          <MessageBubble key={i} message={m} />
        ))}
        {loading && <p className="text-sm text-slate-400">Thinking…</p>}
        <div ref={bottom} />
      </main>

      <ChatInput disabled={loading} placeholder={`Ask about ${stack.name}…`} onSend={onSend} />
    </div>
  )
}
