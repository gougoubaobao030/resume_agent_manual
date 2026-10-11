import test from 'node:test'
import assert from 'node:assert/strict'

import { shouldStartCandidateAnalysis } from '../src/services/resumeTaskOutcome.js'


test('already_linked candidates do not start scoring or talent', () => {
  assert.equal(shouldStartCandidateAnalysis({
    status: 'success',
    outcome: 'already_linked',
    candidate: { id: 'candidate-existing' },
  }), false)
})


test('created and reused candidates continue to scoring and talent', () => {
  for (const outcome of ['created', 'reused']) {
    assert.equal(shouldStartCandidateAnalysis({
      status: 'success',
      outcome,
      candidate: { id: `candidate-${outcome}` },
    }), true)
  }
})
