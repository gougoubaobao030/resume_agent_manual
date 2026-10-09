<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, shallowRef } from 'vue'
import { useI18n } from 'vue-i18n'

import { mergePdfFiles, PdfMergeReadError } from '../services/pdfMerge'

const { t } = useI18n()

const directoryHandle = shallowRef(null)
const pdfFiles = shallowRef([])
const selectedFiles = shallowRef([])
const outputFilename = ref('merge_resume.pdf')
const status = ref('idle')
const message = ref('')
const isExpanded = ref(false)
const isDragging = ref(false)
const toolElement = ref(null)
const position = ref(null)

let dragState = null

const isSupported = typeof window !== 'undefined' && 'showDirectoryPicker' in window
const isBusy = computed(() => status.value === 'loading')
const selectedNames = computed(() => new Set(selectedFiles.value.map((file) => file.name)))
const toolStyle = computed(() => position.value
  ? { left: position.value.left + 'px', top: position.value.top + 'px', right: 'auto', bottom: 'auto' }
  : undefined)

function clamp(value, minimum, maximum) {
  return Math.min(Math.max(value, minimum), maximum)
}

function keepInViewport() {
  if (!position.value || !toolElement.value) return

  const edge = 8
  const rect = toolElement.value.getBoundingClientRect()
  position.value = {
    left: clamp(rect.left, edge, Math.max(edge, window.innerWidth - rect.width - edge)),
    top: clamp(rect.top, edge, Math.max(edge, window.innerHeight - rect.height - edge)),
  }
}

async function toggleExpanded() {
  isExpanded.value = !isExpanded.value
  await nextTick()
  keepInViewport()
}

function handleDragStart(event) {
  if (event.button !== 0 || event.target.closest('button') || !toolElement.value) return

  const rect = toolElement.value.getBoundingClientRect()
  dragState = {
    pointerId: event.pointerId,
    startX: event.clientX,
    startY: event.clientY,
    startLeft: rect.left,
    startTop: rect.top,
  }
  position.value = { left: rect.left, top: rect.top }
  isDragging.value = true
  event.currentTarget.setPointerCapture(event.pointerId)
  event.preventDefault()
}

function handleDragMove(event) {
  if (!dragState || event.pointerId !== dragState.pointerId || !toolElement.value) return

  const edge = 8
  const rect = toolElement.value.getBoundingClientRect()
  const left = dragState.startLeft + event.clientX - dragState.startX
  const top = dragState.startTop + event.clientY - dragState.startY
  position.value = {
    left: clamp(left, edge, Math.max(edge, window.innerWidth - rect.width - edge)),
    top: clamp(top, edge, Math.max(edge, window.innerHeight - rect.height - edge)),
  }
  event.preventDefault()
}

function handleDragEnd(event) {
  if (!dragState || event.pointerId !== dragState.pointerId) return
  if (event.currentTarget.hasPointerCapture(event.pointerId)) {
    event.currentTarget.releasePointerCapture(event.pointerId)
  }
  dragState = null
  isDragging.value = false
}

onMounted(() => window.addEventListener('resize', keepInViewport))
onBeforeUnmount(() => window.removeEventListener('resize', keepInViewport))

