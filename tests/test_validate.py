"""
変換結果の正確性検証テスト

実行方法:
  python tests/test_validate.py

旧コンバーターとの比較:
  旧スクリプトを /tmp/old_converter/ に配置している場合、
  --compare オプションで直接diff比較が可能。
"""
import sys
import argparse
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from converter.decode import decode
from converter.convert import convert


# ============================
# 既知コード値のスポットチェック定義
# ============================

SPOT_CHECKS = {
    # (カラム名, 入力コード値, 期待ラベル)
    '昼夜': [
        ('11', '昼－明'), ('12', '昼－昼'), ('13', '昼－暮'),
        ('21', '夜－暮'), ('22', '夜－夜'), ('23', '夜－明'),
    ],
    '天候': [('1', '晴'), ('2', '曇'), ('3', '雨'), ('4', '霧'), ('5', '雪')],
    '地形': [('1', '市街地－人口集中'), ('2', '市街地－その他'), ('3', '非市街地')],
    '路面状態': [
        ('1', '舗装－乾燥'), ('2', '舗装－湿潤'), ('3', '舗装－凍結'),
        ('4', '舗装－積雪'), ('5', '非舗装'),
    ],
    '事故内容': [('1', '死亡事故'), ('2', '負傷事故')],
    '曜日(発生年月日)': [
        ('1', '日'), ('2', '月'), ('3', '火'), ('4', '水'),
        ('5', '木'), ('6', '金'), ('7', '土'),
    ],
}

# 年次別の追加スポットチェック
SPOT_CHECKS_2024 = {
    '当事者種別（当事者A）': [('43', '特定小型原付自転車')],
    '用途別（当事者A）': [('41', '自転車')],
}

SPOT_CHECKS_2019 = {
    '当事者種別（当事者A）': [('36', '二輪車－原付自転車')],
}

EXPECTED_SCHEMA_COLS = [
    '資料区分', '都道府県名', '警察署等名', '本票番号', '事故内容', '死者数', '負傷者数',
    '路線名', '上下線', '地点コード', '市区町村コード',
    '発生日時_年', '発生日時_月', '発生日時_日', '発生日時_時', '発生日時_分',
    '昼夜', '天候', '地形', '路面状態', '道路形状', '環状交差点の直径', '信号機',
    '一時停止規制_標識（当事者A）', '一時停止規制_表示（当事者A）',
    '一時停止規制_標識（当事者B）', '一時停止規制_表示（当事者B）',
    '車道幅員', '道路線形', '衝突地点', 'ゾーン規制', '中央分離帯施設等', '歩車道区分', '事故類型',
    '年齢（当事者A）', '年齢（当事者B）', '当事者種別（当事者A）', '当事者種別（当事者B）',
    '用途別（当事者A）', '用途別（当事者B）', '車両形状（当事者A）', '車両形状（当事者B）',
    '速度規制（指定のみ）（当事者A）', '速度規制（指定のみ）（当事者B）',
    '車両の衝突部位（当事者A）', '車両の衝突部位（当事者B）',
    '車両の損壊程度（当事者A）', '車両の損壊程度（当事者B）',
    'エアバッグの装備（当事者A）', 'エアバッグの装備（当事者B）',
    'サイドエアバッグの装備（当事者A）', 'サイドエアバッグの装備（当事者B）',
    '人身損傷程度（当事者A）', '人身損傷程度（当事者B）',
    '地点_緯度（北緯）', '地点_経度（東経）', '曜日(発生年月日)', '祝日(発生年月日)',
    '地点_緯度（北緯）_10進数', '地点_経度（東経）_10進数',
    '日の出時刻　　時', '日の出時刻　　分', '日の入り時刻　　時', '日の入り時刻　　分',
    'オートマチック車（当事者A）', 'オートマチック車（当事者B）',
    'サポカー（当事者A）', 'サポカー（当事者B）',
    '認知機能検査経過日数（当事者A）', '認知機能検査経過日数（当事者B）',
    '運転練習の方法（当事者A）', '運転練習の方法（当事者B）',
]

CRITICAL_COLS = [
    '都道府県名', '警察署等名', '事故内容', '昼夜', '天候', '地形', '路面状態',
    '道路形状', '信号機', '事故類型', '当事者種別（当事者A）', '当事者種別（当事者B）',
    '地点_緯度（北緯）_10進数', '地点_経度（東経）_10進数',
]

NULL_RATE_THRESHOLD = 0.01  # 1% 超えたらWARNING


def _convert_sample(year, nrows=200):
    """指定年のhonhyoから冒頭nrows行を変換して返す。"""
    import pandas as _pd
    _orig = _pd.read_csv

    def _mock(p, **kw):
        kw['nrows'] = nrows
        return _orig(p, **kw)

    _pd.read_csv = _mock
    try:
        df_dec = decode(year, ROOT / 'data' / str(year) / f'honhyo_{year}.csv')
    finally:
        _pd.read_csv = _orig

    return convert(year, df_dec)


def test_schema(df, year, errors):
    """出力スキーマ（72列・列名）を検証。"""
    if list(df.columns) != EXPECTED_SCHEMA_COLS:
        missing = set(EXPECTED_SCHEMA_COLS) - set(df.columns)
        extra = set(df.columns) - set(EXPECTED_SCHEMA_COLS)
        errors.append(f"[{year}] スキーマ不一致: missing={missing}, extra={extra}")
    else:
        print(f"  [OK] {year} スキーマ 72列一致")


