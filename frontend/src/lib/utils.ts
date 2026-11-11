import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import { format, formatDistanceToNowStrict, parseISO } from "date-fns";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const inr = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });
const inr2 = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", minimumFractionDigits: 2 });
const num = new Intl.NumberFormat("en-IN");
const compact = new Intl.NumberFormat("en-IN", { notation: "compact", maximumFractionDigits: 1 });

/** Money arrives from the API as decimal strings (BR-15). null means restricted or not supplied by the bank. */
export function formatINR(value: string | number | null | undefined, opts: { precise?: boolean; compact?: boolean } = {}) {
  if (value === null || value === undefined || value === "") return null;
  const n = typeof value === "string" ? Number(value) : value;
  if (Number.isNaN(n)) return null;
  if (opts.compact) return "₹" + compact.format(n);
  return (opts.precise ? inr2 : inr).format(n);
}

export const formatNumber = (n: number | null | undefined) => (n === null || n === undefined ? "-" : num.format(n));

export function toDate(v: string | Date | null | undefined): Date | null {
  if (!v) return null;
  return typeof v === "string" ? parseISO(v) : v;
}

export function formatDate(v: string | Date | null | undefined, pattern = "dd MMM yyyy") {
  const d = toDate(v);
  return d ? format(d, pattern) : "-";
}

export function formatDateTime(v: string | Date | null | undefined) {
  return formatDate(v, "dd MMM yyyy, HH:mm");
}

export function relativeTime(v: string | Date | null | undefined) {
  const d = toDate(v);
  return d ? formatDistanceToNowStrict(d, { addSuffix: true }) : "-";
}

export function titleCase(code: string | null | undefined) {
  if (!code) return "-";
  return code.toLowerCase().split("_").map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
}

export function initials(name: string | null | undefined) {
  if (!name) return "?";
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0]!.toUpperCase()).join("");
}

export function qs(params: Record<string, unknown>) {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === "" || (Array.isArray(v) && v.length === 0)) continue;
    sp.set(k, Array.isArray(v) ? v.join(",") : String(v));
  }
  const s = sp.toString();
  return s ? `?${s}` : "";
}
