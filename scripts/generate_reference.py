#!/usr/bin/env python3
"""
②チェック用: 旧リポジトリの出力CSVを reference/ ディレクトリに準備する

使い方（いずれかの方法で参照データを準備）:

方法A: 旧リポジトリをローカルにクローン済みの場合
  python scripts/generate_reference.py --from-dir /path/to/old-repo/output --year 2024

方法B: 旧リポジトリのURLを指定してクローン・実行
  python scripts/generate_reference.py --clone --year 2024

方法C: 現在の output/ を参照用にコピー（初回ベースライン作成）
  python scripts/generate_reference.py --baseline --year 2024

出力: reference/honhyo_{year}_converted.csv
"""
import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).parent.parent
REF_DIR = ROOT / 'reference'

# 旧リポジトリURL（年次別）
OLD_REPO_URLS = {
    2019: None,  # URLが判明したら設定
    2020: None,
    2021: None,
    2022: None,
    2023: None,
    2024: None,
}
# TODO: 旧リポジトリのGitHub URLが確定したらここに設定してください
# 例:
# OLD_REPO_URLS[2024] = 'https://github.com/xxx/npa-2024-converter'


def from_dir(src_dir, year):
    """既存ディレクトリから参照CSVをコピー"""
    src = Path(src_dir) / f'honhyo_{year}_converted.csv'
    if not src.exists():
        print(f'ERROR: {src} が存在しません')
        return False
    REF_DIR.mkdir(exist_ok=True)
    dst = REF_DIR / f'honhyo_{year}_converted.csv'
    shutil.copy2(src, dst)
    print(f'✅ {year}: 参照CSVをコピー → {dst.relative_to(ROOT)}')
    return True


def baseline(year):
    """現在の output/ をベースラインとして reference/ にコピー"""
    src = ROOT / 'output' / f'honhyo_{year}_converted.csv'
    if not src.exists():
        print(f'ERROR: {src} が存在しません。まず `python -m converter --year {year}` を実行してください')
        return False
    REF_DIR.mkdir(exist_ok=True)
    dst = REF_DIR / f'honhyo_{year}_converted.csv'
    shutil.copy2(src, dst)
    print(f'✅ {year}: 現在の出力をベースラインとして保存 → {dst.relative_to(ROOT)}')
    return True


def clone_and_run(year):
    """旧リポジトリをクローンして変換を実行"""
    url = OLD_REPO_URLS.get(year)
    if not url:
        print(f'ERROR: {year}年の旧リポジトリURLが設定されていません')
        print('  scripts/generate_reference.py の OLD_REPO_URLS を更新してください')
        return False

    with tempfile.TemporaryDirectory() as tmpdir:
        print(f'  クローン中: {url}')
        result = subprocess.run(['git', 'clone', '--depth=1', url, tmpdir], capture_output=True, text=True)
        if result.returncode != 0:
            print(f'ERROR: git clone 失敗: {result.stderr}')
            return False

        # 旧リポジトリの変換スクリプトを実行（リポジトリ構造に依存）
        # TODO: 旧リポジトリの実行方法に合わせて修正
        print('  変換実行中...')
        run_script = Path(tmpdir) / 'run.sh'
        if run_script.exists():
            subprocess.run(['bash', 'run.sh'], cwd=tmpdir)
        else:
            print('  WARNING: run.sh が見つかりません。手動での実行が必要です')
            return False

        # 出力CSVを参照ディレクトリにコピー
        output_candidates = list(Path(tmpdir).glob(f'*{year}*convert*.csv'))
        if not output_candidates:
            print(f'  ERROR: 変換済みCSVが見つかりません: {tmpdir}')
            return False

        REF_DIR.mkdir(exist_ok=True)
        dst = REF_DIR / f'honhyo_{year}_converted.csv'
        shutil.copy2(output_candidates[0], dst)
        print(f'✅ {year}: 旧リポジトリ出力を保存 → {dst.relative_to(ROOT)}')
        return True


def main():
    parser = argparse.ArgumentParser(description='②チェック用参照CSV準備')
    parser.add_argument('--year', type=int, nargs='+', required=True, help='対象年（例: 2024）')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--from-dir', metavar='DIR', help='旧リポジトリ出力ディレクトリ')
    group.add_argument('--clone', action='store_true', help='旧リポジトリをクローンして実行')
    group.add_argument('--baseline', action='store_true', help='現在のoutput/をベースラインとして保存')
    args = parser.parse_args()

    ok = True
    for year in args.year:
        print(f'\n=== {year}年 ===')
        if args.from_dir:
            if not from_dir(args.from_dir, year):
                ok = False
        elif args.clone:
            if not clone_and_run(year):
                ok = False
        elif args.baseline:
            if not baseline(year):
                ok = False

    if ok:
        print(f'\n✅ reference/ ディレクトリに参照CSVを準備しました')
        print(f'   次のステップ: python scripts/check_output_diff.py --year {" ".join(str(y) for y in args.year)}')
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
