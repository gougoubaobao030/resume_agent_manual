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

test('one candidate with one PDF keeps the original file', async () => {
  const resume = fakeFile('Alice/resume.pdf')
  const result = await prepareCandidateFolderUpload([resume], { createFile: createFakeFile })

  assert.deepEqual(result.uploadFiles, [resume])
  assert.deepEqual(result.candidateNames, ['Alice'])
})

test('one candidate with multiple PDFs is merged in stable filename order', async () => {
  const mergeCalls = []
  const result = await prepareCandidateFolderUpload([
    fakeFile('Alice/z.pdf'),
    fakeFile('Alice/a.pdf'),
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
    fakeFile('Alice/resume_2.pdf'),
    fakeFile('Alice/attachments/recommendation.pdf'),
    fakeFile('Alice/resume_1.pdf'),
  ], {
    mergeFiles: async (files) => {
      mergeCalls.push(files.map((file) => file.name))
      return new Uint8Array([1, 2, 3])
    },
    createFile: createFakeFile,
  })

  assert.deepEqual(mergeCalls, [['resume_1.pdf', 'resume_2.pdf']])
})

test('non-PDF files are ignored', () => {
  const groups = groupCandidateFolderFiles([
    fakeFile('Alice/resume.pdf'),
    fakeFile('Alice/photo.jpg'),
    fakeFile('Alice/notes.docx'),
  ])

  assert.deepEqual(groups[0].pdfFiles.map((file) => file.name), ['resume.pdf'])
})

test('a candidate without a root PDF is skipped without failing the batch', async () => {
  const result = await prepareCandidateFolderUpload([
    fakeFile('Alice/notes.txt'),
    fakeFile('Alice/archive/old.pdf'),
  ], { createFile: createFakeFile })

  assert.deepEqual(result.uploadFiles, [])
  assert.deepEqual(result.candidateNames, [])
  assert.deepEqual(result.skippedCandidateNames, ['Alice'])
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
