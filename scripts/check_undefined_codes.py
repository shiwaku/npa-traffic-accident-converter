#!/usr/bin/env python3
"""
④チェック: 実データに出現するコード値が変換辞書/CSVに網羅されているか

使い方:
  python scripts/check_undefined_codes.py --year 2024
  python scripts/check_undefined_codes.py --year 2022 2023 2024
  python scripts/check_undefined_codes.py --all

終了コード: 未定義コードあり=1, 全定義済み=0
"""
import argparse
import csv
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent.parent
KNOWN_YEARS = list(range(2019, 2025))

# 元データ（警察庁CSV）に含まれる公式コード表外の値。
# 各1件のみ出現しており、データ入力ミスと判断。変換結果は空欄になる。
KNOWN_DATA_ANOMALIES = {
    2022: {
        '速度規制（指定のみ）（当事者A）': {'40'},  # 公式コード表になし。'03'(40km/h以下)の誤入力と推測
        '祝日(発生年月日)':             {'0'},   # 公式コード表になし（沖縄県・本票番号0030）
    },
}


def _load_csv_keys(filepath, key_col_indices, skip_rows=5):
    """CSVからキー集合を抽出"""
    keys = set()
    with open(filepath, encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        for _ in range(skip_rows):
            next(reader, None)
        for row in reader:
            if not row or all(not c.strip() for c in row):
                continue
            try:
                key = ''.join(str(row[c]).strip() for c in key_col_indices)
                if key.strip():
                    keys.add(key)
            except IndexError:
                pass
    return keys


def build_lookup(year):
    """年次ごとの有効コード集合を返す {カラム名: set(有効コード)}"""
    from converter.codes import get_codes
    from converter.convert import _year_dir

    c = get_codes(year)
    common_dir = ROOT / 'code_tables' / 'common'
    year_dir = _year_dir(year)
    is_new = year >= 2022

    # Python辞書: str(key)に正規化
    def dict_keys(d):
        return {str(k) for k in d.keys()}

    # CSVキー集合
    todouhuken_keys = _load_csv_keys(common_dir / '2_koudohyou_todouhukenkoudo.csv', [0])
    keisatusyo_keys = _load_csv_keys(year_dir / '3_koudohyou_keisatusyotoukoudo.csv', [0, 1])
    rosenkousoku_keys = _load_csv_keys(year_dir / '9_koudohyou_rosen_kousokujidousyasenyou.csv', [0, 1])

    lookup = {
        '都道府県コード':              todouhuken_keys,
        '昼夜':                      dict_keys(c.TYUUYA),
        '天候':                      dict_keys(c.TENKOU),
        '地形':                      dict_keys(c.TIKEI),
        '路面状態':                   dict_keys(c.ROMENJYOUTAI),
        '道路形状':                   dict_keys(c.DOUROKEIJYOU),
        '信号機':                     dict_keys(c.SINGOUKI),
        '一時停止規制_標識（当事者A）':   dict_keys(c.ITIJITEISIKISEI_HYOUSIKI),
        '一時停止規制_標識（当事者B）':   dict_keys(c.ITIJITEISIKISEI_HYOUSIKI),
        '一時停止規制_表示（当事者A）':   dict_keys(c.ITIJITEISIKISEI_HYOUJI),
        '一時停止規制_表示（当事者B）':   dict_keys(c.ITIJITEISIKISEI_HYOUJI),
        '車道幅員':                   dict_keys(c.SYADOUHUKUIN),
        '道路線形':                   dict_keys(c.DOUROSENKEI),
        '衝突地点':                   dict_keys(c.SYOUTOTUTITEN),
        'ゾーン規制':                  dict_keys(c.ZOONKISEI),
        '中央分離帯施設等':             dict_keys(c.TYUUOUBUNRITAISISETUTOU),
        '歩車道区分':                  dict_keys(c.HOSYADOUKUBUN),
        '事故類型':                   dict_keys(c.JIKORUIKEI),
        '年齢（当事者A）':             dict_keys(c.NENREI),
        '年齢（当事者B）':             dict_keys(c.NENREI),
        '当事者種別（当事者A）':        dict_keys(c.TOUJISYASYUBETU),
        '当事者種別（当事者B）':        dict_keys(c.TOUJISYASYUBETU),
        '用途別（当事者A）':           dict_keys(c.YOUTOBETU),
        '用途別（当事者B）':           dict_keys(c.YOUTOBETU),
        '車両形状（当事者A）':          dict_keys(c.SYARYOUKEIJYOU),
        '車両形状（当事者B）':          dict_keys(c.SYARYOUKEIJYOU),
        '速度規制（指定のみ）（当事者A）': dict_keys(c.SOKUDOKISEI_SITEINOMI),
        '速度規制（指定のみ）（当事者B）': dict_keys(c.SOKUDOKISEI_SITEINOMI),
        '車両の損壊程度（当事者A）':    dict_keys(c.SYARYOUNOSONKAITEIDO),
        '車両の損壊程度（当事者B）':    dict_keys(c.SYARYOUNOSONKAITEIDO),
        'エアバッグの装備（当事者A）':  dict_keys(c.EABAGUNOSOUBI),
        'エアバッグの装備（当事者B）':  dict_keys(c.EABAGUNOSOUBI),
        'サイドエアバッグの装備（当事者A）': dict_keys(c.SAIDOEABAGUNOSOUBI),
        'サイドエアバッグの装備（当事者B）': dict_keys(c.SAIDOEABAGUNOSOUBI),
        '人身損傷程度（当事者A）':     dict_keys(c.JINSINSONSYOUTEIDO),
        '人身損傷程度（当事者B）':     dict_keys(c.JINSINSONSYOUTEIDO),
        '曜日(発生年月日)':            dict_keys(c.YOUBI),
        '祝日(発生年月日)':            dict_keys(c.SYUKUJITU),
    }

    # 2019-2021固有
    if not is_new:
        lookup['上下線'] = dict_keys(c.JYOUGESEN)
        lookup['環状交差点の直径'] = dict_keys(c.KANJYO_CHOKEI)

    return lookup


def check_year(year):
    input_path = ROOT / 'data' / str(year) / f'honhyo_{year}.csv'
    if not input_path.exists():
        print(f'  [SKIP] 入力ファイル未存在: {input_path.relative_to(ROOT)}')
        return True

    # decode後のDataFrameを使う（列名が統一されている）
    from converter.decode import decode
    print(f'  読み込み中...')
    df = decode(year, input_path)

    lookup = build_lookup(year)
    errors = []

    for col, valid_keys in lookup.items():
        if col not in df.columns:
            continue
        col_vals = df[col].dropna().astype(str).str.strip()
        col_vals = col_vals[col_vals != '']
        undefined = col_vals[~col_vals.isin(valid_keys)]
        # 既知のデータ異常を除外
        known = KNOWN_DATA_ANOMALIES.get(year, {}).get(col, set())
        unexpected = undefined[~undefined.isin(known)]
        if not known.issubset(set(undefined)):
            known = set()  # 既知コードが今年のデータに存在しなければ無視
        if not known.isdisjoint(set(undefined)):
            for code in known & set(undefined):
                print(f'  ⚠️  {col}: 既知データ異常 {code!r} ({int((undefined==code).sum())}件、変換結果は空欄)')
        if not unexpected.empty:
            counts = unexpected.value_counts().head(10)
            msg = f'  ❌ {col}: 未定義コード {len(unexpected.unique())}種'
            errors.append(msg)
            print(msg)
            for code, cnt in counts.items():
                print(f'       {code!r:>12}: {cnt}件')

    if not errors:
        print(f'  ✅ {year}: 全コード定義済み（{len(lookup)}カラム確認）')

    return len(errors) == 0


def main():
    parser = argparse.ArgumentParser(description='④チェック: 実データの未定義コード検出')
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
        print('✅ 全年次: 未定義コードなし')
    else:
        print('❌ 未定義コードが存在します。辞書の更新が必要です。')
        sys.exit(1)


if __name__ == '__main__':
    main()
