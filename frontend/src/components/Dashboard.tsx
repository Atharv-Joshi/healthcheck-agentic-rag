import { useEffect, useState } from 'react'
import type { StackCard } from '../api'
import { formatNumber } from '../format'
import { Disclaimer } from './Disclaimer'
import { Logo } from './Logo'
import { StackTile } from './StackTile'

type Props = { stacks: StackCard[] | null; error: string | null; onRetry: () => void }

function Stat({ value, label }: { value: string; label: string }) {
  return (
    <div className="rounded-xl border border-brand-100 bg-white/70 px-4 py-2.5 backdrop-blur">
      <div className="text-lg font-semibold tabular-nums text-ink">{value}</div>
      <div className="text-xs text-ink-muted">{label}</div>
    </div>
  )
}

export function Dashboard({ stacks, error, onRetry }: Props) {
  // The free-tier server sleeps when idle, so the first load can take a minute: tell people instead of leaving a blank page.
  const [slow, setSlow] = useState(false)
  useEffect(() => {
    if (stacks || error) return
    const t = setTimeout(() => setSlow(true), 5000)
    return () => clearTimeout(t)
  }, [stacks, error])

  const totalActions = stacks?.reduce((n, s) => n + s.actions_required, 0) ?? 0
  const totalEntries = stacks?.reduce((n, s) => n + s.entries_count, 0) ?? 0

  return (
    <div className="mx-auto max-w-5xl px-4 pb-10 pt-6">
      <nav className="mb-10 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <Logo />
          <span className="font-semibold tracking-tight text-ink">Healthcheck Q&amp;A</span>
        </div>
        <span className="rounded-full border border-brand-200 bg-brand-50 px-3 py-1 text-xs font-medium text-brand-800">
          Demo · synthetic data
        </span>
      </nav>

      <header className="mb-8">
        <h1 className="max-w-2xl text-3xl font-semibold tracking-tight text-ink sm:text-4xl">
          Ask your audit report <span className="text-brand-600">anything</span>
        </h1>
        <p className="mt-3 max-w-2xl text-base text-ink-muted">
          Pick a stack to chat about its Healthcheck results: what failed, what to fix first, and why it matters. Each
          chat covers the one stack you choose.
        </p>
        {stacks && stacks.length > 0 && (
          <div className="mt-5 flex flex-wrap gap-3">
            <Stat value={String(stacks.length)} label={stacks.length === 1 ? 'stack' : 'stacks'} />
            <Stat value={formatNumber(totalEntries)} label="entries audited" />
            <Stat value={formatNumber(totalActions)} label="actions required" />
          </div>
        )}
      </header>

      {error ? (
        <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
          <p>{error}</p>
          <button
            onClick={onRetry}
            className="mt-3 rounded-lg bg-brand-600 px-3.5 py-1.5 font-medium text-white hover:bg-brand-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2"
          >
            Try again
          </button>
        </div>
      ) : !stacks ? (
        <div aria-busy="true">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[0, 1, 2].map((i) => (
              <div key={i} className="h-52 animate-pulse rounded-2xl border border-brand-100 bg-brand-50" />
            ))}
          </div>
          {slow && (
            <p className="mt-4 text-sm text-ink-muted">
              Waking up the demo server… the first load after a quiet period can take up to a minute.
            </p>
          )}
        </div>
      ) : stacks.length === 0 ? (
        <p className="rounded-xl border border-brand-100 bg-white p-4 text-sm text-ink-muted">
          No stacks have been loaded yet.
        </p>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {stacks.map((s) => (
            <StackTile key={s.id} stack={s} />
          ))}
        </div>
      )}

      <Disclaimer className="mt-10 text-center" />
    </div>
  )
}
