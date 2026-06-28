# チェック観点と実行手順

変換データの品質を保証するための5段階チェックの観点・実行コマンド・判定基準を記述します。

---

## ① 公式コード表 vs 変換用コード表の完全一致チェック

**観点**  
警察庁の公開する公式コード表（`codebook_YYYY.xlsx`）と、変換に実際に使用するコード表（CSVファイル・Pythonコード辞書）が完全に一致すること。

**チェック対象**

| 種別 | 対象 | 保存場所 |
|------|------|---------|
| CSVファイル | 都道府県、警察署等、高速路線、トンネル番号 | `code_tables/common/` `code_tables/{year}/` |
| Pythonコード辞書 | 天候、地形、当事者種別、車両形状など全27辞書 | `converter/codes/yYYYY.py` |

**オプション**

```
python scripts/check_codetable_vs_official.py [-h] [--year YEAR [YEAR ...]] [--all]

  --year YEAR [YEAR ...]  チェックする年を指定（複数可）
  --all                   2022〜2024の全年次をチェック
```

**実行例**

```bash
python scripts/check_codetable_vs_official.py --year 2024
python scripts/check_codetable_vs_official.py --year 2022 2023 2024
python scripts/check_codetable_vs_official.py --all
```

**判定基準**  
- ✅ PASS: 全コード・全ラベルが公式xlsxと一致
- ❌ FAIL: コードの追加漏れ・ラベル差異・未収録コードが存在

**FAILした場合の対処**  
- CSVの差異 → 該当CSVファイルを公式xlsxに合わせて更新
- Pythonコード辞書の差異 → `converter/codes/yYYYY.py` を修正

---

## ② 旧リポジトリ出力 vs 新コンバーター出力の全件比較

**観点**  
旧リポジトリで公開した変換済みCSVと、新コンバーターの出力を全行・全列で比較し、意図しない差異がないこと。コード表修正による意図的な差異は別途ドキュメント化する。

**事前準備: 参照CSVの用意**

```
python scripts/generate_reference.py [-h] --year YEAR [YEAR ...]
                                     (--from-dir DIR | --clone | --baseline)

  --year YEAR [YEAR ...]  対象年を指定（必須）
  --from-dir DIR          旧リポジトリのoutputディレクトリを指定してコピー
  --clone                 旧リポジトリをgit cloneして変換を実行（OLD_REPO_URLS要設定）
  --baseline              現在のoutput/をそのまま参照として保存（初回ベースライン作成）
```

```bash
# 旧リポジトリのCSVがローカルにある場合
python scripts/generate_reference.py --from-dir /path/to/old-output --year 2024

# 初回ベースライン作成（現在の出力を参照として保存）
python scripts/generate_reference.py --baseline --year 2022 2023 2024
```

**オプション**

```
python scripts/check_output_diff.py [-h] [--year YEAR [YEAR ...]] [--all]
                                    [--verbose] [--known-diffs] [--list-known]

  --year YEAR [YEAR ...]  チェックする年を指定（複数可）
  --all                   全既知年（2019〜2024）をチェック
  --verbose               差異のある行のサンプル値を表示
  --known-diffs           意図的差異（コード表修正済み）を除外してチェック
  --list-known            登録済みの意図的差異一覧を表示して終了
```

**実行例**

```bash
# 基本
python scripts/check_output_diff.py --year 2024

# 意図的差異を除外してチェック
python scripts/check_output_diff.py --year 2022 2023 --known-diffs

# 差異の詳細（サンプル値）を表示
python scripts/check_output_diff.py --year 2024 --verbose

# 登録済みの意図的差異一覧を確認
python scripts/check_output_diff.py --list-known
```

**判定基準**  
- ✅ PASS: 全行・全列一致（または意図的差異のみ）
- ❌ FAIL: 想定外の差異が1件でも存在

**既知の意図的差異**

| 年次 | カラム | 旧値 | 新値 | 理由 |
|------|--------|------|------|------|
| 2022 | 当事者種別（当事者A/B） | `一般原付自転車` | `二輪車－原付自転車` | 旧スクリプトのコード誤りを公式xlsxに準拠して修正 |
| 2023 | 当事者種別（当事者A/B） | `一般原付自転車` | `二輪車－原付自転車` | 同上 |

---

## ③ 変換前後の件数確認

