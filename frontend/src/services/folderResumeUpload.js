import { mergePdfFiles } from './pdfMerge.js'

function stableNameSort(left, right) {
  return left.name.localeCompare(right.name)
}

export function groupCandidateFolderFiles(files) {
  const candidates = new Map()
  const batchRootNames = new Set()

  for (const file of Array.from(files ?? [])) {
    const parts = (file.webkitRelativePath ?? '').split('/').filter(Boolean)
    if (parts.length < 2) continue

    batchRootNames.add(parts[0])
    if (batchRootNames.size > 1) {
      throw new Error('Only one batch root folder can be selected at a time')
    }

    // Files directly inside the selected batch root are ignored. Each direct
    // child folder is a candidate, and only PDFs directly inside it are used.
    if (parts.length < 3) continue

    const candidateName = parts[1]
    if (!candidates.has(candidateName)) candidates.set(candidateName, [])

    if (parts.length === 3 && file.name.toLowerCase().endsWith('.pdf')) {
      candidates.get(candidateName).push(file)
    }
  }

  return [...candidates.entries()]
    .map(([name, pdfFiles]) => ({ name, pdfFiles: pdfFiles.sort(stableNameSort) }))
    .sort(stableNameSort)
}

export async function prepareCandidateFolderUpload(
  files,
  {
    mergeFiles = mergePdfFiles,
    createFile = (parts, name, options) => new File(parts, name, options),
  } = {},
) {
  const groups = groupCandidateFolderFiles(files)
  const uploadFiles = []
  const candidateNames = []
  const skippedCandidateNames = []

  for (const group of groups) {
    const ignoredDeepPdfFiles = Array.from(files ?? [])
      .filter((file) => {
        const parts = (file.webkitRelativePath ?? '').split('/').filter(Boolean)
        return parts[1] === group.name
          && parts.length > 3
          && file.name.toLowerCase().endsWith('.pdf')
      })
      .map((file) => file.webkitRelativePath)

    console.debug('[FolderResumeUpload] candidate PDF classification', {
      candidateName: group.name,
      directPdfFiles: group.pdfFiles.map((file) => file.name),
      ignoredDeepPdfFiles,
    })

    if (!group.pdfFiles.length) {
      skippedCandidateNames.push(group.name)
      continue
    }

    let uploadFile = group.pdfFiles[0]
    if (group.pdfFiles.length > 1) {
      console.debug('[FolderResumeUpload] before mergePdfFiles', {
        candidateName: group.name,
        fileCount: group.pdfFiles.length,
      })
      const mergedBytes = await mergeFiles(group.pdfFiles)
      uploadFile = createFile([mergedBytes], `${group.name}.pdf`, {
        type: 'application/pdf',
      })
      console.debug('[FolderResumeUpload] merged file created', {
        name: uploadFile.name,
        type: uploadFile.type,
        size: uploadFile.size,
        isNewFileObject: !group.pdfFiles.includes(uploadFile),
        isFileInstance: typeof File !== 'undefined' && uploadFile instanceof File,
      })
    }

    uploadFiles.push(uploadFile)
    candidateNames.push(group.name)
  }

  return { uploadFiles, candidateNames, skippedCandidateNames }
}
