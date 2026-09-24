<script setup>
import { ref } from 'vue'
import { session } from '../state/session'

const traitInput = ref('')

function addTrait() {
  const value = traitInput.value.trim()
  if (value && !session.desiredTraits.includes(value)) session.desiredTraits.push(value)
  traitInput.value = ''
}
</script>

<template>
  <div class="talent-settings">
    <div class="talent-mode-options" role="group" aria-label="人才能力分析模式">
      <label><input v-model="session.talentMode" type="radio" value="auto" /> AI 自动发现</label>
      <label><input v-model="session.talentMode" type="radio" value="specified" /> HR 指定人才像</label>
    </div>
    <div v-if="session.talentMode === 'specified'" class="trait-editor">
      <label for="talent-trait-input">指定人才特征</label>
      <div class="trait-editor__input">
        <input id="talent-trait-input" v-model="traitInput" class="text-input" type="text" placeholder="例如：认真、学习快" @keydown.enter.prevent="addTrait" />
        <button class="button button--secondary button--small" type="button" :disabled="!traitInput.trim()" @click="addTrait">添加</button>
      </div>
      <div v-if="session.desiredTraits.length" class="trait-chips">
        <button v-for="trait in session.desiredTraits" :key="trait" type="button" :aria-label="`移除 ${trait}`" @click="session.desiredTraits.splice(session.desiredTraits.indexOf(trait), 1)">
          {{ trait }} ×
        </button>
      </div>
      <small v-else>至少添加一项后才能分析。</small>
    </div>
  </div>
</template>
