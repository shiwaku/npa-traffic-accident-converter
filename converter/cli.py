"""CLI: python -m converter --year 2024"""
import argparse
import sys
from pathlib import Path

from converter.decode import decode
from converter.convert import convert
from converter.merge import merge

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / 'data'
OUTPUT_DIR = ROOT / 'output'

KNOWN_YEARS = list(range(2019, 2025))  # 既知の年次（--allで使用）
MIN_YEAR = 2019


def run_year(year):
    input_path = DATA_DIR / str(year) / f'honhyo_{year}.csv'
    if not input_path.exists():
        print(f"ERROR: {input_path} が存在しません", file=sys.stderr)
        return None
    print(f"[{year}] Step1: 緯度経度変換...")
    df_decoded = decode(year, input_path)
    print(f"[{year}] Step2: コード変換... ({len(df_decoded)}件)")
    df_converted = convert(year, df_decoded)
    return df_converted


def main():
    parser = argparse.ArgumentParser(description='警察庁交通事故統計オープンデータ コンバーター')
    parser.add_argument('--year', type=int, nargs='+',
                        help='変換する年（複数指定可）例: --year 2024 または --year 2022 2023 2024 2025')
    parser.add_argument('--all', action='store_true', help=f'{MIN_YEAR}〜最新既知年すべてを変換')
    parser.add_argument('--merge', action='store_true', help='複数年をマージして1ファイルに出力')
    args = parser.parse_args()

    if args.all:
        years = KNOWN_YEARS
    elif args.year:
        years = args.year
    else:
        parser.print_help()
        sys.exit(1)

    for y in years:
        if y < MIN_YEAR:
            print(f"ERROR: {y}年は対応範囲外です（{MIN_YEAR}年以降）", file=sys.stderr)
            sys.exit(1)

    OUTPUT_DIR.mkdir(exist_ok=True)
    results = []

    for year in years:
        df = run_year(year)
        if df is None:
            continue
        results.append((year, df))
        if not args.merge:
            out_path = OUTPUT_DIR / f'honhyo_{year}_converted.csv'
            df.to_csv(out_path, index=False, encoding='utf-8', lineterminator='\n')
            print(f"[{year}] 出力: {out_path} ({len(df)}件)")

    if args.merge and results:
        dfs = [df for _, df in results]
        merged = merge(dfs)
        year_range = f"{min(y for y, _ in results)}-{max(y for y, _ in results)}"
        out_path = OUTPUT_DIR / f'honhyo_{year_range}_converted.csv'
        merged.to_csv(out_path, index=False, encoding='utf-8', lineterminator='\n')
        print(f"[マージ] 出力: {out_path} ({len(merged)}件)")

    print("完了")
