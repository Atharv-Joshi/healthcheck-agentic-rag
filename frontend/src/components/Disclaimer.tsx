export function Disclaimer({ className = '' }: { className?: string }) {
  return (
    <p className={`text-xs text-ink-muted ${className}`}>
      Independent personal project on synthetic data. Not affiliated with or endorsed by Contentstack.
    </p>
  )
}
