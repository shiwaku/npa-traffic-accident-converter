/// <reference types="vite/client" />
import maplibregl, { type MapMouseEvent, setWorkerUrl } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import maplibreWorkerUrl from "maplibre-gl/dist/maplibre-gl-csp-worker?url";
import { Protocol } from "pmtiles";
import MaplibreGeocoder, {
  type MaplibreGeocoderApiConfig,
  type MaplibreGeocoderFeatureResults,
} from "@maplibre/maplibre-gl-geocoder";
import "@maplibre/maplibre-gl-geocoder/dist/maplibre-gl-geocoder.css";
import { MaplibreTerradrawControl } from "@watergis/maplibre-gl-terradraw";
import "@watergis/maplibre-gl-terradraw/dist/maplibre-gl-terradraw.css";
import { buildFilter, type FilterState } from "./filters";
import { buildPopupHtml } from "./popup";
import "./style.css";

// Vite + MapLibre GL CSP ワーカーの URL を明示的に指定
setWorkerUrl(maplibreWorkerUrl);

// 事故データ PMTiles。開発時は vite dev server が ../output を /data として配信。
// 本番デプロイ時は VITE_PMTILES_URL でホスト先 URL を指定する。
const PMTILES_URL: string =
  import.meta.env.VITE_PMTILES_URL ??
  `${import.meta.env.BASE_URL}data/honhyo_2019-2024_converted.pmtiles`;
const SOURCE_LAYER = "honhyo_20192024_converted";

const COLOR_FATAL = "#e8003a";
const COLOR_INJURY = "#2563eb";

const protocol = new Protocol();
maplibregl.addProtocol("pmtiles", protocol.tile.bind(protocol));

const map = new maplibregl.Map({
  container: "map",
  style: `${import.meta.env.BASE_URL}pale.json`,
  center: [139.6917, 35.6895],
  zoom: 9,
  minZoom: 4,
  maxZoom: 23,
  hash: true,
  attributionControl: false,
});

// 開発時のみ、デバッグ・E2E検証用に map インスタンスを公開
if (import.meta.env.DEV) {
  (window as unknown as { __map: maplibregl.Map }).__map = map;
}

// ジオコーダー（国土地理院 地名検索API）: 右上の最上段に配置
const geocoderApi = {
  forwardGeocode: async (
    config: MaplibreGeocoderApiConfig
  ): Promise<MaplibreGeocoderFeatureResults> => {
    const features: MaplibreGeocoderFeatureResults["features"] = [];
    const query = typeof config.query === "string" ? config.query : "";
    const textPrefix = query.substring(0, 3);
    try {
      const response = await fetch(
        `https://msearch.gsi.go.jp/address-search/AddressSearch?q=${encodeURIComponent(query)}`
      );
      const geojson = await response.json();
      for (const item of geojson) {
        if (item.properties.title.indexOf(textPrefix) !== -1) {
          features.push({
            type: "Feature",
            geometry: { type: "Point", coordinates: item.geometry.coordinates },
            place_name: item.properties.title,
            properties: item.properties,
            text: item.properties.title,
            place_type: ["place"],
            center: item.geometry.coordinates,
          });
        }
      }
    } catch (e) {
      console.error(`Failed to forwardGeocode with error: ${e}`);
    }
    return { type: "FeatureCollection", features };
  },
};
map.addControl(new MaplibreGeocoder(geocoderApi, { maplibregl }), "top-right");

map.addControl(new maplibregl.NavigationControl(), "top-right");
map.addControl(new maplibregl.FullscreenControl(), "top-right");
map.addControl(
  new maplibregl.GeolocateControl({
    positionOptions: { enableHighAccuracy: false },
    fitBoundsOptions: { maxZoom: 18 },
    trackUserLocation: true,
    showUserLocation: true,
  }),
  "top-right"
);
map.addControl(
  new maplibregl.ScaleControl({ maxWidth: 200, unit: "metric" }),
  "bottom-left"
);
map.addControl(
  new maplibregl.AttributionControl({
    compact: true,
    customAttribution:
      '<a href="https://github.com/shiwaku/npa-traffic-accident-converter" target="_blank">GitHub</a>',
  })
);

