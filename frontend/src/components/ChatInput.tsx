import { useState } from 'react'

export function ChatInput({
  disabled,
  placeholder,
  onSend,
}: {
  disabled: boolean
  placeholder: string
  onSend: (text: string) => void
}) {
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
        placeholder={placeholder}
        maxLength={1000}
        aria-label={placeholder}
        className="flex-1 rounded-xl border border-brand-200 bg-white px-4 py-2.5 text-sm text-ink shadow-sm outline-none placeholder:text-ink-muted focus:border-brand-500 focus:ring-2 focus:ring-brand-200"
      />
      <button
        disabled={disabled || !value.trim()}
        className="rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-brand-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 disabled:opacity-40"
      >
        Ask
      </button>
    </form>
  )
}
