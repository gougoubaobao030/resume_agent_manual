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

const potentialDimensionLabels = {
  learning_transfer: 'common.potentialDimensions.learningTransfer',
  analytical_problem_solving: 'common.potentialDimensions.analyticalProblemSolving',
  initiative_drive: 'common.potentialDimensions.initiativeDrive',
  persistence_execution: 'common.potentialDimensions.persistenceExecution',
  adaptability_resilience: 'common.potentialDimensions.adaptabilityResilience',
  reflection_growth: 'common.potentialDimensions.reflectionGrowth',
  social_learning_collaboration: 'common.potentialDimensions.socialLearningCollaboration',
}

export function talentLevelLabel(level) {
  const labelKey = talentLevelLabels[level]
  return labelKey ? i18n.global.t(labelKey) : '—'
}

export function talentAbilityLabel(abilityName) {
  const labelKey = potentialDimensionLabels[abilityName]
  return labelKey ? i18n.global.t(labelKey) : abilityName
}

export function talentEvidenceStatus(item) {
  if (['verified', 'needs_review', 'insufficient_evidence'].includes(item?.evidence_status)) {
    return item.evidence_status
  }
  if (item?.evidence_validation_issues?.length) return 'needs_review'
  if (item?.evidence?.length) return 'verified'
  return 'insufficient_evidence'
}

export function isPotentialSignalResult(result) {
  return Boolean(result?.abilities?.some((item) => item.evidence_status != null))
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
