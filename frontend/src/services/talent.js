import { discoverTalent, getFriendlyApiError } from './api'
import { session, setTalentError, setTalentLoading, setTalentResult } from '../state/session'

export const talentLevelLabels = {
  high: '高', medium_high: '中高', medium: '中', medium_low: '中低', low: '低',
}

export function talentLevelLabel(level) {
  return talentLevelLabels[level] || '—'
}

export async function analyzeTalent(candidate, mode = session.talentMode, desiredTraits = session.desiredTraits) {
  if (!candidate?.id || session.talentStatuses[candidate.id] === 'loading') return
  if (mode === 'specified' && !desiredTraits.length) return

  setTalentLoading(candidate.id)
  try {
    const result = await discoverTalent(candidate, mode, [...desiredTraits])
    setTalentResult(candidate.id, result)
  } catch (error) {
    setTalentError(candidate.id, getFriendlyApiError(error, '人才能力分析'))
  }
}
