# 新年次データの追加手順

新しい年次のデータが公開されたときの追加手順です。以下は2026年を追加する場合の例です（2025年はこの手順で追加済み）。

---

## 例：2026年データを追加する場合

### 1. データのダウンロード

警察庁の年次ページ（`https://www.npa.go.jp/publications/statistics/koutsuu/opendata/2026/opendata_2026.html`）でファイル名を確認し、`download.sh` の `YEAR_FILES` に追記します：

```bash
YEAR_FILES[2026]="honhyo_2026.csv hojuhyo_2026.csv kosokuhyo_2026.csv fileteigisyo_2026.pdf fileteigisyo_2026.xlsx codebook_2026.pdf codebook_2026.xlsx"
```

その後、2026年分のみダウンロード：

```bash
./download.sh 2026
```

### 2. 既知年次への追加

`converter/__init__.py` の `KNOWN_YEARS` を更新します。CLI の `--all` と全チェックスクリプトはここを参照します：

```python
KNOWN_YEARS = list(range(2019, 2027))
```

### 3. コード表・ファイル定義書の差分チェック

前年（2025年）との差分を確認します：

```bash
python scripts/check_codebook_diff.py --base 2025 --new 2026
python scripts/check_file_definition.py --year 2025 2026
```

`check_codebook_diff.py` はシートごとにコード（警察署等・路線・トンネルは都道府県などとの複合キー）を比較し、追加・削除・名称変更・説明文の変更を出力します：

```
[変更あり] 当事者種別  (32件 → 33件)
  + 追加                43: 特定小型原付自転車 / ...
  ~ 変更                36: '二輪車－原付自転車 / ...' → '二輪車－一般原付自転車 / ...'

[変更あり] 警察署等  (1207件 → 1209件)
  + 追加            22-127: 宮城 / 栗原
  ~ 変更            47-104: '山梨 / 韮崎' → '山梨 / 甲斐'
```

### 4. Pythonコードの差分対応（コード値に差分がある場合のみ）

当事者種別などコード値の差分があった場合は `converter/codes/y2026.py` を作成し、`converter/codes/__init__.py` の `get_codes()` に分岐を追加します：

```bash
cp converter/codes/y2024.py converter/codes/y2026.py
```

`y2026.py` を開き、手順3で確認した差分のみ修正します。
変更のない辞書はそのまま残してください（`common.py` からの継承になります）。
差分がなければ `get_codes()` の else 節（y2024）がそのまま使われるため、コード変更は不要です。

### 5. コード表CSVの生成

警察署等・高速路線・トンネル番号はほぼ毎年変わる（署の新設・名称変更、道路の開通）ため、公式xlsxから年次別CSVを生成します：

```bash
python scripts/generate_code_tables.py --year 2026
```

`code_tables/2026/` に以下が生成されます：
- `3_koudohyou_keisatusyotoukoudo.csv`（警察署等）
- `9_koudohyou_rosen_kousokujidousyasenyou.csv`（高速路線）
- `53_koudohyou_tonnerubangou.csv`（トンネル番号）

CSVを置かない場合は最新既知年のディレクトリが自動フォールバックとして使用されますが、新設署・名称変更が反映されないため生成を推奨します。

### 6. 変換の実行

```bash
python -m converter --year 2026
```

### 7. 動作確認

```bash
python scripts/run_all_checks.py --year 2026
```

①（公式コード表との一致）・③（件数）・④（未定義コード）・⑤（列構成）がすべて PASS することを確認します。あわせて出力ファイル `output/honhyo_2026_converted.csv` を確認します：
- 都道府県名・警察署等名が正しく変換されているか
- 緯度・経度（10進数）が日本国内の値になっているか

### 8. ビューワ・ドキュメントの更新

- `viewer/src/filters.ts`・`viewer/src/main.ts`・`viewer/index.html`・`viewer/vite.config.ts` の年次リストと表記
- マージ版のファイル名（`honhyo_2019-2026_converted.*`）と PMTiles の source-layer 名（`honhyo_20192026_converted`）
- `.github/workflows/deploy-viewer.yml` の `VITE_PMTILES_URL`（PMTiles を R2 にアップロードしてから切り替える）
- README・CLAUDE.md の対応年次

---

## 注意事項

- **ファイル定義書（fileteigisyo）を必ず確認すること**  
  2022年に出力カラムが60列→72列に増えた前例があります。カラム構成が変わった場合は `converter/decode.py` のカラムマッピングも修正が必要です。

- **codebook（コード表）を必ず確認すること**  
  新しい当事者種別・車両形状コードが追加されることがあります（例：2024年に `43: 特定小型原付自転車` 追加）。

- **2019〜2021年のコード表について**  
  警察署等・高速路線・トンネル番号は2019年時点のスナップショットです。2020・2021年は一部の路線・署が未収録です。年次別CSVの整備は今後の課題です。
