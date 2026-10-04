<script setup>
import { useRoute } from 'vue-router'
import AppLayout from './layouts/AppLayout.vue'
import { auth } from './state/auth'

const route = useRoute()
</script>

<template>
  <RouterView v-if="!auth.initialized || route.meta.public || !auth.user" />
  <AppLayout v-else />
</template>
