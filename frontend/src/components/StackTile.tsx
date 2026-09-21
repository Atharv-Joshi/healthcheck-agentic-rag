import type { StackCard } from '../api'
import { formatDate, formatNumber } from '../format'

export function StackTile({ stack }: { stack: StackCard }) {
  const { total, passed, failed, skipped } = stack.checks
  const pct = (n: number) => (total ? `${(n / total) * 100}%` : '0%')
  return (
    <a
      href={`#/stack/${stack.id}`}
      className="group flex flex-col gap-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-slate-400 hover:shadow-md focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-500"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="font-semibold text-slate-900">{stack.name}</h2>
          <p className="text-xs text-slate-500">Audited {formatDate(stack.run_date)}</p>
        </div>
        {stack.actions_required > 0 && (
          <span className="shrink-0 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
            {stack.actions_required} action{stack.actions_required === 1 ? '' : 's'} required
          </span>
        )}
      </div>

      <dl className="grid grid-cols-2 gap-3 text-sm">
        <div>
          <dt className="text-xs text-slate-500">Entries</dt>
          <dd className="font-medium text-slate-900">{formatNumber(stack.entries_count)}</dd>
        </div>
        <div>
          <dt className="text-xs text-slate-500">Assets</dt>
          <dd className="font-medium text-slate-900">{formatNumber(stack.assets_count)}</dd>
        </div>
      </dl>

      {total > 0 && (
        <div>
          <div
            role="img"
            aria-label={`${passed} passed, ${failed} failed, ${skipped} skipped of ${total} checks`}
            className="flex h-2 overflow-hidden rounded-full bg-slate-100"
          >
            <div className="bg-emerald-500" style={{ width: pct(passed) }} />
            <div className="bg-rose-500" style={{ width: pct(failed) }} />
            <div className="bg-slate-300" style={{ width: pct(skipped) }} />
          </div>
          <p className="mt-1.5 text-xs text-slate-500">
            {passed} passed · {failed} failed · {skipped} skipped
          </p>
        </div>
      )}

      <span className="mt-auto text-sm font-medium text-slate-700 group-hover:underline">Ask about this stack →</span>
    </a>
  )
}
