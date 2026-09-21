export const formatNumber = (n: number) => n.toLocaleString('en-US')

export function formatDate(isoDate: string): string {
  const d = new Date(`${isoDate}T00:00:00`)
  return Number.isNaN(d.getTime())
    ? isoDate
    : d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}
