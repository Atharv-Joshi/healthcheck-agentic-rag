import { useState } from 'react'

export function ChatInput({ disabled, onSend }: { disabled: boolean; onSend: (text: string) => void }) {
  const [value, setValue] = useState('')
  return (
    <form
      className="flex gap-2 pt-3"
      onSubmit={(e) => {
        e.preventDefault()
        if (!value.trim() || disabled) return
        onSend(value.trim())
        setValue('')
      }}
    >
      <input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="Ask about a stack, a check, or a recommendation…"
        maxLength={1000}
        className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-500"
      />
      <button
        disabled={disabled || !value.trim()}
        className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
      >
        Ask
      </button>
    </form>
  )
}
