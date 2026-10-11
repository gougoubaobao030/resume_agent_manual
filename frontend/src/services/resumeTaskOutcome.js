export function shouldStartCandidateAnalysis(item) {
  return item?.status === 'success'
    && Boolean(item.candidate?.id)
    && item.outcome !== 'already_linked'
}
