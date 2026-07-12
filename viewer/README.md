# 交通事故統計マップ ビューワ

コンバーターが生成した PMTiles（`output/honhyo_2019-2024_converted.pmtiles`）を表示する Web ビューワ。

MapLibre GL JS v5 + PMTiles + Vite + TypeScript 構成。
[shiwaku/npa-traffic-accident-map](https://github.com/shiwaku/npa-traffic-accident-map) をベースに、フィルタパネル・ヒートマップ表示などを追加したモダン版。

## 機能

- **事故ポイント表示**: 死亡事故=赤 / 負傷事故=青（死亡事故を前面に描画）。ズーム16以上で発生日ラベル
- **フィルタ**: 事故内容・発生年（2019–2024）・昼夜・関与当事者種別（歩行者/自転車/二輪車/特定小型原付/乗用車/貨物車）
- **ヒートマップ切替**: ポイント⇔ヒートマップ（タイル生成時の間引きがあるため低ズームの密度は目安）
- **詳細ポップアップ**: 事故情報＋当事者A/B情報、Google Maps / Street View リンク
- **住所検索**: 国土地理院 地名検索API
- **空中写真オーバーレイ**: 地理院 全国最新写真（ズーム14以上）、不透明度スライダー
- **作図ツール**: TerraDraw（計測・マーキング・GeoJSONダウンロード）
- ベースマップ: 国土地理院 最適化ベクトルタイル（淡色スタイル）
- **PWA対応**: ホーム画面に追加してアプリのように起動可能。スマホ最適化（フィルタパネルの開閉、ポップアップのボトムシート表示）
  - アプリシェル（HTML/JS/CSS/アイコン）はサービスワーカーでキャッシュされオフラインでも起動する。地図タイル・事故データ（外部ホストの大容量PMTiles）はキャッシュ対象外のため表示にはネットワークが必要

## 開発

```bash
cd viewer
npm install
npm run dev
```

開発サーバーは リポジトリの `../output/` を `/data/*` として配信する（HTTP Range 対応）。
事前に `python -m converter --all --merge` → `./export_geo.sh` で PMTiles を生成しておくこと。

## ビルド・デプロイ

```bash
# ホストしたPMTilesのURLを指定してビルド
VITE_PMTILES_URL=https://example.com/path/honhyo_2019-2024_converted.pmtiles npm run build
```

`dist/` を静的ホスティング（GitHub Pages 等）に配置する。
PMTiles 本体（約650MB）は Range リクエスト対応のストレージ（Cloudflare R2、レンタルサーバー等）に別途アップロードし、その URL を `VITE_PMTILES_URL` に指定する。

- ソースレイヤ名は `honhyo_20192024_converted`（tippecanoe がファイル名から自動命名）。
  PMTiles を作り直してファイル名が変わった場合は `src/main.ts` の `SOURCE_LAYER` を更新すること。
