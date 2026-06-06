<template>
  <div class="risk-map">
    <div class="map-head">
      <span>关键节点风险分布</span>
      <small>{{ nodes.length }} 个节点</small>
    </div>
    <svg viewBox="0 0 680 360" role="img" aria-label="关键节点风险分布散点图">
      <rect x="0" y="0" width="680" height="360" rx="8" class="map-bg" />
      <g class="grid-lines">
        <line v-for="x in [80, 200, 320, 440, 560]" :key="`x-${x}`" :x1="x" y1="28" :x2="x" y2="332" />
        <line v-for="y in [80, 160, 240, 320]" :key="`y-${y}`" x1="36" :y1="y" x2="644" :y2="y" />
      </g>
      <circle
        v-for="node in points"
        :key="node.node_id"
        :cx="node.cx"
        :cy="node.cy"
        :r="node.radius"
        :class="['risk-dot', node.gradeClass]"
      >
        <title>{{ node.node_id }} 风险 {{ node.scoreText }}</title>
      </circle>
    </svg>
    <div class="map-legend">
      <span><i class="legend green"></i>正常</span>
      <span><i class="legend yellow"></i>关注</span>
      <span><i class="legend orange"></i>预警</span>
      <span><i class="legend red"></i>高风险</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { OverflowRiskAssessment } from "../types";
import { fmt, gradeClass } from "../utils";

const props = defineProps<{
  nodes: OverflowRiskAssessment[];
}>();

const points = computed(() => {
  const valid = props.nodes.filter(
    (node) => Number.isFinite(Number(node.x_coord)) && Number.isFinite(Number(node.y_coord)),
  );
  const xs = valid.map((node) => Number(node.x_coord));
  const ys = valid.map((node) => Number(node.y_coord));
  const minX = Math.min(...xs, 0);
  const maxX = Math.max(...xs, 1);
  const minY = Math.min(...ys, 0);
  const maxY = Math.max(...ys, 1);
  const xRange = maxX - minX || 1;
  const yRange = maxY - minY || 1;
  return valid.map((node) => {
    const score = Number(node.overflow_risk_score ?? 0);
    return {
      node_id: node.node_id,
      cx: 44 + ((Number(node.x_coord) - minX) / xRange) * 592,
      cy: 328 - ((Number(node.y_coord) - minY) / yRange) * 292,
      radius: 4 + Math.min(10, score * 12),
      gradeClass: gradeClass(node.risk_grade),
      scoreText: fmt(score, 2),
    };
  });
});
</script>
