#!/bin/bash
# マージCSV → GeoParquet / GeoJSON / PMTiles 変換
#
# 使い方:
#   ./export_geo.sh                                    # デフォルト入力を使用
#   ./export_geo.sh output/honhyo_2019-2024_converted.csv

set -e

INPUT_CSV="${1:-output/honhyo_2019-2024_converted.csv}"
BASENAME="${INPUT_CSV%.csv}"

if [ ! -f "$INPUT_CSV" ]; then
    echo "ERROR: $INPUT_CSV が存在しません" >&2
    echo "先に python -m converter --all --merge を実行してください" >&2
    exit 1
fi

echo "入力: $INPUT_CSV"
echo ""

# GeoParquet（geopandas + pyarrowで変換）
echo "[1/3] GeoParquet 変換中..."
python - <<EOF
import geopandas as gpd
import pandas as pd

df = pd.read_csv("$INPUT_CSV", dtype=str)
df["geometry_x"] = pd.to_numeric(df["地点_経度（東経）_10進数"], errors="coerce")
df["geometry_y"] = pd.to_numeric(df["地点_緯度（北緯）_10進数"], errors="coerce")
df = df.dropna(subset=["geometry_x", "geometry_y"])
gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df["geometry_x"], df["geometry_y"]), crs="EPSG:4326")
gdf = gdf.drop(columns=["geometry_x", "geometry_y"])
gdf.to_parquet("${BASENAME}.parquet", index=False)
EOF
echo "  → ${BASENAME}.parquet"

# GeoJSON
echo "[2/3] GeoJSON 変換中..."
ogr2ogr -f "GeoJSON" "${BASENAME}.geojson" "$INPUT_CSV" \
    -oo X_POSSIBLE_NAMES=地点_経度（東経）_10進数 \
    -oo Y_POSSIBLE_NAMES=地点_緯度（北緯）_10進数 \
    -s_srs EPSG:4326 -t_srs EPSG:4326
echo "  → ${BASENAME}.geojson"

# PMTiles
echo "[3/3] PMTiles 変換中..."
tippecanoe -o "${BASENAME}.pmtiles" "${BASENAME}.geojson" -pf -pk -P -B12
echo "  → ${BASENAME}.pmtiles"

echo ""
echo "完了"
