import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { Retry, ToolCall, Verification } from '../api'
import { ToolChip } from './ToolChip'

export type Message =
  | { role: 'user'; text: string }
  | {
      role: 'assistant'
      text: string
      toolCalls: ToolCall[]
      retries?: Retry[]
      verification?: Verification | null
      error?: boolean
    }

export function MessageBubble({ message }: { message: Message }) {
  if (message.role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-2xl bg-slate-900 px-4 py-2 text-sm text-white">{message.text}</div>
      </div>
    )
  }
  return (
    <div className="max-w-[90%] space-y-2">
      <div
        className={`rounded-2xl px-4 py-2 text-sm ${
          message.error ? 'bg-red-50 text-red-800' : 'prose prose-sm max-w-none bg-slate-100 text-slate-900'
        }`}
      >
        {message.error ? message.text : <Markdown remarkPlugins={[remarkGfm]}>{message.text}</Markdown>}
      </div>
      {(message.toolCalls.length > 0 || message.retries?.length || message.verification?.status === 'unsupported') && (
        <div className="flex flex-wrap gap-1">
          {message.toolCalls.map((c, i) => (
            <ToolChip key={i} call={c} />
          ))}
          {message.retries?.map((r, i) => (
            <span
              key={`r${i}`}
              title={`${r.outcome}${r.retry_query ? ` · retry query: ${r.retry_query}` : ''}`}
              className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800"
            >
              ↻ retried · {r.reason}
            </span>
          ))}
          {message.verification?.status === 'unsupported' && (
            <span
              title={message.verification.reason}
              className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-800"
            >
              ⚠ unverified against docs
            </span>
          )}
        </div>
      )}
    </div>
  )
}