// TerraDraw（作図ツール）
map.addControl(
  new MaplibreTerradrawControl({
    modes: [
      "render",
      "point",
      "linestring",
      "polygon",
      "rectangle",
      "circle",
      "freehand",
      "select",
      "delete-selection",
      "delete",
      "download",
    ],
    open: false,
  }),
  "top-right"
);

// ---- フィルタ状態 ----
const filterState: FilterState = {
  naiyou: new Set(["死亡事故", "負傷事故"]),
  years: new Set(["2019", "2020", "2021", "2022", "2023", "2024"]),
  tyuya: new Set(["昼", "夜"]),
  party: "",
};

const JIKO_LAYERS = ["jiko-heat", "jiko-points", "jiko-labels"] as const;

function applyFilter(): void {
  if (!map.isStyleLoaded()) return;
  const filter = buildFilter(filterState);
  for (const id of JIKO_LAYERS) {
    if (map.getLayer(id)) map.setFilter(id, filter);
  }
}

// ---- レイヤ追加 ----
map.on("load", () => {
  // 全国最新写真（シームレス）: 初期は非表示
  map.addSource("seamlessphoto", {
    type: "raster",
    tiles: [
      "https://cyberjapandata.gsi.go.jp/xyz/seamlessphoto/{z}/{x}/{y}.jpg",
    ],
    tileSize: 256,
    attribution:
      '<a href="https://maps.gsi.go.jp/development/ichiran.html#seamlessphoto">全国最新写真（シームレス）</a>',
  });
  map.addLayer({
    id: "seamlessphoto",
    type: "raster",
    source: "seamlessphoto",
    minzoom: 14,
    maxzoom: 23,
    layout: { visibility: "none" },
    paint: { "raster-opacity": 0.5 },
  });

  // 交通事故データ
  map.addSource("jiko", {
    type: "vector",
    url: `pmtiles://${PMTILES_URL}`,
    attribution:
      '<a href="https://www.npa.go.jp/publications/statistics/koutsuu/opendata/index_opendata.html">警察庁 交通事故統計情報のオープンデータ（2019〜2024年）を加工して作成</a>',
  });

  // ヒートマップ（初期は非表示）
  map.addLayer({
    id: "jiko-heat",
    type: "heatmap",
    source: "jiko",
    "source-layer": SOURCE_LAYER,
    layout: { visibility: "none" },
    paint: {
      "heatmap-weight": 1,
      // 高ズームほど実ポイント数が増える（タイル間引きが減る）ため、強度は逆に下げる
      "heatmap-intensity": [
        "interpolate", ["linear"], ["zoom"],
        4, 1.2,
        6, 0.9,
        8, 0.4,
        10, 0.12,
        12, 0.06,
        14, 0.03,
      ],
      "heatmap-radius": [
        "interpolate", ["linear"], ["zoom"],
        4, 2,
        9, 5,
        14, 12,
      ],
      "heatmap-color": [
        "interpolate", ["linear"], ["heatmap-density"],
        0, "rgba(37, 99, 235, 0)",
        0.2, "rgba(37, 99, 235, 0.55)",
        0.45, "rgba(16, 185, 129, 0.7)",
        0.7, "rgba(250, 204, 21, 0.85)",
        1, "rgba(232, 0, 58, 0.95)",
      ],
      "heatmap-opacity": 0.85,
    },
  });

  // 事故ポイント（死亡=赤 / 負傷=青、死亡を上に描画）
  map.addLayer({
    id: "jiko-points",
    type: "circle",
    source: "jiko",
    "source-layer": SOURCE_LAYER,
    layout: {
      "circle-sort-key": [
        "match", ["get", "事故内容"],
        "死亡事故", 1,
        0,
      ],
    },
    paint: {
      "circle-color": [
        "match", ["get", "事故内容"],
        "死亡事故", COLOR_FATAL,
        COLOR_INJURY,
      ],
      "circle-radius": [
        "interpolate", ["linear"], ["zoom"],
        4, 1.4,
        8, 2.6,
        12, 5,
        16, 8,
      ],
      "circle-opacity": 0.85,
      "circle-stroke-color": "#ffffff",
      "circle-stroke-width": [
        "interpolate", ["linear"], ["zoom"],
        4, 0.2,
        12, 1.2,
      ],
      "circle-stroke-opacity": 0.9,
    },
  });

  // 選択中の事故ポイントのハイライト（クリックした点にリングを表示）
  map.addSource("selected", {
    type: "geojson",
    data: { type: "FeatureCollection", features: [] },
  });
  map.addLayer({
    id: "jiko-highlight-glow",
    type: "circle",
    source: "selected",
    paint: {
      "circle-color": "#ffab00",
      "circle-opacity": 0.25,
      "circle-radius": [
        "interpolate", ["linear"], ["zoom"],
        4, 10,
        8, 14,
        12, 18,
        16, 24,
      ],
    },
  });
  map.addLayer({
    id: "jiko-highlight-ring",
    type: "circle",
    source: "selected",
    paint: {
      "circle-color": "rgba(0, 0, 0, 0)",
      "circle-radius": [
        "interpolate", ["linear"], ["zoom"],
        4, 6,
        8, 9,
        12, 12,
        16, 16,
      ],
      "circle-stroke-color": "#ff9500",
      "circle-stroke-width": 3,
    },
  });

  // 発生日ラベル（高ズームのみ）
  map.addLayer({
    id: "jiko-labels",
    type: "symbol",
    source: "jiko",
    "source-layer": SOURCE_LAYER,
    minzoom: 16,
    layout: {
      "text-field": [
        "concat",
        ["get", "発生日時_年"], "/",
        ["get", "発生日時_月"], "/",
        ["get", "発生日時_日"],
      ],
      "text-font": ["NotoSansJP-Regular"],
      "text-offset": [0, -1.3],
      "text-allow-overlap": true,
      "text-size": 12,
    },
    paint: {
      "text-color": [
        "match", ["get", "事故内容"],
        "死亡事故", COLOR_FATAL,
        COLOR_INJURY,
      ],
      "text-halo-color": "#ffffff",
      "text-halo-width": 1,
    },
  });

  applyFilter();
});

