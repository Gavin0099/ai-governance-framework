import { describe, expect, it } from 'vitest'
import { normalizeProbeLabel } from '../validator-probe-fixture'

describe('validator probe fixture', () => {
  it('normalizes a visible label', () => {
    expect(normalizeProbeLabel('  Probe  ')).toBe('probe')
  })

  it('classifies a blank label', () => {
    expect(normalizeProbeLabel('   ')).toBe('missing')
  })
})
