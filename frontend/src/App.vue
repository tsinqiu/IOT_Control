<template>
  <div class="app-shell">
    <aside class="sidebar">
      <div class="brand">
        <span class="brand-mark">IC</span>
        <div>
          <strong>IOT Control</strong>
          <small>现状评估</small>
        </div>
      </div>
      <nav>
        <button
          v-for="item in navItems"
          :key="item.key"
          :class="{ active: activeTab === item.key }"
          type="button"
          @click="activeTab = item.key"
        >
          <span class="nav-icon" aria-hidden="true">{{ item.icon }}</span>
          {{ item.label }}
        </button>
      </nav>
    </aside>

    <main>
      <header class="topbar">
        <div>
          <h1>管网液位与泵站现状评估</h1>
          <p>基于多指标归一化与规则加权的现状评估模型</p>
        </div>
        <div class="top-actions">
          <div class="range-control" aria-label="时间范围">
            <button
              v-for="item in rangeItems"
              :key="item.key"
              :class="{ active: selectedRange === item.key }"
              type="button"
              @click="setRange(item.key)"
            >
              {{ item.label }}
            </button>
          </div>
          <div class="timestamp">
            <span>评估窗口</span>
            <strong>{{ summary?.latest_timestamp ?? "-" }}</strong>
          </div>
        </div>
      </header>

      <div v-if="loading" class="state-box">正在读取第二部分评估结果...</div>
      <div v-else-if="error" class="state-box error">{{ error }}</div>

      <template v-else>
        <section v-show="activeTab === 'overview'" class="screen-grid">
          <MetricTile
            title="系统能耗"
            :grade="summary?.system_energy_grade ?? 'no_data'"
            :value="summary?.top_energy_pump || '-'"
            :detail="`红色 ${summary?.red_energy_count ?? 0} 台，橙色 ${summary?.orange_energy_count ?? 0} 台`"
          />
          <MetricTile
            title="设备安全"
            :grade="summary?.system_safety_grade ?? 'no_data'"
            :value="summary?.lowest_health_pump ?? '-'"
            :detail="`低健康泵 ${summary?.low_health_pump_count ?? 0} 台`"
          />
          <MetricTile
            title="漫溢风险"
            :grade="summary?.system_overflow_grade ?? 'no_data'"
            :value="summary?.highest_risk_node ?? '-'"
            :detail="`红色节点 ${summary?.red_overflow_node_count ?? 0} 个`"
          />

          <section class="panel wide">
            <BarList
              title="单位电耗排名"
              :caption="rangeCaption"
              :rows="energyChartRows"
              label-key="pump_id"
              value-key="interval_unit_energy_kwh_per_kt"
              grade-key="energy_grade"
              :digits="2"
            />
          </section>
          <section class="panel">
            <BarList
              title="设备疲劳指数"
              :caption="rangeCaption"
              :rows="healthChartRows"
              label-key="pump_id"
              value-key="fatigue_index"
              grade-key="safety_grade"
              :digits="2"
              :max-value="1"
            />
          </section>
          <section class="panel wide">
            <RiskMap :nodes="overflowRows" />
          </section>
        </section>

        <section v-show="activeTab === 'energy'" class="panel single">
          <div class="section-head">
            <div>
              <h2>能耗评估</h2>
              <p>窗口单位电耗使用有效流量窗口计算，所选范围内按单位电耗与规则等级排序。</p>
            </div>
            <StatusPill :grade="summary?.system_energy_grade ?? 'no_data'" />
          </div>
          <DataTable :columns="energyColumns" :rows="energyTableRows">
            <template #cross_unit_energy_grade="{ value }"><StatusPill :grade="String(value)" /></template>
            <template #energy_grade="{ value }"><StatusPill :grade="String(value)" /></template>
          </DataTable>
        </section>

        <section v-show="activeTab === 'safety'" class="panel single">
          <div class="section-head">
            <div>
              <h2>设备安全</h2>
              <p>启停、24h 运行负荷、连续运行和共享前池液位均按滚动窗口参与扣分。</p>
            </div>
            <StatusPill :grade="summary?.system_safety_grade ?? 'no_data'" />
          </div>
          <DataTable :columns="healthColumns" :rows="healthTableRows">
            <template #safety_grade="{ value }"><StatusPill :grade="String(value)" /></template>
          </DataTable>
        </section>

        <section v-show="activeTab === 'overflow'" class="overflow-layout">
          <section class="panel">
            <RiskMap :nodes="overflowRows" />
          </section>
          <section class="panel">
            <div class="section-head compact">
              <div>
                <h2>节点风险排名</h2>
                <p>规则评分不是统计概率，当前表格展示所选范围内每个节点的最高风险记录。</p>
              </div>
              <StatusPill :grade="summary?.system_overflow_grade ?? 'no_data'" />
            </div>
            <DataTable :columns="overflowColumns" :rows="overflowTableRows">
              <template #risk_grade="{ value }"><StatusPill :grade="String(value)" /></template>
            </DataTable>
          </section>
        </section>
      </template>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { fetchEnergy, fetchOverflowRisk, fetchPumpHealth, fetchSummary, type TimeRange } from "./api";
