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
            <span>{{ timestampTitle }}</span>
            <strong>{{ timestampMain }}</strong>
            <small v-if="timestampSub">{{ timestampSub }}</small>
          </div>
        </div>
      </header>

      <div v-if="loading" class="state-box">正在读取第二部分评估结果...</div>
      <div v-else-if="error" class="state-box error">{{ error }}</div>

      <template v-else>
        <section v-show="activeTab === 'overview'" class="screen-grid">
          <MetricTile
            title="系统能耗"
            :scope-label="summaryScopeLabel"
            :grade="summary?.system_energy_grade ?? 'no_data'"
            :value="summary?.top_energy_pump || '-'"
            :detail="`红色 ${summary?.red_energy_count ?? 0} 台，橙色 ${summary?.orange_energy_count ?? 0} 台`"
          />
          <MetricTile
            title="设备安全"
            :scope-label="summaryScopeLabel"
            :grade="summary?.system_safety_grade ?? 'no_data'"
            :value="summary?.lowest_health_pump ?? '-'"
            :detail="`低健康泵 ${summary?.low_health_pump_count ?? 0} 台`"
          />
          <MetricTile
            title="漫溢风险"
            :scope-label="summaryScopeLabel"
            :grade="summary?.system_overflow_grade ?? 'no_data'"
            :value="summary?.highest_risk_node ?? '-'"
            :detail="`红色节点 ${summary?.red_overflow_node_count ?? 0} 个`"
          />

          <section class="panel wide">
            <BarList
              title="单位电耗排名"
              :caption="rangeCaption"
              :rows="energyChartRecords"
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
              :rows="healthChartRecords"
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
              <p class="section-note">{{ rangeScopeDescription }}</p>
              <p class="section-note">
                单位电耗用于横向比较不同水泵效率，冗余率用于比较当前窗口相对该泵自身 P25 基线的偏离程度。
              </p>
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
              <p class="section-note">{{ rangeScopeDescription }}</p>
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
                <p class="section-note">{{ rangeScopeDescription }}</p>
              </div>
              <StatusPill :grade="summary?.system_overflow_grade ?? 'no_data'" />
            </div>
            <DataTable :columns="overflowColumns" :rows="overflowTableRows">
              <template #risk_grade="{ value }"><StatusPill :grade="String(value)" /></template>
            </DataTable>
            <p class="table-footnote">
              降雨来源：forecast 表示来自降雨预报情景表；observed_replay 表示预报情景不覆盖当前时刻后
              1h/2h 时，采用历史实测降雨回放补足短时降雨输入。
            </p>
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
import type { EnergyAssessment, Grade, OverflowRiskAssessment, PumpHealthAssessment, SystemSummary } from "./types";
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

const gradeSeverity: Record<string, number> = { no_data: 0, green: 1, yellow: 2, orange: 3, red: 4 };

function worstGrade(a: Grade | undefined, b: Grade | undefined): Grade {
  return (gradeSeverity[String(a ?? "no_data")] >= gradeSeverity[String(b ?? "no_data")] ? a : b) ?? "no_data";
}

