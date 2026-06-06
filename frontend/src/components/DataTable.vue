<template>
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th v-for="column in columns" :key="column.key">{{ column.label }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(row, rowIndex) in rows" :key="rowKey(row, rowIndex)">
          <td v-for="column in columns" :key="column.key">
            <slot :name="column.key" :row="row" :value="row[column.key]">
              {{ column.format ? column.format(row[column.key], row) : row[column.key] ?? "-" }}
            </slot>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
export interface ColumnDef {
  key: string;
  label: string;
  format?: (value: unknown, row: Record<string, unknown>) => string;
}

defineProps<{
  columns: ColumnDef[];
  rows: Record<string, unknown>[];
}>();

function rowKey(row: Record<string, unknown>, index: number) {
  return `${row.timestamp ?? row.latest_timestamp ?? "row"}-${row.pump_id ?? row.node_id ?? index}`;
}
</script>
