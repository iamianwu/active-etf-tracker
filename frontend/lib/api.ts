const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";
const ADMIN_PASSWORD = process.env.NEXT_PUBLIC_ADMIN_PASSWORD || "";

export async function apiGet(path: string) {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function apiPost(path: string) {
  const headers: Record<string, string> = {};
  if (ADMIN_PASSWORD) headers["x-admin-password"] = ADMIN_PASSWORD;
  const res = await fetch(`${API_BASE}${path}`, { method: "POST", headers, cache: "no-store" });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export function fmt(n: any, digits = 2, empty = "-") {
  if (n === null || n === undefined || n === "" || Number.isNaN(Number(n))) return empty;
  return Number(n).toLocaleString("zh-TW", { maximumFractionDigits: digits, minimumFractionDigits: digits });
}

export function fmt0(n: any, empty = "-") {
  if (n === null || n === undefined || n === "" || Number.isNaN(Number(n))) return empty;
  return Number(n).toLocaleString("zh-TW", { maximumFractionDigits: 0 });
}

export function signedClass(n: any) {
  const v = Number(n || 0);
  if (v > 0) return "red";
  if (v < 0) return "green";
  return "muted";
}