function normalizeOutputFilename(value) {
  let filename = value.trim() || 'merge_resume.pdf'
  filename = filename.replace(/[\\/:*?"<>|]/g, '_')
  if (!filename.toLowerCase().endsWith('.pdf')) filename += '.pdf'
  if (!filename.startsWith('merge_')) filename = 'merge_' + filename
  return filename === 'merge_.pdf' ? 'merge_resume.pdf' : filename
}

async function ensureWritePermission(handle) {
  const options = { mode: 'readwrite' }
  if (!handle.queryPermission || await handle.queryPermission(options) === 'granted') return true
  return await handle.requestPermission(options) === 'granted'
}

async function refreshDirectory({ clearSelection = false } = {}) {
  if (!directoryHandle.value) return

  const files = []
  for await (const [name, handle] of directoryHandle.value.entries()) {
    if (handle.kind !== 'file' || !name.toLowerCase().endsWith('.pdf')) continue
    const file = await handle.getFile()
    files.push({ name, handle, size: file.size, lastModified: file.lastModified })
  }
  pdfFiles.value = files.sort((left, right) => left.name.localeCompare(right.name))
  if (clearSelection) selectedFiles.value = []
}

async function chooseDirectory() {
  if (!isSupported || isBusy.value) return

  try {
    const handle = await window.showDirectoryPicker({ mode: 'readwrite' })
    if (!await ensureWritePermission(handle)) {
      status.value = 'error'
      message.value = t('pdfMerge.messages.permissionDenied')
      return
    }
    directoryHandle.value = handle
    selectedFiles.value = []
    status.value = 'idle'
    message.value = ''
    await refreshDirectory()
  } catch (error) {
    if (error?.name === 'AbortError') return
    status.value = 'error'
    message.value = t('pdfMerge.messages.openFailed')
  }
}

function toggleFile(file, checked) {
  if (checked) {
    if (!selectedNames.value.has(file.name)) selectedFiles.value = [...selectedFiles.value, file]
  } else {
    selectedFiles.value = selectedFiles.value.filter((item) => item.name !== file.name)
  }
  status.value = 'idle'
  message.value = ''
}

function moveFile(index, offset) {
  const targetIndex = index + offset
  if (targetIndex < 0 || targetIndex >= selectedFiles.value.length) return
  const reordered = [...selectedFiles.value]
  const [file] = reordered.splice(index, 1)
  reordered.splice(targetIndex, 0, file)
  selectedFiles.value = reordered
}

async function outputExists(filename) {
  try {
    await directoryHandle.value.getFileHandle(filename)
    return true
  } catch (error) {
    if (error?.name === 'NotFoundError') return false
    throw error
  }
}

async function mergeSelectedFiles() {
  if (!directoryHandle.value) {
    status.value = 'error'
    message.value = t('pdfMerge.messages.folderRequired')
    return
  }
  if (selectedFiles.value.length < 2) {
    status.value = 'error'
    message.value = t('pdfMerge.messages.filesRequired')
    return
  }

  const filename = normalizeOutputFilename(outputFilename.value)
  outputFilename.value = filename
  status.value = 'loading'
  message.value = t('pdfMerge.messages.merging')

  let mergedBytes
  try {
    const files = []
    for (const item of selectedFiles.value) {
      try {
        files.push(await item.handle.getFile())
      } catch (error) {
        throw new PdfMergeReadError(item.name, error)
      }
    }
    mergedBytes = await mergePdfFiles(files)
  } catch (error) {
    status.value = 'error'
    message.value = error instanceof PdfMergeReadError
      ? t('pdfMerge.messages.readFailed', { filename: error.filename })
      : t('pdfMerge.messages.mergeFailed')
    return
  }

  try {
    if (!await ensureWritePermission(directoryHandle.value)) throw new Error('Permission denied')
    if (await outputExists(filename)
      && !window.confirm(t('pdfMerge.messages.overwriteConfirm', { filename }))) {
      status.value = 'idle'
      message.value = ''
      return
    }

    const outputHandle = await directoryHandle.value.getFileHandle(filename, { create: true })
    const writable = await outputHandle.createWritable()
    await writable.write(mergedBytes)
    await writable.close()
  } catch (error) {
    status.value = 'error'
    message.value = t('pdfMerge.messages.writeFailed')
    return
  }

  await refreshDirectory({ clearSelection: true })
  outputFilename.value = 'merge_resume.pdf'
  status.value = 'success'
  message.value = t('pdfMerge.messages.success', { filename })
}
</script>

<template>
  <aside
    ref="toolElement"
    class="pdf-merge-tool"
    :class="{ 'pdf-merge-tool--expanded': isExpanded, 'pdf-merge-tool--dragging': isDragging }"
    :style="toolStyle"
    aria-labelledby="pdf-merge-title"
  >
    <div
      class="pdf-merge-tool__header"
      @pointerdown="handleDragStart"
      @pointermove="handleDragMove"
      @pointerup="handleDragEnd"
      @pointercancel="handleDragEnd"
    >
      <svg class="pdf-merge-tool__icon" viewBox="0 0 24 24" aria-hidden="true">
        <path d="M7 3.5h7l3 3V20.5H7zM14 3.5v3h3M9.5 11h5M9.5 14h5M9.5 17h3" />
      </svg>
      <span id="pdf-merge-title">{{ t('pdfMerge.title') }}</span>
      <span v-if="selectedFiles.length" class="pdf-merge-tool__count">{{ selectedFiles.length }}</span>
      <button
        class="pdf-merge-tool__window-control"
        type="button"
        :aria-expanded="isExpanded"
        :aria-label="t(isExpanded ? 'pdfMerge.actions.collapse' : 'pdfMerge.actions.expand')"
        @pointerdown.stop
        @click="toggleExpanded"
      >
        <span aria-hidden="true">{{ isExpanded ? '−' : '↗' }}</span>
      </button>
    </div>

    <div v-if="isExpanded" class="pdf-merge-tool__body">
      <p class="pdf-merge-tool__description">{{ t('pdfMerge.description') }}</p>
      <button class="button button--secondary button--small pdf-merge-tool__folder-button" type="button" :disabled="!isSupported || isBusy" @click="chooseDirectory">
        {{ t('pdfMerge.actions.selectFolder') }}
      </button>

      <div v-if="!isSupported" class="inline-message inline-message--error" role="alert">
        {{ t('pdfMerge.messages.unsupported') }}
      </div>

      <template v-if="directoryHandle">
        <p class="pdf-merge-tool__folder">
          <strong>{{ t('pdfMerge.currentFolder') }}</strong>
          <span>{{ directoryHandle.name }}</span>
          <small>{{ t('pdfMerge.folderPathNote') }}</small>
        </p>

        <div class="pdf-merge-grid">
          <div class="pdf-merge-files">
            <strong>{{ t('pdfMerge.availableFiles') }}</strong>
            <p v-if="!pdfFiles.length" class="helper-text">{{ t('pdfMerge.noFiles') }}</p>
            <label v-for="file in pdfFiles" :key="file.name + '-' + file.lastModified" class="pdf-merge-file">
              <input
                type="checkbox"
                :checked="selectedNames.has(file.name)"
                :disabled="isBusy"
                @change="toggleFile(file, $event.target.checked)"
              />
              <span>{{ file.name }}</span>
            </label>
          </div>

          <div class="pdf-merge-queue">
            <strong>{{ t('pdfMerge.selectedCount', { count: selectedFiles.length }) }}</strong>
            <ol v-if="selectedFiles.length">
              <li v-for="(file, index) in selectedFiles" :key="file.name">
                <span>{{ file.name }}</span>
                <span class="pdf-merge-queue__actions">
                  <button type="button" :disabled="isBusy || index === 0" :aria-label="t('pdfMerge.actions.moveUpLabel', { filename: file.name })" @click="moveFile(index, -1)">↑</button>
                  <button type="button" :disabled="isBusy || index === selectedFiles.length - 1" :aria-label="t('pdfMerge.actions.moveDownLabel', { filename: file.name })" @click="moveFile(index, 1)">↓</button>
                </span>
              </li>
            </ol>
            <p v-else class="helper-text">{{ t('pdfMerge.selectHint') }}</p>
          </div>
        </div>

        <div class="pdf-merge-tool__footer">
          <label class="field pdf-merge-tool__filename">
            <span>{{ t('pdfMerge.outputFilename') }}</span>
            <input v-model="outputFilename" class="text-input" type="text" :disabled="isBusy" @blur="outputFilename = normalizeOutputFilename(outputFilename)" />
          </label>
          <button class="button button--primary button--small" type="button" :disabled="isBusy" @click="mergeSelectedFiles">
            {{ t(isBusy ? 'pdfMerge.actions.merging' : 'pdfMerge.actions.merge') }}
          </button>
        </div>
      </template>

      <div v-if="message" class="inline-message" :class="'inline-message--' + status" :role="status === 'error' ? 'alert' : 'status'">
        <span v-if="isBusy" class="loading-spinner" aria-hidden="true"></span>
        <span>{{ message }}</span>
      </div>
    </div>
  </aside>
</template>
