import test from 'node:test'
import assert from 'node:assert/strict'

import {
  groupCandidateFolderFiles,
  prepareCandidateFolderUpload,
} from '../src/services/folderResumeUpload.js'

function fakeFile(path, contents = path) {
  return {
    name: path.split('/').at(-1),
    webkitRelativePath: path,
    contents,
    size: contents.length,
  }
}

function createFakeFile(parts, name, options) {
  return { name, parts, type: options.type, size: parts[0].length }
}

test('one batch root groups its direct child folders as candidates', () => {
  const groups = groupCandidateFolderFiles([
    fakeFile('Batch/Alice/resume.pdf'),
    fakeFile('Batch/Bob/resume.pdf'),
  ])

  assert.deepEqual(groups.map((group) => group.name), ['Alice', 'Bob'])
  assert.deepEqual(groups.map((group) => group.pdfFiles.map((file) => file.name)), [
    ['resume.pdf'],
    ['resume.pdf'],
  ])
})

test('one candidate with one PDF keeps the original file', async () => {
  const resume = fakeFile('Batch/Alice/resume.pdf')
  const result = await prepareCandidateFolderUpload([resume], { createFile: createFakeFile })

  assert.deepEqual(result.uploadFiles, [resume])
  assert.deepEqual(result.candidateNames, ['Alice'])
})

test('one candidate with multiple PDFs is merged in stable filename order', async () => {
  const mergeCalls = []
  const result = await prepareCandidateFolderUpload([
    fakeFile('Batch/Alice/z.pdf'),
    fakeFile('Batch/Alice/a.pdf'),
  ], {
    mergeFiles: async (files) => {
      mergeCalls.push(files.map((file) => file.name))
      return new Uint8Array([1, 2, 3])
    },
    createFile: createFakeFile,
  })

  assert.deepEqual(mergeCalls, [['a.pdf', 'z.pdf']])
  assert.equal(result.uploadFiles[0].name, 'Alice.pdf')
})

test('direct PDFs are merged while PDFs in deeper subdirectories are ignored', async () => {
  const mergeCalls = []
  await prepareCandidateFolderUpload([
    fakeFile('Batch/Alice/resume_2.pdf'),
    fakeFile('Batch/Alice/attachments/recommendation.pdf'),
    fakeFile('Batch/Alice/resume_1.pdf'),
  ], {
    mergeFiles: async (files) => {
      mergeCalls.push(files.map((file) => file.name))
      return new Uint8Array([1, 2, 3])
    },
    createFile: createFakeFile,
  })

  assert.deepEqual(mergeCalls, [['resume_1.pdf', 'resume_2.pdf']])
})

test('PDF files directly inside the batch root are ignored', async () => {
  const resume = fakeFile('Batch/Alice/resume.pdf')
  const result = await prepareCandidateFolderUpload([
    fakeFile('Batch/memo.pdf'),
    resume,
  ], { createFile: createFakeFile })

  assert.deepEqual(result.uploadFiles, [resume])
  assert.deepEqual(result.candidateNames, ['Alice'])
})

test('non-PDF files are ignored', () => {
  const groups = groupCandidateFolderFiles([
    fakeFile('Batch/readme.txt'),
    fakeFile('Batch/Alice/resume.pdf'),
    fakeFile('Batch/Alice/photo.jpg'),
    fakeFile('Batch/Alice/notes.docx'),
  ])

  assert.deepEqual(groups[0].pdfFiles.map((file) => file.name), ['resume.pdf'])
})

test('a candidate without a root PDF is skipped without failing the batch', async () => {
  const bobResume = fakeFile('Batch/Bob/resume.pdf')
  const result = await prepareCandidateFolderUpload([
    fakeFile('Batch/Alice/notes.txt'),
    fakeFile('Batch/Alice/archive/old.pdf'),
    bobResume,
  ], { createFile: createFakeFile })

  assert.deepEqual(result.uploadFiles, [bobResume])
  assert.deepEqual(result.candidateNames, ['Bob'])
  assert.deepEqual(result.skippedCandidateNames, ['Alice'])
})

test('files from multiple batch roots are rejected', () => {
  assert.throws(() => groupCandidateFolderFiles([
    fakeFile('Batch-A/Alice/resume.pdf'),
    fakeFile('Batch-B/Bob/resume.pdf'),
  ]), /Only one batch root folder/)
})

test('ordinary single PDF inputs remain outside folder grouping and merging', async () => {
  let mergeCalled = false
  const ordinaryPdf = { name: 'resume.pdf', webkitRelativePath: '' }
  const result = await prepareCandidateFolderUpload([ordinaryPdf], {
    mergeFiles: async () => { mergeCalled = true },
    createFile: createFakeFile,
  })

  assert.deepEqual(result.uploadFiles, [])
  assert.equal(mergeCalled, false)
})
