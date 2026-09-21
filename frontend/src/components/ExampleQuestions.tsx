// Stack-agnostic on purpose: every chat is already locked to one stack, so questions never need to name it.
const EXAMPLES = [
  'What are the top actions required?',
  'How many checks failed?',
  'List the failed Security checks',
  'Why does two-factor authentication matter?',
]

export function ExampleQuestions({ onPick }: { onPick: (q: string) => void }) {
  return (
    <div>
      <p className="mb-3 text-sm font-medium text-ink">Try asking</p>
      <div className="grid gap-2 sm:grid-cols-2">
        {EXAMPLES.map((ex) => (
          <button
            key={ex}
            onClick={() => onPick(ex)}
            className="group flex items-center justify-between gap-2 rounded-xl border border-brand-100 bg-brand-50/60 px-3.5 py-3 text-left text-sm text-ink transition hover:border-brand-300 hover:bg-brand-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
          >
            {ex}
            <span aria-hidden className="text-brand-600 transition group-hover:translate-x-0.5">
              →
            </span>
          </button>
        ))}
      </div>
    </div>
  )
}
