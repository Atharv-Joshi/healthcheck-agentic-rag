// Stack-agnostic on purpose: every chat is already locked to one stack, so questions never need to name it.
const EXAMPLES = [
  'What are the top actions required?',
  'How many checks failed?',
  'List the failed Security checks',
  'Why does two-factor authentication matter?',
]

export function ExampleQuestions({ onPick }: { onPick: (q: string) => void }) {
  return (
    <div className="space-y-2">
      <p className="text-sm text-slate-500">Try a question:</p>
      {EXAMPLES.map((ex) => (
        <button
          key={ex}
          onClick={() => onPick(ex)}
          className="block w-full rounded-md border border-slate-200 px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-50"
        >
          {ex}
        </button>
      ))}
    </div>
  )
}