import BarList from "./components/BarList.vue";
import DataTable, { type ColumnDef } from "./components/DataTable.vue";
import MetricTile from "./components/MetricTile.vue";
import RiskMap from "./components/RiskMap.vue";
import StatusPill from "./components/StatusPill.vue";
import type { EnergyAssessment, OverflowRiskAssessment, PumpHealthAssessment, SystemSummary } from "./types";
import { fmt, pct } from "./utils";

const navItems = [
  { key: "overview", label: "系统总览", icon: "01" },
  { key: "energy", label: "能耗评估", icon: "02" },
  { key: "safety", label: "设备安全", icon: "03" },
  { key: "overflow", label: "漫溢风险", icon: "04" },
] as const;
const rangeItems: Array<{ key: TimeRange; label: string }> = [
  { key: "latest", label: "最新窗口" },
  { key: "24h", label: "过去24h" },
  { key: "all", label: "全周期" },
];

const activeTab = ref<(typeof navItems)[number]["key"]>("overview");
const selectedRange = ref<TimeRange>("latest");
const loading = ref(true);
const error = ref("");
const summary = ref<SystemSummary | null>(null);
const energyRows = ref<EnergyAssessment[]>([]);
const healthRows = ref<PumpHealthAssessment[]>([]);
const overflowRowsRaw = ref<OverflowRiskAssessment[]>([]);

const rangeCaption = computed(() => rangeItems.find((item) => item.key === selectedRange.value)?.label ?? "最新窗口");
const energyChartRows = computed(() =>
  [...energyRows.value]
    .filter((row) => row.interval_unit_energy_kwh_per_kt !== null)
    .sort((a, b) => Number(b.interval_unit_energy_kwh_per_kt ?? -1) - Number(a.interval_unit_energy_kwh_per_kt ?? -1)),
);
const healthChartRows = computed(() =>
  [...healthRows.value].sort((a, b) => Number(b.fatigue_index ?? 0) - Number(a.fatigue_index ?? 0)),
);
const overflowRows = computed(() =>
  [...overflowRowsRaw.value].sort((a, b) => Number(b.overflow_risk_score ?? 0) - Number(a.overflow_risk_score ?? 0)),
);

const energyTableRows = computed(() => energyChartRows.value.slice(0, 80) as unknown as Record<string, unknown>[]);
const healthTableRows = computed(() => healthChartRows.value.slice(0, 80) as unknown as Record<string, unknown>[]);
const overflowTableRows = computed(() => overflowRows.value.slice(0, 80) as unknown as Record<string, unknown>[]);

const energyColumns: ColumnDef[] = [
  { key: "timestamp", label: "时间" },
  { key: "pump_id", label: "水泵" },
  { key: "pump_station_id", label: "泵站" },
  { key: "flow_cms_avg", label: "流量 m3/s", format: (v) => fmt(v as number, 4) },
  { key: "interval_unit_energy_kwh_per_kt", label: "窗口单位电耗", format: (v) => fmt(v as number, 2) },
  { key: "energy_redundancy_ratio", label: "冗余率", format: (v) => pct(v as number, 1) },
  { key: "cross_unit_energy_grade", label: "横向等级" },
  { key: "energy_grade", label: "综合等级" },
];
const healthColumns: ColumnDef[] = [
  { key: "timestamp", label: "时间" },
  { key: "pump_id", label: "水泵" },
  { key: "startup_count_24h", label: "24h 启动", format: (v) => fmt(v as number, 0) },
  { key: "runtime_min_24h", label: "24h 运行 min", format: (v) => fmt(v as number, 0) },
  { key: "health_score", label: "健康分", format: (v) => fmt(v as number, 1) },
  { key: "fatigue_index", label: "疲劳指数", format: (v) => fmt(v as number, 2) },
  { key: "safety_grade", label: "等级" },
  { key: "deduction_detail", label: "扣分依据" },
];
const overflowColumns: ColumnDef[] = [
  { key: "timestamp", label: "时间" },
  { key: "node_id", label: "节点" },
  { key: "level_ratio", label: "液位比", format: (v) => pct(v as number, 1) },
  { key: "rainfall_next_1h_mm", label: "未来1h mm", format: (v) => fmt(v as number, 2) },
  { key: "rainfall_next_2h_mm", label: "未来2h mm", format: (v) => fmt(v as number, 2) },
  { key: "rainfall_source_2h", label: "降雨来源" },
  { key: "overflow_risk_score", label: "风险评分", format: (v) => fmt(v as number, 3) },
  { key: "risk_grade", label: "等级" },
];

async function loadRange(range: TimeRange) {
  loading.value = true;
  error.value = "";
  try {
    const [summaryData, energyData, healthData, overflowData] = await Promise.all([
      fetchSummary(range),
      fetchEnergy(range),
      fetchPumpHealth(range),
      fetchOverflowRisk(range, 5000),
    ]);
    summary.value = summaryData;
    energyRows.value = energyData;
    healthRows.value = healthData;
    overflowRowsRaw.value = overflowData;
  } catch (err) {
    error.value = err instanceof Error ? err.message : "无法读取后端 API";
  } finally {
    loading.value = false;
  }
}

function setRange(range: TimeRange) {
  if (selectedRange.value === range) return;
  selectedRange.value = range;
  void loadRange(range);
}

onMounted(() => {
  void loadRange(selectedRange.value);
});
</script>
