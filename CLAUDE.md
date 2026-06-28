# CLAUDE.md

警察庁交通事故統計オープンデータ コンバーターの開発ガイド。

---

## プロジェクト概要

警察庁公開の本票CSV（Shift-JIS）を読み込み、コード値→人間可読ラベルに変換し、緯度経度（度分秒）→10進数変換して UTF-8 CSVとして出力するPythonパッケージ。

対応年次: 2019〜2024年（2025年以降はフォールバック設計済み）

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
- `__init__.py` の `get_codes(year)`: 年次→モジュールのルーティング。2024以降はy2024にフォールバック

### CSVコード表の構造

`code_tables/` 以下：

- `common/`: 都道府県コードなど年次不変のCSV
- `2019-2021/` / `2022/` / `2023/` / `2024/`: 警察署等・高速路線・トンネル番号（年次別）
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

### 2019〜2021年の警察署等・高速路線
警察庁は2022年以降、年次別の警察署等コードCSVを提供しているが、2019〜2021年分は1つのCSV（`code_tables/2019-2021/`）しか存在しない。このCSVは2019年時点の内容であり、2020年・2021年に警察署の統廃合や高速道路の新規開通があった場合、その分のコードが未収録となる。該当レコードの警察署等名・路線名は空欄で出力される。

### 2024年のトンネル番号CSV
公式コード表（`codebook_2024.xlsx` トンネル番号シート）には2024年版として3658件が記載されているが、`code_tables/2024/53_koudohyou_tonnerubangou.csv` は2023年版（3664件）をそのまま使用している。2024年に変更されたトンネル10件程度について、変換結果のトンネル名が正確でない可能性がある（入手可能な2024年版CSVがないため）。

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
| `check_codebook_diff.py` | 年次間コード表差分（新年次追加時に使用） |

### ①チェックの既知許容差異

- **SYADOUHUKUIN（車道幅員）**: xlsxが `'12,14'` のように複合コード表記。`'12'`, `'13'`, `'16'` はxlsxのみに存在するが実データには出現しないため許容
- **トンネル番号（2022・2024年）**: CSV版と公式xlsx版で一部差異あり（既知の問題）

---

## 新年次（2025年）追加手順

詳細は [ADDING_NEW_YEAR.md](ADDING_NEW_YEAR.md) を参照。概要：

1. `download.sh` の `YEAR_FILES[2025]=...` のコメントを解除
2. `./download.sh 2025`
3. `python scripts/check_codebook_diff.py --base 2024 --new 2025`
4. 差分があれば `converter/codes/y2025.py` を作成
5. `get_codes()` の else 節は自動的に y2024 → y2025 へフォールバックするため、差分なければコード変更不要
6. `python -m converter --year 2025` → `python scripts/run_all_checks.py --year 2025`

---

## 注意事項

- 入力CSVのエンコーディングは `cp932`（Shift-JIS）。出力は `utf-8`
- 緯度経度変換: 度分秒形式（`DDMMSS.SSS` 9〜10桁）→ 10進数。フォーマット不正行はスキップ
- `check_output_diff.py` の `KNOWN_DIFFS` に、旧リポジトリとの意図的差異（コード表修正済み）を記録してある
- 2019〜2021の警察署等・高速路線CSVは2019年版のみ。2020・2021に新設された署・路線は未収録（将来課題）
