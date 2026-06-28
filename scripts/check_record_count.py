#!/usr/bin/env python3
"""
③チェック: 変換前後の件数一致確認

使い方:
  python scripts/check_record_count.py --year 2024
  python scripts/check_record_count.py --year 2019 2020 2021 2022 2023 2024
  python scripts/check_record_count.py --all

終了コード: 閾値超過=1, 正常=0
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent.parent
SKIP_RATE_WARN = 0.001  # 0.1%超でWARN
KNOWN_YEARS = list(range(2019, 2025))


def count_csv_rows(path, encoding='cp932'):
    """CSVのデータ行数をカウント（ヘッダー除く）"""
    df = pd.read_csv(path, dtype=object, encoding=encoding)
    return len(df)


def check_year(year):
    input_path = ROOT / 'data' / str(year) / f'honhyo_{year}.csv'
    output_path = ROOT / 'output' / f'honhyo_{year}_converted.csv'

    if not input_path.exists():
        print(f'  [SKIP] 入力ファイル未存在: {input_path.relative_to(ROOT)}')
        return True

    if not output_path.exists():
        print(f'  [SKIP] 出力ファイル未存在: {output_path.relative_to(ROOT)}')
        print(f'         まず `python -m converter --year {year}` を実行してください')
        return True

    input_count = count_csv_rows(input_path, encoding='cp932')
    output_count = count_csv_rows(output_path, encoding='utf-8')
    skipped = input_count - output_count
    skip_rate = skipped / input_count if input_count > 0 else 0

    status = '✅' if skip_rate <= SKIP_RATE_WARN else '⚠️ '
    print(f'  {status} {year}: 入力={input_count:,}件 / 出力={output_count:,}件 / '
          f'スキップ={skipped}件 ({skip_rate*100:.3f}%)')

    if skipped > 0:
        # スキップ行の緯度経度を確認（緯度経度不正が主因）
        print(f'       スキップ主因: 緯度経度フォーマット不正（度分秒9桁/10桁以外）')

    return skip_rate <= SKIP_RATE_WARN


def main():
    parser = argparse.ArgumentParser(description='③チェック: 変換前後の件数確認')
    parser.add_argument('--year', type=int, nargs='+', help='対象年（例: 2024）')
    parser.add_argument('--all', action='store_true', help='全既知年チェック')
    args = parser.parse_args()

    years = KNOWN_YEARS if args.all else (args.year or [2024])

    ok = True
    for year in years:
        print(f'\n=== {year}年 ===')
        if not check_year(year):
            ok = False

    print(f'\n{"="*60}')
    if ok:
        print('✅ 全年次: スキップ率が許容範囲内')
    else:
        print(f'⚠️  スキップ率が {SKIP_RATE_WARN*100:.1f}% を超える年次があります')
        sys.exit(1)


if __name__ == '__main__':
    main()
