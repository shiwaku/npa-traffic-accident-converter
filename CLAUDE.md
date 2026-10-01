# CLAUDE.md

警察庁交通事故統計オープンデータ コンバーターの開発ガイド。

---

## プロジェクト概要

警察庁公開の本票CSV（Shift-JIS）を読み込み、コード値→人間可読ラベルに変換し、緯度経度（度分秒）→10進数変換して UTF-8 CSVとして出力するPythonパッケージ。

対応年次: 2019〜2025年（既知年次は `converter/__init__.py` の `KNOWN_YEARS` で一元管理。2026年以降はフォールバック設計済み）

---

## よく使うコマンド

```bash
# 変換実行
python -m converter --year 2024
python -m converter --all

# チェック（全5種まとめ）
python scripts/run_all_checks.py --year 2024
python scripts/run_all_checks.py --all

# ①コード表照合（公式xlsx vs 変換用）
python scripts/check_codetable_vs_official.py --all

# ③件数確認
python scripts/check_record_count.py --all

# ⑤ファイル定義書との列確認
python scripts/check_file_definition.py --year 2022 2023 2024

# 年次間コード表差分（新年次追加時）
python scripts/check_codebook_diff.py --base 2024 --new 2025

# 公式xlsxから年次別CSV（警察署等・高速路線・トンネル）を生成
python scripts/generate_code_tables.py --year 2025
```

---

## アーキテクチャ

```
decode.py   → Shift-JIS読み込み・緯度経度変換（度分秒→10進数）
convert.py  → コード値→ラベル変換（CSV辞書 + Pythonコード辞書）
merge.py    → 複数年DataFrameのマージ
cli.py      → --year / --all / --merge の引数処理
```

### コード辞書の構造

`converter/codes/` 以下：

- `common.py`: 全年次共通の辞書（TYUUYA, TENKOU, TIKEI など27種）
- `y2019_2021.py`: 2019〜2021年固有の差分（`from common import *` + 上書き）
- `y2022.py` / `y2023.py` / `y2024.py`: 各年次固有の差分
- `__init__.py` の `get_codes(year)`: 年次→モジュールのルーティング。2024以降はy2024にフォールバック（2025年はコード値の差分がないためy2024を使用）

### CSVコード表の構造

`code_tables/` 以下：

- `common/`: 都道府県コードなど年次不変のCSV
- `2019-2021/` / `2022/` / `2023/` / `2024/` / `2025/`: 警察署等・高速路線・トンネル番号（年次別）。2025年は `generate_code_tables.py` で公式xlsxから生成
- 本票の変換で読むのは警察署等・高速路線の2つ。トンネル番号CSVは高速票用で、本票の出力には影響しない
- 存在しない年次のCSVは `_year_dir()` が最新既知年にフォールバック

---

## 年次別の主な差分（公式コード表に基づく）

### 2022年（令和4年）: ファイル定義書の大幅改訂
公式ファイル定義書（`fileteigisyo_2022.xlsx`）の改訂により、本票の列構成が **60列→72列** に変更。
追加列: `日の出時刻 時/分`・`日の入り時刻 時/分`・`オートマチック車（A/B）`・`サポカー（A/B）`・`認知機能検査経過日数（A/B）`・`運転練習の方法（A/B）` の計12列。
2019〜2021年はこれらの列を元データが持っていないため、出力CSV上は空値。

### 2024年（令和6年）: 当事者種別コード表の変更
公式コード表（`codebook_2024.xlsx` 当事者種別シート）に2件の変更：
- コード `36`: ラベルが `二輪車－原付自転車`（〜2023） → `二輪車－一般原付自転車`（2024〜）
- コード `43`: 新規追加 `特定小型原付自転車`（電動キックボード等。道路交通法改正により2023年7月以降に区分が新設）

### 2025年（令和7年）: 地理系コード表のみ変更
入力CSVの列構成（ファイル定義書の68列）とコード値の辞書は2024年と同一。変わったのは警察署等・高速路線・トンネル番号のみ：
- 警察署等: 新設2署（`13-050` 北海道（釧路方面）交通課、`22-127` 宮城 栗原）、名称変更5署（`40-114` 龍ヶ崎→竜ケ崎、`47-104` 韮崎→甲斐、`63-170` 朝来→南但馬、`65-108` 湯浅→有田湯浅、`96-116` 伊佐→伊佐湧水）
- 高速路線: 26路線追加（倶知安余市道路、小名浜道路、山陰道の島根区間）、`83-5003/5004` 高知南国道路→高知東部自動車道（公式xlsxでは5004の「下り」が欠落しており、そのまま収録）
- トンネル番号: 30件追加