const rangeCaption = computed(() => rangeItems.find((item) => item.key === selectedRange.value)?.label ?? "最新窗口");
const latestTimestamp = computed(() => summary.value?.latest_timestamp ?? "-");
const timestampTitle = computed(() => (selectedRange.value === "latest" ? "评估窗口" : "评估范围"));
const timestampMain = computed(() => (selectedRange.value === "latest" ? latestTimestamp.value : rangeCaption.value));
const timestampSub = computed(() =>
  selectedRange.value === "latest" ? "" : `最新窗口：${latestTimestamp.value}`,
);
const rangeScopeDescription = computed(() =>
  selectedRange.value === "latest"
    ? "最新窗口：展示当前时间窗口的评估结果。"
    : "过去24h / 全周期：展示所选范围内各对象的最不利记录或综合排名。",
);
const summaryScopeLabel = computed(() => {
  if (selectedRange.value === "latest") return "最新窗口状态";
  if (selectedRange.value === "24h") return "过去24h最差状态";
  return "全周期最差状态";
});
const energyChartRows = computed(() => {
  const grouped = new Map<string, EnergyAssessment>();
  for (const row of energyRows.value) {
    if (row.interval_unit_energy_kwh_per_kt === null) continue;
    const current = grouped.get(row.pump_id);
    if (!current || Number(row.interval_unit_energy_kwh_per_kt) > Number(current.interval_unit_energy_kwh_per_kt ?? -1)) {
      grouped.set(row.pump_id, { ...row, energy_grade: worstGrade(row.energy_grade, current?.energy_grade) });
    } else if (current) {
      current.energy_grade = worstGrade(current.energy_grade, row.energy_grade);
      current.cross_unit_energy_grade = worstGrade(current.cross_unit_energy_grade, row.cross_unit_energy_grade);
    }
  }
  return [...grouped.values()].sort(
    (a, b) => Number(b.interval_unit_energy_kwh_per_kt ?? -1) - Number(a.interval_unit_energy_kwh_per_kt ?? -1),
  );
});
const healthChartRows = computed(() => {
  const grouped = new Map<string, PumpHealthAssessment>();
  for (const row of healthRows.value) {
    const current = grouped.get(row.pump_id);
    if (!current || Number(row.fatigue_index ?? 0) > Number(current.fatigue_index ?? 0)) {
      grouped.set(row.pump_id, { ...row, safety_grade: worstGrade(row.safety_grade, current?.safety_grade) });
    } else if (current) {
      current.safety_grade = worstGrade(current.safety_grade, row.safety_grade);
      current.health_score = Math.min(Number(current.health_score), Number(row.health_score));
      current.runtime_min_24h = Math.max(Number(current.runtime_min_24h), Number(row.runtime_min_24h));
      current.startup_count_24h = Math.max(Number(current.startup_count_24h), Number(row.startup_count_24h));
    }
  }
  return [...grouped.values()].sort((a, b) => Number(b.fatigue_index ?? 0) - Number(a.fatigue_index ?? 0));
});
const overflowRows = computed(() =>
  [...overflowRowsRaw.value].sort((a, b) => Number(b.overflow_risk_score ?? 0) - Number(a.overflow_risk_score ?? 0)),
);

const energyChartRecords = computed(() => energyChartRows.value as unknown as Record<string, unknown>[]);
const healthChartRecords = computed(() => healthChartRows.value as unknown as Record<string, unknown>[]);
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
  { key: "deduction_detail", label: "扣分依据", format: translateDeductionDetail },
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

function translateDeductionDetail(value: unknown): string {
  if (value === null || value === undefined || value === "" || String(value).trim().toLowerCase() === "none") {
    return "无";
  }
  return String(value)
    .split(";")
    .map((item) => item.trim())
    .filter(Boolean)
    .map((item) => {
      const repeatedStarts = item.match(/^30min repeated starts=(\d+)/i);
      if (repeatedStarts) return `30min内重复启停 ${repeatedStarts[1]} 次`;

      const starts24h = item.match(/^24h starts=(\d+)/i);
      if (starts24h) return `24h启停次数偏多（${starts24h[1]}次）`;

      const runtimeLoad = item.match(/^24h runtime load>([\d.]+)min/i);
      if (runtimeLoad) return `24h运行负荷过高（>${fmt(runtimeLoad[1], 0)}min）`;

      const continuousRuntime = item.match(/^continuous runtime>([\d.]+)min/i);
      if (continuousRuntime) return `连续运行时间过长（>${fmt(continuousRuntime[1], 0)}min）`;

      const forebay = item.match(/^forebay>([\d.]+)%/i);
      if (forebay) return `前池液位超过${fmt(forebay[1], 1)}%`;

      const levelChange = item.match(/^level change rate>([\d.]+)m\/min/i);
      if (levelChange) return `液位变化率偏大（>${fmt(levelChange[1], 3)}m/min）`;

      return item;
    })
    .join("；");
}

onMounted(() => {
  void loadRange(selectedRange.value);
});
</script>
