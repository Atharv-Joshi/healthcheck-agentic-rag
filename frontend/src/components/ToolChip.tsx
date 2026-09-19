import type { ToolCall } from '../api'

// Colour shows which retrieval path answered: SQL (report data) vs vector search (docs).
export function ToolChip({ call }: { call: ToolCall }) {
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
