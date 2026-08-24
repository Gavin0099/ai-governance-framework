export function normalizeProbeLabel(value: string): string {
  const normalized = value.trim().toLowerCase()
  return normalized.length === 0 ? 'missing' : normalized
}
