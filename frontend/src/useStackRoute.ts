import { useEffect, useState } from 'react'

/** Minimal hash routing: "#/" is the dashboard, "#/stack/3" is stack 3's chat. Gives working back/forward buttons and
 *  shareable links without a router dependency. */
function parse(hash: string): number | null {
  const m = /^#\/stack\/(\d+)$/.exec(hash)
  return m ? Number(m[1]) : null
}

export function useStackRoute(): number | null {
  const [stackId, setStackId] = useState<number | null>(() => parse(window.location.hash))
  useEffect(() => {
    const onChange = () => setStackId(parse(window.location.hash))
    window.addEventListener('hashchange', onChange)
    return () => window.removeEventListener('hashchange', onChange)
  }, [])
  return stackId
}