### 2019〜2021年の警察署等・高速路線
警察庁は2022年以降、年次別の警察署等コードCSVを提供しているが、2019〜2021年分は1つのCSV（`code_tables/2019-2021/`）しか存在しない。このCSVは2019年時点の内容であり、2020年・2021年に警察署の統廃合や高速道路の新規開通があった場合、その分のコードが未収録となる。該当レコードの警察署等名・路線名は空欄で出力される。

### 2024年のトンネル番号CSV
公式コード表（`codebook_2024.xlsx` トンネル番号シート）には2024年版として3658件が記載されているが、`code_tables/2024/53_koudohyou_tonnerubangou.csv` は2023年版（3664件）をそのまま使用している。ただしトンネル番号CSVは本票の変換では使っていないため、本票の出力（リリースデータ）には影響しない。

---

## チェックスクリプト概要

| スクリプト | チェック内容 |
|-----------|------------|
| `check_codetable_vs_official.py` | ① 公式xlsx ↔ CSV・Pythonコード辞書の完全一致 |
| `check_output_diff.py` | ② 旧リポジトリ出力 ↔ 新コンバーター出力の全件比較 |
| `check_record_count.py` | ③ 変換前後の件数一致（スキップ率0.1%以下） |
| `check_undefined_codes.py` | ④ 実データに未定義コードが出現しないか |
| `check_file_definition.py` | ⑤ ファイル定義書との列構成確認 |
| `run_all_checks.py` | ①③④⑤を一括実行（②は--with-diffで追加） |
| `check_codebook_diff.py` | 年次間コード表差分（新年次追加時に使用）。複数列シートは複合キーで比較 |
| `generate_code_tables.py` | 公式xlsx → `code_tables/{year}/` のCSV生成 |

各スクリプトは `scripts/_common.py` を import し、リポジトリルートの sys.path 追加と標準出力のUTF-8化を行う（`pip install -e .` や `PYTHONUTF8` なしで動く）。

### ①チェックの既知許容差異

- **SYADOUHUKUIN（車道幅員）**: 2022年xlsxは `'12,14'` のような複合コード表記。2023年以降のxlsxからは `'12'`/`'13'`/`'16'` が削除されたが、2022年データに29,322件出現するため辞書に残している（旧ツールは未定義で空値になっていた。詳細は [CHECKS.md](CHECKS.md) の②比較結果を参照）。`check_codetable_vs_official.py` の `DICT_ONLY_ALLOWED` で許容済み
- **トンネル番号（2022・2024年）**: CSV版と公式xlsx版で一部差異あり（既知の問題）

---

## 新年次（2026年）追加手順

詳細は [ADDING_NEW_YEAR.md](ADDING_NEW_YEAR.md) を参照。概要：

1. `download.sh` に `YEAR_FILES[2026]=...` を追記し `./download.sh 2026`
2. `converter/__init__.py` の `KNOWN_YEARS` に2026を追加
3. `python scripts/check_codebook_diff.py --base 2025 --new 2026`
4. コード値に差分があれば `converter/codes/y2026.py` を作成し `get_codes()` に分岐追加（差分なければ不要）
5. `python scripts/generate_code_tables.py --year 2026`
6. `python -m converter --year 2026` → `python scripts/run_all_checks.py --year 2026`
7. ビューワ（`viewer/`）の年次リスト、マージ版ファイル名、`deploy-viewer.yml` の PMTiles URL を更新

---

## 注意事項

- 入力CSVのエンコーディングは `cp932`（Shift-JIS）。出力は `utf-8`
- 緯度経度変換: 度分秒形式（`DDMMSS.SSS` 9〜10桁）→ 10進数。フォーマット不正行はスキップ
- `check_output_diff.py` の `KNOWN_DIFFS` に、旧リポジトリとの意図的差異（コード表修正済み）を記録してある
- 2019〜2021の警察署等・高速路線CSVは2019年版のみ。2020・2021に新設された署・路線は未収録（将来課題）