// ---- 選択ハイライト ----
const EMPTY_FC: GeoJSON.FeatureCollection = {
  type: "FeatureCollection",
  features: [],
};
function setHighlight(coords: [number, number] | null): void {
  const src = map.getSource("selected") as maplibregl.GeoJSONSource | undefined;
  if (!src) return;
  src.setData(
    coords
      ? {
          type: "FeatureCollection",
          features: [
            { type: "Feature", geometry: { type: "Point", coordinates: coords }, properties: {} },
          ],
        }
      : EMPTY_FC
  );
}

// ---- ポップアップ ----
// ポップアップは1つを使い回す。closeOnClick を無効にして、
// 別の点を連続クリックしたときに「前のポップアップの close」が
// 「新しいハイライトの設定」より後に走ってハイライトを消してしまう
// レースを防ぐ。選択解除は空きスペースのクリックと×ボタンで行う。
let selectedPopup: maplibregl.Popup | null = null;

function clearSelection(): void {
  setHighlight(null);
  if (selectedPopup) {
    const p = selectedPopup;
    selectedPopup = null;
    p.remove();
  }
}

map.on(
  "click",
  "jiko-points",
  (e: MapMouseEvent & { features?: maplibregl.MapGeoJSONFeature[] }) => {
    if (!e.features || e.features.length === 0) return;
    const feature = e.features[0];
    const [lng, lat] = (feature.geometry as GeoJSON.Point).coordinates;
    setHighlight([lng, lat]);
    if (!selectedPopup) {
      selectedPopup = new maplibregl.Popup({ maxWidth: "360px", closeOnClick: false });
      // ×ボタンで閉じたらハイライトも消す
      selectedPopup.on("close", () => {
        selectedPopup = null;
        setHighlight(null);
      });
    }
    selectedPopup
      .setLngLat([lng, lat])
      .setHTML(buildPopupHtml(feature.properties as Record<string, unknown>, lng, lat))
      .addTo(map);
  }
);

