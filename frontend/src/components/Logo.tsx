/** The app's own mark (a health-pulse line on a rounded square). Deliberately generic: it is not any company's logo. */
export function Logo({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true" className="shrink-0">
      <rect width="32" height="32" rx="8" fill="#6d3fd0" />
      <path
        d="M6 17h5l3-7 4 12 3-7h5"
        fill="none"
        stroke="#fff"
        strokeWidth="2.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}
