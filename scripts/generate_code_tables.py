#!/usr/bin/env python3
"""
公式コード表xlsxから年次別CSV（警察署等・高速路線・トンネル番号）を生成

使い方:
  python scripts/generate_code_tables.py --year 2025

data/{year}/codebook_{year}.xlsx の該当シートを、既存CSVと同じ形式
（UTF-8 BOM付き・CRLF・先頭5行が項目名/適用/説明/空行/見出し）で
code_tables/{year}/ に書き出す。生成後は ①チェックで xlsx との一致を確認すること。
"""
import argparse
import csv
import sys

import openpyxl

from _common import ROOT

# (シート名, 出力CSV, 列数)
TABLES = [
    ('警察署等',     '3_koudohyou_keisatusyotoukoudo.csv',          5),
    ('路線 (高速)',  '9_koudohyou_rosen_kousokujidousyasenyou.csv', 4),
    ('トンネル番号', '53_koudohyou_tonnerubangou.csv',              6),
]


def sheet_rows(ws, ncol):
    """xlsxの2行目以降・B列以降を ncol 列の文字列行として返す（末尾の空行は除く）"""
    rows = []
    for r in ws.iter_rows(min_row=2, values_only=True):
        cells = ['' if v is None else str(v).strip() for v in r[1:1 + ncol]]
        rows.append(cells + [''] * (ncol - len(cells)))
    while rows and not any(rows[-1]):
        rows.pop()
    return rows


def main():
    parser = argparse.ArgumentParser(description='公式コード表xlsxから年次別コード表CSVを生成')
    parser.add_argument('--year', type=int, required=True, help='対象年（例: 2025）')
    args = parser.parse_args()

    xlsx_path = ROOT / 'data' / str(args.year) / f'codebook_{args.year}.xlsx'
    if not xlsx_path.exists():
        print(f'ERROR: {xlsx_path} が存在しません', file=sys.stderr)
        sys.exit(1)

    wb = openpyxl.load_workbook(xlsx_path)
    out_dir = ROOT / 'code_tables' / str(args.year)
    out_dir.mkdir(parents=True, exist_ok=True)

    for sheet_name, filename, ncol in TABLES:
        rows = sheet_rows(wb[sheet_name], ncol)
        out_path = out_dir / filename
        with open(out_path, 'w', encoding='utf-8-sig', newline='') as f:
            csv.writer(f, lineterminator='\r\n').writerows(rows)
        print(f'  {out_path.relative_to(ROOT)}: {len(rows) - 5}件')


if __name__ == '__main__':
    main()
