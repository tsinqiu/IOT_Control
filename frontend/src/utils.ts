import type { Grade } from "./types";

export function gradeLabel(grade: Grade | undefined): string {
  const labels: Record<string, string> = {
    green: "正常",
    yellow: "关注",
    orange: "预警",
    red: "高风险",
    no_data: "无数据",
  };
  return labels[String(grade ?? "")] ?? String(grade ?? "-");
}

export function gradeClass(grade: Grade | undefined): string {
  const normalized = String(grade ?? "no_data");
  return ["green", "yellow", "orange", "red", "no_data"].includes(normalized)
    ? normalized
    : "no_data";
}

export function fmt(value: number | string | null | undefined, digits = 2): string {
  if (value === null || value === undefined || value === "") return "-";
  const numberValue = Number(value);
  if (!Number.isFinite(numberValue)) return String(value);
  return numberValue.toLocaleString("zh-CN", {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  });
}

export function pct(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) return "-";
  return `${(Number(value) * 100).toLocaleString("zh-CN", {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  })}%`;
}
