# 新年次データの追加手順

2025年など新しい年次のデータが公開されたときの追加手順です。

---

## 例：2025年データを追加する場合

### 1. データのダウンロード

`download.sh` の末尾付近にある以下のコメント行を有効にします：

```bash
# YEAR_FILES[2025]="honhyo_2025.csv hojuhyo_2025.csv kosokuhyo_2025.csv fileteigisyo_2025.pdf fileteigisyo_2025.xlsx codebook_2025.pdf codebook_2025.xlsx"
```

その後、2025年分のみダウンロード：

```bash
./download.sh 2025
```

### 2. コード表の差分チェック

前年（2024年）との差分を自動チェックします：

```bash
python scripts/check_codebook_diff.py --base 2024 --new 2025
```

出力例：
```
[変更あり] 当事者種別
  + 追加  XX: 新しい種別名
  ~ 変更  36: '二輪車－一般原付自転車' → '...'
```

差分がなければ追加作業は不要です（前年の設定が自動的に使用されます）。

### 3. Pythonコードの差分対応（差分がある場合のみ）

差分があった場合は `converter/codes/y2025.py` を作成します：

```bash
cp converter/codes/y2024.py converter/codes/y2025.py
```

`y2025.py` を開き、手順2で確認した差分のみ修正します。
変更のない辞書はそのまま残してください（`common.py` からの継承になります）。

### 4. コード表CSVの追加（差分がある場合のみ）

警察署等コード・高速路線コード・トンネル番号に変更があった場合：

```bash
mkdir -p code_tables/2025
```

対応するCSVファイルを `code_tables/2025/` に配置します：
- `3_koudohyou_keisatusyotoukoudo.csv`（警察署等）
- `9_koudohyou_rosen_kousokujidousyasenyou.csv`（高速路線）
- `53_koudohyou_tonnerubangou.csv`（トンネル番号）

CSVが存在しない場合は前年（`code_tables/2024/`）が自動フォールバックとして使用されます。

### 5. 変換の実行

```bash
python -m converter --year 2025
```

### 6. 動作確認

出力ファイル `output/honhyo_2025_converted.csv` を確認します：
- 行数が元データ（`data/2025/honhyo_2025.csv`）と一致しているか
- 都道府県名・警察署等名が正しく変換されているか
- 緯度・経度（10進数）が日本国内の値になっているか

---

## 注意事項

- **ファイル定義書（fileteigisyo）を必ず確認すること**  
  2022年に出力カラムが60列→72列に増えた前例があります。カラム構成が変わった場合は `converter/decode.py` のカラムマッピングも修正が必要です。

- **codebook（コード表）を必ず確認すること**  
  新しい当事者種別・車両形状コードが追加されることがあります（例：2024年に `43: 特定小型原付自転車` 追加）。

- **2019〜2021年のコード表について**  
  警察署等・高速路線・トンネル番号は2019年時点のスナップショットです。2020・2021年は一部の路線・署が未収録です。年次別CSVの整備は今後の課題です。
