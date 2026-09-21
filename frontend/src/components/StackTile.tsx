import type { StackCard } from '../api'
import { formatDate, formatNumber } from '../format'

const initials = (name: string) =>
  name
    .split(/\s+/)
    .filter((w) => /^[A-Za-z0-9]/.test(w))
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join('')

export function StackTile({ stack }: { stack: StackCard }) {
  const { total, passed, failed, skipped } = stack.checks
  const pct = (n: number) => (total ? `${(n / total) * 100}%` : '0%')
  return (
    <a
      href={`#/stack/${stack.id}`}
      className="group relative flex flex-col gap-4 overflow-hidden rounded-2xl border border-brand-100 bg-white p-5 shadow-sm shadow-brand-900/5 transition duration-200 hover:-translate-y-0.5 hover:border-brand-300 hover:shadow-lg hover:shadow-brand-900/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
    >
      <span aria-hidden className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-brand-300 via-brand-500 to-brand-600" />

      <div className="flex items-start gap-3">
        <span
          aria-hidden
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-sm font-semibold text-brand-700"
        >
          {initials(stack.name)}
        </span>
        <div className="min-w-0 flex-1">
          <h2 className="font-semibold leading-snug text-ink">{stack.name}</h2>
          <p className="text-xs text-ink-muted">Audited {formatDate(stack.run_date)}</p>
        </div>
      </div>

      <dl className="grid grid-cols-2 gap-2 text-sm">
        <div className="rounded-lg bg-canvas px-3 py-2">
          <dt className="text-xs text-ink-muted">Entries</dt>
          <dd className="font-semibold tabular-nums text-ink">{formatNumber(stack.entries_count)}</dd>
        </div>
        <div className="rounded-lg bg-canvas px-3 py-2">
          <dt className="text-xs text-ink-muted">Assets</dt>
          <dd className="font-semibold tabular-nums text-ink">{formatNumber(stack.assets_count)}</dd>
        </div>
      </dl>

      {total > 0 && (
        <div>
          <div
            role="img"
            aria-label={`${passed} passed, ${failed} failed, ${skipped} skipped of ${total} checks`}
            className="flex h-2 overflow-hidden rounded-full bg-brand-50"
          >
            <div className="bg-pass" style={{ width: pct(passed) }} />
            <div className="bg-fail" style={{ width: pct(failed) }} />
            <div className="bg-brand-200" style={{ width: pct(skipped) }} />
          </div>
          <p className="mt-1.5 text-xs text-ink-muted">
            <span className="font-medium text-pass-ink">{passed} passed</span> · {failed} failed · {skipped} skipped
          </p>
        </div>
      )}

      <div className="mt-auto flex items-center justify-between gap-2">
        {stack.actions_required > 0 ? (
          <span className="rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-medium text-amber-800">
            {stack.actions_required} action{stack.actions_required === 1 ? '' : 's'} required
          </span>
        ) : (
          <span className="rounded-full bg-pass-soft px-2.5 py-0.5 text-xs font-medium text-pass-ink">
            No actions required
          </span>
        )}
        <span className="text-sm font-medium text-brand-700">
          Open chat <span className="inline-block transition group-hover:translate-x-0.5">→</span>
        </span>
      </div>
    </a>
  )
}
