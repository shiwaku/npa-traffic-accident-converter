#!/usr/bin/env python3
"""
①〜⑤の全チェックをまとめて実行

使い方:
  python scripts/run_all_checks.py --year 2024
  python scripts/run_all_checks.py --year 2022 2023 2024
  python scripts/run_all_checks.py --all

  # ②（旧リポジトリとの比較）を含む場合
  python scripts/run_all_checks.py --year 2024 --with-diff

  # 意図的差異を除外した②チェック
  python scripts/run_all_checks.py --year 2022 --with-diff --known-diffs

終了コード: いずれかが失敗=1, 全て成功=0
"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
KNOWN_YEARS = list(range(2019, 2025))

CHECKS = [
    # (番号, 説明, スクリプト名, 追加オプション取得関数)
    ('①', '公式コード表 vs 変換用コード表（CSV+辞書）', 'check_codetable_vs_official.py', None),
    ('②', '旧リポジトリ出力 vs 新コンバーター出力',      'check_output_diff.py',           'diff_opts'),
    ('③', '変換前後の件数確認',                          'check_record_count.py',           None),
    ('④', '未定義コード検出',                            'check_undefined_codes.py',        None),
    ('⑤', 'ファイル定義書とのカラム構成確認',             'check_file_definition.py',        None),
]


def run_check(num, desc, script, extra_args, year_args):
    script_path = ROOT / 'scripts' / script
    cmd = [sys.executable, str(script_path)] + year_args + extra_args
    print(f'\n{"="*60}')
    print(f'{num} {desc}')
    print(f'{"="*60}')
    result = subprocess.run(cmd, cwd=ROOT)
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description='①〜⑤ 全チェックまとめ実行')
    parser.add_argument('--year', type=int, nargs='+', help='対象年（例: 2024）')
    parser.add_argument('--all', action='store_true', help='全既知年チェック')
    parser.add_argument('--with-diff', action='store_true', help='②旧リポジトリとの比較を含める')
    parser.add_argument('--known-diffs', action='store_true', help='②で既知の意図的差異を除外')
    args = parser.parse_args()

    if args.all:
        year_args = ['--all']
        year_strs = [str(y) for y in KNOWN_YEARS]
    elif args.year:
        year_args = ['--year'] + [str(y) for y in args.year]
        year_strs = [str(y) for y in args.year]
    else:
        parser.print_help()
        sys.exit(1)

    results = {}
    for num, desc, script, extra_key in CHECKS:
        if num == '②' and not args.with_diff:
            print(f'\n[SKIP] {num} {desc}（--with-diff を付けて有効化）')
            continue

        extra = []
        if extra_key == 'diff_opts' and args.known_diffs:
            extra = ['--known-diffs']

        ok = run_check(num, desc, script, extra, year_args)
        results[num] = ok

    # サマリー
    print(f'\n\n{"="*60}')
    print('  チェック結果サマリー')
    print(f'{"="*60}')
    all_ok = True
    for num, desc, script, _ in CHECKS:
        if num not in results:
            print(f'  {num} {desc}: SKIP')
            continue
        status = '✅ PASS' if results[num] else '❌ FAIL'
        if not results[num]:
            all_ok = False
        print(f'  {num} {desc}: {status}')

    print()
    if all_ok:
        print('✅ 全チェック PASS')
    else:
        print('❌ FAIL したチェックがあります。上記の詳細を確認してください。')
        sys.exit(1)


if __name__ == '__main__':
    main()