// 事故ポイント以外をクリックしたら選択を解除する。
// この一般クリックハンドラは点の有無を自前で判定するため、レイヤ用ハンドラとの
// 実行順に依存しない（点をクリックした場合はここでは何もしない）。
map.on("click", (e) => {
  const hit = map.queryRenderedFeatures(e.point, { layers: ["jiko-points"] });
  if (hit.length === 0) clearSelection();
});
map.on("mouseenter", "jiko-points", () => {
  map.getCanvas().style.cursor = "pointer";
});
map.on("mouseleave", "jiko-points", () => {
  map.getCanvas().style.cursor = "";
});

// ---- パネル UI ----
function setupChipGroup(
  containerId: string,
  values: Set<string>
): void {
  const container = document.getElementById(containerId)!;
  container.querySelectorAll<HTMLButtonElement>(".chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const value = chip.dataset.value!;
      if (values.has(value)) {
        values.delete(value);
        chip.classList.remove("active");
      } else {
        values.add(value);
        chip.classList.add("active");
      }
      applyFilter();
    });
  });
}

setupChipGroup("filter-naiyou", filterState.naiyou);
setupChipGroup("filter-year", filterState.years);
setupChipGroup("filter-tyuya", filterState.tyuya);

document.getElementById("filter-party")!.addEventListener("change", (e) => {
  filterState.party = (e.target as HTMLSelectElement).value;
  applyFilter();
});

// 表示モード（ポイント / ヒートマップ）
document
  .querySelectorAll<HTMLButtonElement>("#display-mode .segment")
  .forEach((btn) => {
    btn.addEventListener("click", () => {
      document
        .querySelectorAll("#display-mode .segment")
        .forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      const heatmap = btn.dataset.value === "heatmap";
      map.setLayoutProperty("jiko-heat", "visibility", heatmap ? "visible" : "none");
      map.setLayoutProperty("jiko-points", "visibility", heatmap ? "none" : "visible");
      map.setLayoutProperty("jiko-labels", "visibility", heatmap ? "none" : "visible");
    });
  });

// 空中写真の表示切替・不透明度
const photoToggle = document.getElementById("photo-toggle") as HTMLInputElement;
const photoOpacity = document.getElementById("photo-opacity") as HTMLInputElement;
const photoOpacityValue = document.getElementById("photo-opacity-value")!;
photoToggle.addEventListener("change", () => {
  photoOpacity.disabled = !photoToggle.checked;
  map.setLayoutProperty(
    "seamlessphoto",
    "visibility",
    photoToggle.checked ? "visible" : "none"
  );
});
photoOpacity.addEventListener("input", () => {
  const value = parseInt(photoOpacity.value, 10);
  map.setPaintProperty("seamlessphoto", "raster-opacity", value / 100);
  photoOpacityValue.textContent = `${value}%`;
});

// 画面内の描画済み件数（タイル間引きがあるため目安）
const statsEl = document.getElementById("stats")!;
map.on("idle", () => {
  if (!map.isStyleLoaded() || !map.getLayer("jiko-points")) return;
  if (map.getLayoutProperty("jiko-points", "visibility") === "none") {
    statsEl.textContent = "ヒートマップ表示中";
    return;
  }
  const features = map.queryRenderedFeatures({ layers: ["jiko-points"] });
  const seen = new Set<string>();
  for (const f of features) {
    const p = f.properties as Record<string, unknown>;
    seen.add(`${p["都道府県名"]}|${p["発生日時_年"]}|${p["本票番号"]}`);
  }
  statsEl.textContent = `画面内: ${seen.size.toLocaleString()} 件（描画済みポイント・目安）`;
});

// パネル開閉（狭い画面では初期状態を閉じる）
const panel = document.getElementById("panel")!;
if (window.matchMedia("(max-width: 640px)").matches) {
  panel.classList.add("closed");
}
document.getElementById("panel-toggle")!.addEventListener("click", () => {
  panel.classList.toggle("closed");
});
document.getElementById("panel-close")!.addEventListener("click", () => {
  panel.classList.add("closed");
});
