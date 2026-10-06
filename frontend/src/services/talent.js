import { discoverTalent, getFriendlyApiError } from './api'
import { i18n } from '../i18n'
import { session, setTalentError, setTalentLoading, setTalentResult } from '../state/session'

export const talentLevelLabels = {
  high: 'common.talent.level.high',
  medium_high: 'common.talent.level.mediumHigh',
  medium: 'common.talent.level.medium',
  medium_low: 'common.talent.level.mediumLow',
  low: 'common.talent.level.low',
}

export function talentLevelLabel(level) {
  const labelKey = talentLevelLabels[level]
  return labelKey ? i18n.global.t(labelKey) : '—'
}

export async function analyzeTalent(
  candidate,
  mode = session.talentMode,
  desiredTraits = session.desiredTraits,
  analysisLanguage,
) {
  if (!candidate?.id || session.talentStatuses[candidate.id]?.[mode] === 'loading') return
  if (mode === 'specified' && !desiredTraits.length) return

  setTalentLoading(candidate.id, mode)
  try {
    const result = await discoverTalent(candidate.id, mode, [...desiredTraits], analysisLanguage)
    setTalentResult(candidate.id, mode, result)
  } catch (error) {
    setTalentError(
      candidate.id,
      mode,
      getFriendlyApiError(error, i18n.global.t('common.operations.talent')),
    )
  }
}
