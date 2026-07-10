import type { DraftSnapshot } from '../types'
import { normalizeDraftSnapshot } from './draftSchema'

export function encodeDraft(snapshot: DraftSnapshot): string {
  const bytes = new TextEncoder().encode(JSON.stringify(snapshot))
  let binary = ''
  for (const byte of bytes) binary += String.fromCharCode(byte)
  return btoa(binary).replaceAll('+', '-').replaceAll('/', '_').replaceAll('=', '')
}

export function decodeDraft(encoded: string): DraftSnapshot | null {
  try {
    const padded = encoded.replaceAll('-', '+').replaceAll('_', '/') + '='.repeat((4 - encoded.length % 4) % 4)
    const binary = atob(padded)
    const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0))
    const parsed: unknown = JSON.parse(new TextDecoder().decode(bytes))
    return normalizeDraftSnapshot(parsed)
  } catch {
    return null
  }
}
