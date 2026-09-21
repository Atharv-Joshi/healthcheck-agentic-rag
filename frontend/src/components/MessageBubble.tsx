import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { Refusal, Retry, ToolCall, Verification } from '../api'
import { Logo } from './Logo'
import { ToolChip } from './ToolChip'

export type Message =
  | { role: 'user'; text: string }
  | {
      role: 'assistant'
      text: string
      toolCalls: ToolCall[]
      retries?: Retry[]
      verification?: Verification | null
      refusal?: Refusal | null
      error?: boolean
    }

export function MessageBubble({ message }: { message: Message }) {
  if (message.role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-2xl rounded-br-md bg-brand-600 px-4 py-2.5 text-sm text-white shadow-sm">
          {message.text}
        </div>
      </div>
    )
  }

  const bubble = message.error
    ? 'border-rose-200 bg-rose-50 text-rose-800'
    : message.refusal
      ? 'border-amber-200 bg-amber-50 text-ink'
      : 'border-brand-100 bg-white text-ink'
  const showChips =
    (!message.refusal && message.toolCalls.length > 0) ||
    !!message.retries?.length ||
    message.verification?.status === 'unsupported'

  return (
    <div className="flex max-w-[92%] gap-2.5">
      <div className="mt-1">
        <Logo size={24} />
      </div>
      <div className="min-w-0 space-y-2">
        <div
          className={`prose prose-sm max-w-none rounded-2xl rounded-tl-md border px-4 py-3 shadow-sm prose-p:my-1.5 prose-a:text-brand-700 prose-strong:text-ink prose-th:text-ink ${bubble}`}
        >
          {message.error ? message.text : <Markdown remarkPlugins={[remarkGfm]}>{message.text}</Markdown>}
        </div>

        {message.refusal && (
          <span className="inline-block rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-medium text-amber-800">
            {message.refusal === 'other_stack' ? 'other stack' : 'off topic'}
          </span>
        )}

        {showChips && (
          <div className="flex flex-wrap gap-1.5">
            {message.toolCalls.map((c, i) => (
              <ToolChip key={i} call={c} />
            ))}
            {message.retries?.map((r, i) => (
              <span
                key={`r${i}`}
                title={`${r.outcome}${r.retry_query ? ` · retry query: ${r.retry_query}` : ''}`}
                className="rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-medium text-amber-800"
              >
                ↻ retried · {r.reason}
              </span>
            ))}
            {message.verification?.status === 'unsupported' && (
              <span
                title={message.verification.reason}
                className="rounded-full bg-rose-100 px-2.5 py-0.5 text-xs font-medium text-rose-800"
              >
                ⚠ unverified against docs
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
