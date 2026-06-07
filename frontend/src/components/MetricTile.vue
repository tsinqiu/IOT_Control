<template>
  <section class="metric-tile">
    <div class="metric-head">
      <span>{{ title }}</span>
      <StatusPill :grade="grade" />
    </div>
    <small v-if="scopeLabel" class="metric-scope">{{ scopeLabel }}</small>
    <strong>{{ value }}</strong>
    <p>{{ detail }}</p>
  </section>
</template>

<script setup lang="ts">
import type { Grade } from "../types";
import StatusPill from "./StatusPill.vue";

defineProps<{
  title: string;
  value: string | number;
  detail: string;
  grade: Grade;
  scopeLabel?: string;
}>();
</script>
