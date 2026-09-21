import { useEffect, useRef } from 'react'
import type { StackCard } from '../api'
import { formatDate, formatNumber } from '../format'
import { ChatInput } from './ChatInput'
import { Disclaimer } from './Disclaimer'
import { ExampleQuestions } from './ExampleQuestions'
import { Logo } from './Logo'
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
    <div className="mx-auto flex h-dvh max-w-3xl flex-col px-4 py-4">
      <header className="pb-3">
        <a
          href="#/"
          className="inline-flex items-center gap-1 rounded text-sm font-medium text-brand-700 hover:text-brand-800 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
        >
          <span aria-hidden>←</span> All stacks
        </a>
        <div className="mt-2 flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <Logo size={36} />
            <div>
              <h1 className="text-xl font-semibold leading-tight tracking-tight text-ink">{stack.name}</h1>
              <p className="text-sm text-ink-muted">
                {formatNumber(stack.entries_count)} entries · {formatNumber(stack.assets_count)} assets · audited{' '}
                {formatDate(stack.run_date)}
              </p>
            </div>
          </div>
          <button
            onClick={onReset}
            disabled={messages.length === 0 || loading}
            className="shrink-0 rounded-xl border border-brand-200 bg-white px-3.5 py-1.5 text-sm font-medium text-brand-700 shadow-sm hover:bg-brand-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 disabled:opacity-40"
          >
            New chat
          </button>
        </div>
        <p className="mt-3 flex items-center gap-2 rounded-lg bg-brand-50 px-3 py-2 text-xs text-brand-800">
          <svg width="14" height="14" viewBox="0 0 16 16" aria-hidden="true" className="shrink-0">
            <path
              d="M5 7V5a3 3 0 0 1 6 0v2M4 7h8a1 1 0 0 1 1 1v5a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V8a1 1 0 0 1 1-1z"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.4"
              strokeLinecap="round"
            />
          </svg>
          <span>
            This chat only covers <strong>{stack.name}</strong>. To ask about another stack, go back to all stacks and
            open it.
          </span>
        </p>
      </header>

      <main
        role="log"
        aria-live="polite"
        aria-label="Conversation"
        className="flex-1 space-y-4 overflow-y-auto rounded-2xl border border-brand-100 bg-white/80 p-4 shadow-sm shadow-brand-900/5 backdrop-blur"
      >
        {messages.length === 0 && <ExampleQuestions onPick={onSend} />}
        {messages.map((m, i) => (
          <MessageBubble key={i} message={m} />
        ))}
        {loading && (
          <div className="flex items-center gap-2 text-sm text-ink-muted" role="status">
            <span className="flex gap-1" aria-hidden>
              <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-brand-400" />
              <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-brand-400 [animation-delay:120ms]" />
              <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-brand-400 [animation-delay:240ms]" />
            </span>
            Thinking…
          </div>
        )}
        <div ref={bottom} />
      </main>

      <ChatInput disabled={loading} placeholder={`Ask about ${stack.name}…`} onSend={onSend} />
      <Disclaimer className="pt-2 text-center" />
    </div>
  )
}
