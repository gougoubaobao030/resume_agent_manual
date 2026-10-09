export class PdfMergeReadError extends Error {
  constructor(filename, cause) {
    super('Unable to read PDF: ' + filename, { cause })
    this.name = 'PdfMergeReadError'
    this.filename = filename
  }
}

export async function mergePdfFiles(files) {
  const { PDFDocument } = await import('pdf-lib')
  const mergedDocument = await PDFDocument.create()

  for (const file of files) {
    try {
      const sourceDocument = await PDFDocument.load(await file.arrayBuffer())
      const pages = await mergedDocument.copyPages(sourceDocument, sourceDocument.getPageIndices())
      pages.forEach((page) => mergedDocument.addPage(page))
    } catch (error) {
      throw new PdfMergeReadError(file.name, error)
    }
  }

  return mergedDocument.save()
}