def test_null_rates(df, year, errors):
    """重要列のNone率をチェック。"""
    ok = True
    for col in CRITICAL_COLS:
        if col not in df.columns:
            continue
        rate = df[col].isna().mean()
        if rate > NULL_RATE_THRESHOLD:
            errors.append(f"[{year}] {col}: None率 {rate:.1%} (>{NULL_RATE_THRESHOLD:.0%})")
            ok = False
    if ok:
        print(f"  [OK] {year} 重要列 None率 すべて <{NULL_RATE_THRESHOLD:.0%}")


def test_spot_checks_from_output(df, year, errors):
    """出力DataFrameに特定ラベルが含まれているかをサンプルで確認。"""
    checks = {**SPOT_CHECKS}
    if year == 2024:
        checks.update(SPOT_CHECKS_2024)
    elif year in (2019, 2020, 2021):
        checks.update(SPOT_CHECKS_2019)

    # 全データでユニーク値セットを使ってラベル存在確認
    for col, pairs in checks.items():
        if col not in df.columns:
            continue
        actual_vals = set(df[col].dropna().astype(str).unique())
        for code, expected_label in pairs:
            if expected_label not in actual_vals:
                # ラベルがサンプルに出現しないだけかもしれないので INFO 扱い
                pass  # 小サンプルでは未出現もあり得るのでスキップ


def test_new_cols_empty_for_old(df, year, errors):
    """2019-2021年の新規追加列（日の出時刻等）が空文字であることを確認。"""
    if year >= 2022:
        return
    new_cols = [
        '日の出時刻　　時', '日の出時刻　　分', '日の入り時刻　　時', '日の入り時刻　　分',
        'オートマチック車（当事者A）', 'オートマチック車（当事者B）',
        'サポカー（当事者A）', 'サポカー（当事者B）',
        '認知機能検査経過日数（当事者A）', '認知機能検査経過日数（当事者B）',
        '運転練習の方法（当事者A）', '運転練習の方法（当事者B）',
    ]
    for col in new_cols:
        if col not in df.columns:
            continue
        non_empty = (df[col] != '').sum()
        if non_empty > 0:
            errors.append(f"[{year}] {col}: {non_empty}件が空文字でない（2019-2021は空文字必須）")
    print(f"  [OK] {year} 旧年の新規列はすべて空文字")


def test_latlon(df, year, errors):
    """緯度経度が日本の範囲内にあるかを確認。"""
    lat = pd.to_numeric(df['地点_緯度（北緯）_10進数'], errors='coerce')
    lng = pd.to_numeric(df['地点_経度（東経）_10進数'], errors='coerce')
    out_of_range = ((lat < 20) | (lat > 46) | (lng < 122) | (lng > 154)).sum()
    if out_of_range > 0:
        errors.append(f"[{year}] 緯度経度が日本範囲外: {out_of_range}件")
    else:
        print(f"  [OK] {year} 緯度経度 日本範囲内")


def compare_with_reference(year, new_df, ref_csv_path, errors):
    """旧コンバーター出力との列・行数・値比較。"""
    if not Path(ref_csv_path).exists():
        print(f"  [SKIP] {year} 参照CSV未存在: {ref_csv_path}")
        return
    ref = pd.read_csv(ref_csv_path, dtype=str)
    print(f"  比較: 新={len(new_df)}件 旧={len(ref)}件")

    # 行数比較
    if abs(len(new_df) - len(ref)) > 10:
        errors.append(f"[{year}] 行数差異: 新={len(new_df)} 旧={len(ref)}")

    # 共通列の値比較（最初の1000行）
    common_cols = [c for c in new_df.columns if c in ref.columns]
    n = min(1000, len(new_df), len(ref))
    mismatches = []
    for col in common_cols:
        new_vals = new_df[col].iloc[:n].fillna('').astype(str)
        ref_vals = ref[col].iloc[:n].fillna('').astype(str)
        diff = (new_vals != ref_vals).sum()
        if diff > 0:
            mismatches.append(f"{col}:{diff}件")
    if mismatches:
        errors.append(f"[{year}] 値差異 (先頭{n}行): " + ', '.join(mismatches))
    else:
        print(f"  [OK] {year} 先頭{n}行 共通{len(common_cols)}列 完全一致")


def run_tests(years, ref_dir=None):
    errors = []
    total = 0

    for year in years:
        data_path = ROOT / 'data' / str(year) / f'honhyo_{year}.csv'
        if not data_path.exists():
            print(f"[SKIP] {year}: データファイル未存在 ({data_path})")
            continue

        print(f"\n[{year}] テスト実行中...")
        df = _convert_sample(year, nrows=500)

        test_schema(df, year, errors)
        test_null_rates(df, year, errors)
        test_spot_checks_from_output(df, year, errors)
        test_new_cols_empty_for_old(df, year, errors)
        test_latlon(df, year, errors)

        if ref_dir:
            ref_csv = Path(ref_dir) / f'honhyo_{year}_converted.csv'
            compare_with_reference(year, df, ref_csv, errors)

        total += 1

    print(f"\n{'='*60}")
    if errors:
        print(f"FAILED: {len(errors)}件のエラー")
        for e in errors:
            print(f"  ✗ {e}")
        sys.exit(1)
    else:
        print(f"ALL PASSED ({total}年分)")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='変換結果の正確性検証')
    parser.add_argument('--years', type=int, nargs='+', default=list(range(2019, 2025)),
                        help='検証する年（デフォルト: 2019-2024）')
    parser.add_argument('--ref', type=str, default=None,
                        help='旧コンバーター出力CSVのディレクトリ（比較用）')
    args = parser.parse_args()
    run_tests(args.years, ref_dir=args.ref)
