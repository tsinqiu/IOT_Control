<template>
  <span :class="['status-pill', gradeClass(grade)]">{{ gradeLabel(grade) }}</span>
</template>

<script setup lang="ts">
import type { Grade } from "../types";
import { gradeClass, gradeLabel } from "../utils";

defineProps<{
  grade: Grade;
}>();
</script>
