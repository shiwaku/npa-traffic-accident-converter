#!/usr/bin/env python3
"""
年次間のコード表差分チェックスクリプト

使い方:
  python scripts/check_codebook_diff.py --base 2024 --new 2025

各シートの表見出し行（「コード」「コード（都道府県）」…）を探し、
「コード」で始まる列をすべてキー（警察署等なら 都道府県+警察署等）として比較する。
表のないシート（発生日時など）や表の上にある説明文は、文面の変更として比較する。
"""
import argparse

import openpyxl

from _common import ROOT


def _cell(v):
    return '' if v is None else str(v).replace('\n', '').strip()


def extract_sheet(ws):
    """シートから (コード表, 説明文リスト) を返す。

    コード表: {キー(タプル): 値(タプル)}。値はキー以外の見出し付き列（区分・名称・備考など）。
    説明文: 表見出しより上の行（表がなければ全行）の文字列。
    """
    rows = [[_cell(v) for v in r] for r in ws.iter_rows(values_only=True)]
    header_idx = next(
        (i for i, r in enumerate(rows) if any(c.startswith('コード') for c in r)), None)

    notes_rows = rows if header_idx is None else rows[:header_idx]
    notes = [' '.join(c for c in r if c) for r in notes_rows]
    notes = [n for n in notes if n]
    if header_idx is None:
        return {}, notes

    header = rows[header_idx]
    key_cols = [i for i, c in enumerate(header) if c.startswith('コード')]
    val_cols = [i for i, c in enumerate(header) if c and i not in key_cols]

    codes = {}
    for r in rows[header_idx + 1:]:
        key = tuple(r[i] if i < len(r) else '' for i in key_cols)
        if not any(key):
            continue
        codes[key] = tuple(r[i] if i < len(r) else '' for i in val_cols)
    return codes, notes


def _fmt_key(key):
    return '-'.join(key)


def _fmt_val(val):
    return ' / '.join(v for v in val if v)


def compare_codebooks(base_year: int, new_year: int):
    base_path = ROOT / 'data' / str(base_year) / f'codebook_{base_year}.xlsx'
    new_path = ROOT / 'data' / str(new_year) / f'codebook_{new_year}.xlsx'

    if not base_path.exists():
        print(f"ERROR: {base_path} が存在しません")
        return
    if not new_path.exists():
        print(f"ERROR: {new_path} が存在しません")
        print(f"  → data/{new_year}/codebook_{new_year}.xlsx をダウンロードしてから実行してください")
        return

    base_wb = openpyxl.load_workbook(base_path)
    new_wb = openpyxl.load_workbook(new_path)

    print(f"\n{'='*60}")
    print(f" コード表差分チェック: {base_year} → {new_year}")
    print(f"{'='*60}")

    all_sheets = sorted(set(base_wb.sheetnames) | set(new_wb.sheetnames))
    has_diff = False

    for sheet_name in all_sheets:
        if sheet_name not in base_wb.sheetnames:
            print(f"\n[NEW SHEET] {sheet_name}")
            has_diff = True
            continue
        if sheet_name not in new_wb.sheetnames:
            print(f"\n[DELETED SHEET] {sheet_name}")
            has_diff = True
            continue

        base_codes, base_notes = extract_sheet(base_wb[sheet_name])
        new_codes, new_notes = extract_sheet(new_wb[sheet_name])

        added = {k: v for k, v in new_codes.items() if k not in base_codes}
        removed = {k: v for k, v in base_codes.items() if k not in new_codes}
        changed = {
            k: (base_codes[k], new_codes[k])
            for k in new_codes
            if k in base_codes and base_codes[k] != new_codes[k]
        }
        notes_changed = base_notes != new_notes

        if added or removed or changed or notes_changed:
            has_diff = True
            print(f"\n[変更あり] {sheet_name}  ({len(base_codes)}件 → {len(new_codes)}件)")
            for k, v in sorted(added.items()):
                print(f"  + 追加  {_fmt_key(k):>16}: {_fmt_val(v)}")
            for k, v in sorted(removed.items()):
                print(f"  - 削除  {_fmt_key(k):>16}: {_fmt_val(v)}")
            for k, (old, new) in sorted(changed.items()):
                print(f"  ~ 変更  {_fmt_key(k):>16}: {_fmt_val(old)!r} → {_fmt_val(new)!r}")
            if notes_changed:
                print("  ~ 説明文の変更:")
                for n in base_notes:
                    if n not in new_notes:
                        print(f"      - {n}")
                for n in new_notes:
                    if n not in base_notes:
                        print(f"      + {n}")

    if not has_diff:
        print(f"\n✅ 差分なし（{base_year}年と{new_year}年のコード表は同一）")
    else:
        print("\n⚠️  上記の差分を反映してください")
        print(f"   コード値の差分        → converter/codes/y{new_year}.py（y{base_year}.py をコピーして差分のみ修正）")
        print(f"   警察署等・路線・トンネル → code_tables/{new_year}/ のCSV")


def main():
    parser = argparse.ArgumentParser(description='年次間のコード表差分チェック')
    parser.add_argument('--base', type=int, required=True, help='比較元の年（例: 2024）')
    parser.add_argument('--new', type=int, required=True, help='新しい年（例: 2025）')
    args = parser.parse_args()
    compare_codebooks(args.base, args.new)


if __name__ == '__main__':
    main()
