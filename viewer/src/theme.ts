export type Theme = "light" | "dark";

const STORAGE_KEY = "npa-traffic-accident-viewer-theme";

/** 一度でも切り替えたらその選択、無ければ OS のダークモード設定に合わせる。 */
export function initialTheme(): Theme {
  let saved: string | null = null;
  try {
    saved = localStorage.getItem(STORAGE_KEY);
  } catch {
    /* プライベートモード等 */
  }
  if (saved === "light" || saved === "dark") return saved;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

/** <html data-theme="…"> と theme-color を更新する。 */
export function applyThemeAttr(theme: Theme): void {
  document.documentElement.dataset.theme = theme;
  document
    .querySelector('meta[name="theme-color"]')
    ?.setAttribute("content", theme === "dark" ? "#1b1e24" : "#ffffff");
}

/** ボタンで切り替えたテーマを保存する（OS 設定追従のままの人は保存しない）。 */
export function saveTheme(theme: Theme): void {
  try {
    localStorage.setItem(STORAGE_KEY, theme);
  } catch {
    /* 保存できなくても表示はできる */
  }
}