**観点**  
入力CSV（`honhyo_YYYY.csv`）の行数と変換後CSV（`honhyo_YYYY_converted.csv`）の行数が一致すること。スキップ件数が許容閾値（0.1%）以内であること。

**スキップの主な原因**  
緯度経度フォーマット不正（度分秒9桁/10桁以外）の行はスキップされる。

**オプション**

```
python scripts/check_record_count.py [-h] [--year YEAR [YEAR ...]] [--all]

  --year YEAR [YEAR ...]  チェックする年を指定（複数可）
  --all                   全既知年（2019〜2024）をチェック
```

**実行例**

```bash
python scripts/check_record_count.py --year 2024
python scripts/check_record_count.py --all
```

**判定基準**  
- ✅ PASS: スキップ率 0.1% 以下
- ⚠️ WARN: スキップ率 0.1% 超（調査が必要）

---

## ④ 未定義コード検出

**観点**  
実データ（`honhyo_YYYY.csv`）に出現するコード値が、変換辞書（Pythonコード辞書またはCSV）に全て定義されていること。未定義コードがあれば変換結果が `None`（欠損）になるため必ず検出・対処する。

**オプション**

```
python scripts/check_undefined_codes.py [-h] [--year YEAR [YEAR ...]] [--all]

  --year YEAR [YEAR ...]  チェックする年を指定（複数可）
  --all                   全既知年（2019〜2024）をチェック
```

**実行例**

```bash
python scripts/check_undefined_codes.py --year 2024
python scripts/check_undefined_codes.py --all
```

**判定基準**  
- ✅ PASS: 全コード定義済み
- ❌ FAIL: 未定義コードが存在 → 辞書またはCSVへの追加が必要

**FAILした場合の対処**  
1. 公式xlsxで当該コードの正式ラベルを確認
2. `converter/codes/yYYYY.py` の該当辞書に追加
3. ①チェックを再実行して整合性確認

---

## ⑤ ファイル定義書との列構成確認

**観点**  
入力CSV（`honhyo_YYYY.csv`）の列数・列名がファイル定義書（`fileteigisyo_YYYY.xlsx`）の本票シートと一致すること。列構成が変わった場合は `converter/decode.py` の修正が必要。

※ 2019〜2021年はxlsxが存在しない（PDFのみ）のためスキップ。

**オプション**

```
python scripts/check_file_definition.py [-h] [--year YEAR [YEAR ...]] [--all]

  --year YEAR [YEAR ...]  チェックする年を指定（複数可）
  --all                   全年次チェック（2019〜2021はスキップ）
```

**実行例**

```bash
# 2022以降のみ意味あり
python scripts/check_file_definition.py --year 2022 2023 2024
python scripts/check_file_definition.py --all
```

**判定基準**  
- ✅ PASS: 列数・列名が完全一致
- ❌ FAIL: 列数・列名の差異あり → `converter/decode.py` の更新が必要

---

## まとめて実行

**オプション**

```
python scripts/run_all_checks.py [-h] [--year YEAR [YEAR ...]] [--all]
                                 [--with-diff] [--known-diffs]

  --year YEAR [YEAR ...]  チェックする年を指定（複数可）
  --all                   全既知年（2019〜2024）をチェック
  --with-diff             ②旧リポジトリとの比較も実行（参照CSV要準備）
  --known-diffs           ②で既知の意図的差異を除外してチェック
```

**実行例**

```bash
# ①③④⑤を実行（基本）
python scripts/run_all_checks.py --year 2024

# ②も含めて実行
python scripts/run_all_checks.py --year 2024 --with-diff

# ②で意図的差異を除外
python scripts/run_all_checks.py --year 2022 2023 --with-diff --known-diffs

# 全年次
python scripts/run_all_checks.py --all
```

---

## 新年次（例: 2025年）追加時のチェック手順

1. `./download.sh 2025` でデータ・コード表をダウンロード
2. `python scripts/check_codebook_diff.py --base 2024 --new 2025` でコード表差分を確認
3. 差分があれば `converter/codes/y2025.py` を作成
4. `python -m converter --year 2025` で変換
5. `python scripts/run_all_checks.py --year 2025` で全チェック

詳細は [ADDING_NEW_YEAR.md](ADDING_NEW_YEAR.md) を参照。
