const EXAMPLES = [
  'What are the top 3 actions required for Globex Corporate Site?',
  'How many checks failed for Initech Support Portal?',
  'Why does two-factor authentication matter?',
  'Is SSO enabled for Acme Retail - Web, and why does it matter?',
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
