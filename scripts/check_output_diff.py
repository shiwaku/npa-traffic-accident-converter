#!/usr/bin/env python3
"""
②チェック: 旧リポジトリ出力 vs 新コンバーター出力の全件比較

前提: scripts/generate_reference.py で reference/honhyo_{year}_converted.csv を準備済み

使い方:
  python scripts/check_output_diff.py --year 2024
  python scripts/check_output_diff.py --year 2022 2023 2024
  python scripts/check_output_diff.py --all

  # 差異を詳細表示
  python scripts/check_output_diff.py --year 2024 --verbose

  # 既知の意図的差異を無視（コード表修正による差異など）
  python scripts/check_output_diff.py --year 2022 --known-diffs

終了コード: 予期しない差異あり=1, 一致（または許容差異のみ）=0
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent.parent
REF_DIR = ROOT / 'reference'
OUT_DIR = ROOT / 'output'
KNOWN_YEARS = list(range(2019, 2025))

# 意図的に旧出力と異なることが確認済みの差異
# 形式: {year: [(column, old_value, new_value, reason), ...]}
KNOWN_DIFFS = {
    2022: [
        # 2022年の旧スクリプトは当事者種別'36'を'一般原付自転車'とコードしていた
        # 公式xlsxでは'二輪車－一般原付自転車'が正しいため修正済み
        ('当事者種別（当事者A）', '一般原付自転車', '二輪車－一般原付自転車', '旧スクリプトのコード誤りを修正'),
        ('当事者種別（当事者B）', '一般原付自転車', '二輪車－一般原付自転車', '旧スクリプトのコード誤りを修正'),
    ],
    2023: [
        ('当事者種別（当事者A）', '一般原付自転車', '二輪車－一般原付自転車', '旧スクリプトのコード誤りを修正'),
        ('当事者種別（当事者B）', '一般原付自転車', '二輪車－一般原付自転車', '旧スクリプトのコード誤りを修正'),
    ],
}


def load_csv(path):
    return pd.read_csv(path, dtype=str, encoding='utf-8').fillna('')


def check_year(year, verbose=False, ignore_known=False):
    ref_path = REF_DIR / f'honhyo_{year}_converted.csv'
    out_path = OUT_DIR / f'honhyo_{year}_converted.csv'

    if not ref_path.exists():
        print(f'  [SKIP] 参照CSV未存在: {ref_path.relative_to(ROOT)}')
        print(f'         先に: python scripts/generate_reference.py --baseline --year {year}')
        return True

    if not out_path.exists():
        print(f'  [SKIP] 出力CSV未存在: {out_path.relative_to(ROOT)}')
        print(f'         先に: python -m converter --year {year}')
        return True

    ref_df = load_csv(ref_path)
    out_df = load_csv(out_path)

    # 行数チェック
    if len(ref_df) != len(out_df):
        print(f'  ❌ {year}: 行数不一致 ref={len(ref_df):,} / out={len(out_df):,}')
        return False

    # カラムチェック
    ref_cols = set(ref_df.columns)
    out_cols = set(out_df.columns)
    only_ref = ref_cols - out_cols
    only_out = out_cols - ref_cols
    if only_ref or only_out:
        if only_ref:
            print(f'  ❌ {year}: 参照のみのカラム: {sorted(only_ref)}')
        if only_out:
            print(f'  ❌ {year}: 出力のみのカラム: {sorted(only_out)}')
        return False

    # 共通カラムでの全件比較
    common_cols = [c for c in ref_df.columns if c in out_cols]

    known_year_diffs = KNOWN_DIFFS.get(year, []) if ignore_known else []
    known_pairs = {
        (col, old_v): new_v
        for col, old_v, new_v, _ in known_year_diffs
    }

    diff_cols = {}
    for col in common_cols:
        mask = ref_df[col] != out_df[col]
        if not mask.any():
            continue

        # 既知差異を除外
        actual_diffs = mask.copy()
        for (known_col, old_v), new_v in known_pairs.items():
            if col != known_col:
                continue
            known_mask = (ref_df[col] == old_v) & (out_df[col] == new_v)
            actual_diffs = actual_diffs & ~known_mask

        if actual_diffs.any():
            diff_cols[col] = int(actual_diffs.sum())

    if diff_cols:
        total_diff_rows = sum(diff_cols.values())
        print(f'  ❌ {year}: {len(diff_cols)}カラムで差異あり（合計{total_diff_rows:,}件）')
        for col, cnt in sorted(diff_cols.items(), key=lambda x: -x[1])[:20]:
            print(f'     {col}: {cnt:,}件')
            if verbose:
                mask = ref_df[col] != out_df[col]
                sample = ref_df[mask][[col]].copy()
                sample['out'] = out_df[mask][col].values
                for _, r in sample.head(3).iterrows():
                    print(f'       ref={r[col]!r} / out={r["out"]!r}')
        return False
    else:
        known_cnt = sum(
            int((ref_df[col] == old_v).sum())
            for col, old_v, new_v, _ in known_year_diffs
        )
        msg = f'  ✅ {year}: 全{len(ref_df):,}行一致'
        if known_cnt:
            msg += f'（意図的差異 {known_cnt}件 除外済み）'
        print(msg)
        return True


def print_known_diffs():
    print('\n既知の意図的差異（--known-diffs で除外）:')
    for year, diffs in sorted(KNOWN_DIFFS.items()):
        for col, old_v, new_v, reason in diffs:
            print(f'  {year} / {col}: {old_v!r} → {new_v!r}')
            print(f'    理由: {reason}')


def main():
    parser = argparse.ArgumentParser(description='②チェック: 旧リポジトリ出力 vs 新コンバーター出力')
    parser.add_argument('--year', type=int, nargs='+', help='対象年（例: 2024）')
    parser.add_argument('--all', action='store_true', help='全既知年チェック')
    parser.add_argument('--verbose', action='store_true', help='差異の詳細を表示')
    parser.add_argument('--known-diffs', action='store_true', help='意図的差異を除外してチェック')
    parser.add_argument('--list-known', action='store_true', help='既知の意図的差異一覧を表示して終了')
    args = parser.parse_args()

    if args.list_known:
        print_known_diffs()
        return

    years = KNOWN_YEARS if args.all else (args.year or [2024])

    ok = True
    for year in years:
        print(f'\n=== {year}年 ===')
        if not check_year(year, verbose=args.verbose, ignore_known=args.known_diffs):
            ok = False

    print(f'\n{"="*60}')
    if ok:
        print('✅ 全年次: 旧リポジトリ出力との差異なし（またはスキップ）')
    else:
        print('❌ 差異があります。上記の詳細を確認してください。')
        if not args.known_diffs:
            print('   ヒント: --known-diffs で意図的差異を除外できます')
        sys.exit(1)


if __name__ == '__main__':
    main()
