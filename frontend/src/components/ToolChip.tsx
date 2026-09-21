import type { ToolCall } from '../api'

// Colour shows which retrieval path answered: SQL over the report data (periwinkle) vs vector search over docs (violet).
export function ToolChip({ call }: { call: ToolCall }) {
  const isDocs = call.name === 'search_docs'
  return (
    <span
      title={call.arguments}
      className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
        isDocs ? 'bg-brand-100 text-brand-800' : 'bg-periwinkle-100 text-periwinkle-800'
      }`}
    >
      {isDocs ? 'docs' : 'sql'} · {call.name}
    </span>
  )
}
