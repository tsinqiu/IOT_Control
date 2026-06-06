<template>
  <div class="chart-block">
    <div class="chart-title">
      <span>{{ title }}</span>
      <small>{{ caption }}</small>
    </div>
    <div class="bar-list">
      <div v-for="item in normalizedItems" :key="item.label" class="bar-row">
        <span class="bar-label">{{ item.label }}</span>
        <div class="bar-track">
          <div class="bar-fill" :class="item.gradeClass" :style="{ width: `${item.width}%` }"></div>
        </div>
        <span class="bar-value">{{ item.display }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { Grade } from "../types";
import { fmt, gradeClass } from "../utils";

const props = defineProps<{
  title: string;
  caption: string;
  rows: Array<Record<string, unknown>>;
  labelKey: string;
  valueKey: string;
  gradeKey?: string;
  digits?: number;
  maxValue?: number;
  limit?: number;
}>();

const normalizedItems = computed(() => {
  const rows = props.rows
    .map((row) => ({
      label: String(row[props.labelKey] ?? "-"),
      value: Number(row[props.valueKey] ?? 0),
      grade: String(row[props.gradeKey ?? ""] ?? "green") as Grade,
    }))
    .filter((row) => Number.isFinite(row.value))
    .sort((a, b) => b.value - a.value)
    .slice(0, props.limit ?? 8);
  const max = props.maxValue ?? Math.max(...rows.map((row) => row.value), 1);
  return rows.map((row) => ({
    ...row,
    width: Math.max(3, Math.min(100, (row.value / max) * 100)),
    display: fmt(row.value, props.digits ?? 2),
    gradeClass: gradeClass(row.grade),
  }));
});
</script>
