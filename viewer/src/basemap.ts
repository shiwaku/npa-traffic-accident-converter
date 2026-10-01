// 背景地図（国土地理院 最適化ベクトルタイルの淡色地図風スタイル public/pale.json）のテーマ対応。
// ダークテーマは淡色スタイルの色を明度反転して作る（japan-legal-speed-30kmh-map/viewer と同じ方式）。
// setStyle で差し替えると事故レイヤーやフィルタ状態が消えるため、背景レイヤーの色だけを
// setPaintProperty で書き換える。
import type maplibregl from "maplibre-gl";
import type { StyleSpecification } from "maplibre-gl";
import type { Theme } from "./theme";

function parseColor(str: string): [number, number, number, number] | null {
  const s = str.trim();
  const rgba = /^rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*(?:,\s*([\d.]+)\s*)?\)$/i.exec(s);
  if (rgba) return [+rgba[1], +rgba[2], +rgba[3], rgba[4] !== undefined ? +rgba[4] : 1];
  const hex = /^#([0-9a-f]{3}|[0-9a-f]{4}|[0-9a-f]{6}|[0-9a-f]{8})$/i.exec(s);
  if (hex) {
    let h = hex[1];
    if (h.length === 3 || h.length === 4) h = h.split("").map((c) => c + c).join("");
    const r = parseInt(h.slice(0, 2), 16), g = parseInt(h.slice(2, 4), 16), b = parseInt(h.slice(4, 6), 16);
    const a = h.length === 8 ? parseInt(h.slice(6, 8), 16) / 255 : 1;
    return [r, g, b, a];
  }
  return null;
}

function rgbToHsl(r: number, g: number, b: number): [number, number, number] {
  r /= 255; g /= 255; b /= 255;
  const max = Math.max(r, g, b), min = Math.min(r, g, b);
  const l = (max + min) / 2;
  let h = 0, s = 0;
  if (max !== min) {
    const d = max - min;
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    if (max === r) h = (g - b) / d + (g < b ? 6 : 0);
    else if (max === g) h = (b - r) / d + 2;
    else h = (r - g) / d + 4;
    h /= 6;
  }
  return [h, s, l];
}

function hslToRgb(h: number, s: number, l: number): [number, number, number] {
  if (s === 0) { const v = Math.round(l * 255); return [v, v, v]; }
  const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
  const p = 2 * l - q;
  const hue = (t: number): number => {
    if (t < 0) t += 1;
    if (t > 1) t -= 1;
    if (t < 1 / 6) return p + (q - p) * 6 * t;
    if (t < 1 / 2) return q;
    if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
    return p;
  };
  return [Math.round(hue(h + 1 / 3) * 255), Math.round(hue(h) * 255), Math.round(hue(h - 1 / 3) * 255)];
}

/** 明度を反転して暗色に(色相は保持、彩度は少し抑える)。 */
function darkenColor(str: string): string {
  const c = parseColor(str);
  if (!c) return str;
  const [r, g, b, a] = c;
  const [h, s, l] = rgbToHsl(r, g, b);
  const nl = Math.min(0.9, Math.max(0.05, 1 - l));
  const [nr, ng, nb] = hslToRgb(h, s * 0.85, nl);
  return `rgba(${nr},${ng},${nb},${a})`;
}

function transformValue(v: unknown, fn: (s: string) => string): unknown {
  if (typeof v === "string") return parseColor(v) ? fn(v) : v;
  if (Array.isArray(v)) return v.map((x) => transformValue(x, fn));
  return v;
}

function recolor(src: StyleSpecification, fn: (s: string) => string): StyleSpecification {
  const style = structuredClone(src) as StyleSpecification;
  for (const layer of style.layers) {
    const paint = (layer as { paint?: Record<string, unknown> }).paint;
    if (!paint) continue;
    for (const key of Object.keys(paint)) {
      if (key.includes("color")) paint[key] = transformValue(paint[key], fn);
    }
  }
  return style;
}

let paleStyle: StyleSpecification | null = null;
let darkStyle: StyleSpecification | null = null;

/** 淡色スタイルを読み込み、テーマに合わせた色にして返す。 */
export async function loadBasemapStyle(theme: Theme): Promise<StyleSpecification> {
  const res = await fetch(`${import.meta.env.BASE_URL}pale.json`);
  paleStyle = (await res.json()) as StyleSpecification;
  darkStyle = recolor(paleStyle, darkenColor);
  // Map に渡したオブジェクトは後で色の書き戻しに使うので、複製を渡す
  return structuredClone(theme === "dark" ? darkStyle : paleStyle);
}

/** 表示中の地図の背景レイヤーをテーマの色に塗り替える。 */
export function applyBasemapTheme(map: maplibregl.Map, theme: Theme): void {
  const style = theme === "dark" ? darkStyle : paleStyle;
  if (!style) return;
  for (const layer of style.layers) {
    const paint = (layer as { paint?: Record<string, unknown> }).paint;
    if (!paint || !map.getLayer(layer.id)) continue;
    for (const key of Object.keys(paint)) {
      if (key.includes("color")) map.setPaintProperty(layer.id, key, paint[key]);
    }
  }
}
