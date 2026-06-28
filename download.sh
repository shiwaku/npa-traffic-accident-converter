#!/bin/bash
# 使い方:
#   ./download.sh          # 全年度ダウンロード
#   ./download.sh 2025     # 2025年のみダウンロード
#   ./download.sh 2024 2025  # 複数年指定

BASE_URL="https://www.npa.go.jp/publications/statistics/koutsuu/opendata"
DATA_DIR="./data"

# 年次ごとのファイル定義
# 引数なし → 全年度、引数あり → 指定年度のみ
declare -A YEAR_FILES

YEAR_FILES[2019]="honhyo_2019.csv hojuhyo_2019.csv kosokuhyo_2019.csv filedefinition_2019.pdf codebook_2019.pdf"
YEAR_FILES[2020]="honhyo_2020.csv hojuhyo_2020.csv kosokuhyo_2020.csv 1_fileteigisyo_2020.pdf codebook_2020.pdf"
YEAR_FILES[2021]="honhyo_2021.csv hojuhyo_2021.csv kosokuhyo_2021.csv fileteigisyo_2021.pdf codebook_2021.pdf"
YEAR_FILES[2022]="honhyo_2022.csv hojuhyo_2022.csv kosokuhyo_2022.csv fileteigisyo_2022.pdf fileteigisyo_2022.xlsx codebook_2022.pdf codebook_2022.xlsx"
YEAR_FILES[2023]="honhyo_2023.csv hojuhyo_2023.csv kosokuhyo_2023.csv fileteigisyo_2023.pdf fileteigisyo_2023.xlsx codebook_2023.pdf codebook_2023.xlsx"
YEAR_FILES[2024]="honhyo_2024.csv hojuhyo_2024.csv kosokuhyo_2024.csv fileteigisyo_2024.pdf fileteigisyo_2024.xlsx codebook_2024.pdf codebook_2024.xlsx"
# 2025年追加時はここに追記:
# YEAR_FILES[2025]="honhyo_2025.csv hojuhyo_2025.csv kosokuhyo_2025.csv fileteigisyo_2025.pdf fileteigisyo_2025.xlsx codebook_2025.pdf codebook_2025.xlsx"

mkdir -p "$DATA_DIR"

# 対象年度の決定
if [ $# -eq 0 ]; then
  TARGET_YEARS=($(echo "${!YEAR_FILES[@]}" | tr ' ' '\n' | sort))
else
  TARGET_YEARS=("$@")
fi

for YEAR in "${TARGET_YEARS[@]}"; do
  if [ -z "${YEAR_FILES[$YEAR]+_}" ]; then
    echo "ERROR: Year $YEAR is not defined in YEAR_FILES. Add it to download.sh first."
    continue
  fi

  mkdir -p "$DATA_DIR/$YEAR"
  echo "--- $YEAR ---"

  for FILENAME in ${YEAR_FILES[$YEAR]}; do
    DEST="$DATA_DIR/$YEAR/$FILENAME"

    if [ -f "$DEST" ]; then
      echo "SKIP: $YEAR/$FILENAME (already exists)"
      continue
    fi

    URL="$BASE_URL/$YEAR/$FILENAME"
    echo "Downloading: $URL"
    curl -fL --retry 3 --retry-delay 2 -o "$DEST" "$URL"
    if [ $? -ne 0 ]; then
      echo "ERROR: Failed to download $URL"
      rm -f "$DEST"
    else
      echo "OK: $DEST"
    fi
    sleep 1
  done
done

echo ""
echo "Done."
