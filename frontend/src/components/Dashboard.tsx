import { useEffect, useState } from 'react'
import type { StackCard } from '../api'
import { StackTile } from './StackTile'

type Props = { stacks: StackCard[] | null; error: string | null; onRetry: () => void }

export function Dashboard({ stacks, error, onRetry }: Props) {
  // The free-tier server sleeps when idle, so the first load can take a minute: tell people instead of leaving a blank page.
  const [slow, setSlow] = useState(false)
  useEffect(() => {
    if (stacks || error) return
    const t = setTimeout(() => setSlow(true), 5000)
    return () => clearTimeout(t)
  }, [stacks, error])

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold text-slate-900">Healthcheck Report Q&amp;A</h1>
        <p className="mt-1 max-w-2xl text-sm text-slate-600">
          Pick a stack to ask questions about its audit results: failed checks, priorities, and how to fix them. Each
          chat covers the one stack you choose. This demo runs on synthetic mock data.
        </p>
      </header>

      {error ? (
        <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          <p>{error}</p>
          <button onClick={onRetry} className="mt-2 rounded-md bg-red-700 px-3 py-1.5 text-white hover:bg-red-800">
            Try again
          </button>
        </div>
      ) : !stacks ? (
        <div aria-busy="true">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[0, 1, 2].map((i) => (
              <div key={i} className="h-44 animate-pulse rounded-xl border border-slate-200 bg-slate-100" />
            ))}
          </div>
          {slow && (
            <p className="mt-4 text-sm text-slate-500">
              Waking up the demo server… the first load after a quiet period can take up to a minute.
            </p>
          )}
        </div>
      ) : stacks.length === 0 ? (
        <p className="rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-600">
          No stacks have been loaded yet.
        </p>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {stacks.map((s) => (
            <StackTile key={s.id} stack={s} />
          ))}
        </div>
      )}
    </div>
  )
}
