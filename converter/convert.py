"""Step2: コード値→人間可読ラベルに変換"""
import csv
from pathlib import Path

import pandas as pd

from converter.codes import get_codes


ROOT = Path(__file__).parent.parent

# 全年度共通の統一出力スキーマ（72列）
OUTPUT_FIELDNAMES = [
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


def _load_csv_dict(filepath, key_cols, value_col, skip_rows=5):
    with open(filepath, mode='r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for _ in range(skip_rows):
            next(reader)
        return {''.join(str(row[c]) for c in key_cols): row[value_col] for row in reader}


def _rosenkoudo(code):
    if 1 <= code <= 999:
        return '一般国道' + str(code) + '号'
    elif 1000 <= code <= 1499:
        return '主要地方道－都道府県道'
    elif 1500 <= code <= 1999:
        return '主要地方道－市道'
    elif 2000 <= code <= 2999:
        return '一般都道府県道'
    elif 3000 <= code <= 3999:
        return '一般市町村道'
    elif 4000 <= code <= 4999:
        return None  # 高速自動車国道: 路線名CSV引き
    elif 5000 <= code <= 5499:
        return None  # 自動車専用道－指定: 路線名CSV引き
    elif 5500 <= code <= 5999:
        return '自動車専用道－その他'
    elif 6000 <= code <= 6999:
        return '道路運送法上の道路'
    elif 7000 <= code <= 7999:
        return '農（免）道'
    elif 8000 <= code <= 8499:
        return '林道'
    elif 8500 <= code <= 8999:
        return '港湾道'
    elif 9000 <= code <= 9499:
        return '私道'
    elif code == 9500:
        return 'その他'
    elif code == 9900:
        return '一般の交通の用に供するその他の道路'
    return None


def _resolve_rosen(rosen_str, pref_code, dict_rosenkousoku):
    try:
        top4 = int(str(rosen_str)[:4])
    except (ValueError, IndexError):
        return None
    label = _rosenkoudo(top4)
    if label is None:
        # 高速・専用道: CSVから路線名を引く
        label = dict_rosenkousoku.get(str(pref_code) + str(rosen_str)[:4])
    return label


def _year_dir(year):
    if year <= 2021:
        return ROOT / 'code_tables' / '2019-2021'
    d = ROOT / 'code_tables' / str(year)
    if d.exists():
        return d
    # 新年次のcode_tablesが未整備の場合は最新既知年にフォールバック
    latest = sorted(
        p for p in (ROOT / 'code_tables').iterdir()
        if p.is_dir() and p.name.isdigit()
    )[-1]
    return latest


def convert(year, df):
    """decodeで得たDataFrameにコード変換を適用し、変換済みDataFrameを返す。"""
    c = get_codes(year)
    common_dir = ROOT / 'code_tables' / 'common'
    year_dir = _year_dir(year)
    is_new = year >= 2022

    dict_todouhuken = _load_csv_dict(common_dir / '2_koudohyou_todouhukenkoudo.csv', [0], 1)
    dict_keisatusyo = _load_csv_dict(year_dir / '3_koudohyou_keisatusyotoukoudo.csv', [0, 1], 3)
    dict_syaryounosyoutotubui = _load_csv_dict(common_dir / 'hit.csv', [0], 1, skip_rows=1)
    dict_rosenkousoku = _load_csv_dict(
        year_dir / '9_koudohyou_rosen_kousokujidousyasenyou.csv', [0, 1], 3)

    rows = []
    for _, row in df.iterrows():
        rosen_label = _resolve_rosen(row['路線コード'], row['都道府県コード'], dict_rosenkousoku)

        def si(col, d):
            """int型キーの辞書をルックアップ"""
            try:
                return d.get(int(row[col]))
            except (ValueError, TypeError):
                return None

        def ss(col, d):
            """str型キーの辞書をルックアップ"""
            return d.get(str(row[col]))

        # 2019-2021はITIJITEISIKISEI_HYOUJIのキーがint
        if is_new:
            hyouji_a = ss('一時停止規制_表示（当事者A）', c.ITIJITEISIKISEI_HYOUJI)
            hyouji_b = ss('一時停止規制_表示（当事者B）', c.ITIJITEISIKISEI_HYOUJI)
            jougesen = ''
            kannjo_chokei = ''
        else:
            hyouji_a = si('一時停止規制_表示（当事者A）', c.ITIJITEISIKISEI_HYOUJI)
            hyouji_b = si('一時停止規制_表示（当事者B）', c.ITIJITEISIKISEI_HYOUJI)
            try:
                jougesen = c.JYOUGESEN.get(int(row['上下線']))
            except (ValueError, TypeError):
                jougesen = None
            kannjo_chokei = ss('環状交差点の直径', c.KANJYO_CHOKEI)

        entry = {
            '資料区分': si('資料区分', c.SIRYOUKUBUN),
            '都道府県名': dict_todouhuken.get(str(row['都道府県コード'])),
            '警察署等名': dict_keisatusyo.get(str(row['都道府県コード']) + str(row['警察署等コード'])),
            '本票番号': row['本票番号'],
            '事故内容': si('事故内容', c.JIKONAIYOU),
            '死者数': row['死者数'], '負傷者数': row['負傷者数'],
            '路線名': rosen_label,
            '上下線': jougesen,
            '地点コード': row['地点コード'], '市区町村コード': row['市区町村コード'],
            '発生日時_年': row['発生日時_年'], '発生日時_月': row['発生日時_月'],
            '発生日時_日': row['発生日時_日'], '発生日時_時': row['発生日時_時'],
            '発生日時_分': row['発生日時_分'],
            '昼夜': si('昼夜', c.TYUUYA),
            '天候': si('天候', c.TENKOU),
            '地形': si('地形', c.TIKEI),
            '路面状態': si('路面状態', c.ROMENJYOUTAI),
            '道路形状': ss('道路形状', c.DOUROKEIJYOU),
            '環状交差点の直径': kannjo_chokei,
            '信号機': si('信号機', c.SINGOUKI),
            '一時停止規制_標識（当事者A）': ss('一時停止規制_標識（当事者A）', c.ITIJITEISIKISEI_HYOUSIKI),
            '一時停止規制_表示（当事者A）': hyouji_a,
            '一時停止規制_標識（当事者B）': ss('一時停止規制_標識（当事者B）', c.ITIJITEISIKISEI_HYOUSIKI),
            '一時停止規制_表示（当事者B）': hyouji_b,
            '車道幅員': ss('車道幅員', c.SYADOUHUKUIN),
            '道路線形': si('道路線形', c.DOUROSENKEI),
            '衝突地点': ss('衝突地点', c.SYOUTOTUTITEN),
            'ゾーン規制': ss('ゾーン規制', c.ZOONKISEI),
            '中央分離帯施設等': si('中央分離帯施設等', c.TYUUOUBUNRITAISISETUTOU),
            '歩車道区分': si('歩車道区分', c.HOSYADOUKUBUN),
            '事故類型': ss('事故類型', c.JIKORUIKEI),
            '年齢（当事者A）': ss('年齢（当事者A）', c.NENREI),
            '年齢（当事者B）': ss('年齢（当事者B）', c.NENREI),
            '当事者種別（当事者A）': ss('当事者種別（当事者A）', c.TOUJISYASYUBETU),
            '当事者種別（当事者B）': ss('当事者種別（当事者B）', c.TOUJISYASYUBETU),
            '用途別（当事者A）': ss('用途別（当事者A）', c.YOUTOBETU),
            '用途別（当事者B）': ss('用途別（当事者B）', c.YOUTOBETU),
            '車両形状（当事者A）': ss('車両形状（当事者A）', c.SYARYOUKEIJYOU),
            '車両形状（当事者B）': ss('車両形状（当事者B）', c.SYARYOUKEIJYOU),
            '速度規制（指定のみ）（当事者A）': ss('速度規制（指定のみ）（当事者A）', c.SOKUDOKISEI_SITEINOMI),
            '速度規制（指定のみ）（当事者B）': ss('速度規制（指定のみ）（当事者B）', c.SOKUDOKISEI_SITEINOMI),
            '車両の衝突部位（当事者A）': dict_syaryounosyoutotubui.get(str(row['車両の衝突部位（当事者A）'])),
            '車両の衝突部位（当事者B）': dict_syaryounosyoutotubui.get(str(row['車両の衝突部位（当事者B）'])),
            '車両の損壊程度（当事者A）': ss('車両の損壊程度（当事者A）', c.SYARYOUNOSONKAITEIDO),
            '車両の損壊程度（当事者B）': ss('車両の損壊程度（当事者B）', c.SYARYOUNOSONKAITEIDO),
            'エアバッグの装備（当事者A）': si('エアバッグの装備（当事者A）', c.EABAGUNOSOUBI),
            'エアバッグの装備（当事者B）': si('エアバッグの装備（当事者B）', c.EABAGUNOSOUBI),
            'サイドエアバッグの装備（当事者A）': si('サイドエアバッグの装備（当事者A）', c.SAIDOEABAGUNOSOUBI),
            'サイドエアバッグの装備（当事者B）': si('サイドエアバッグの装備（当事者B）', c.SAIDOEABAGUNOSOUBI),
            '人身損傷程度（当事者A）': si('人身損傷程度（当事者A）', c.JINSINSONSYOUTEIDO),
            '人身損傷程度（当事者B）': si('人身損傷程度（当事者B）', c.JINSINSONSYOUTEIDO),
            '地点_緯度（北緯）': row['地点_緯度（北緯）'],
            '地点_経度（東経）': row['地点_経度（東経）'],
            '曜日(発生年月日)': si('曜日(発生年月日)', c.YOUBI),
            '祝日(発生年月日)': si('祝日(発生年月日)', c.SYUKUJITU),
            '地点_緯度（北緯）_10進数': row['地点_緯度（北緯）_10進数'],
            '地点_経度（東経）_10進数': row['地点_経度（東経）_10進数'],
            # 2019-2021は decode 段階で '' にセット済み（pass-through）
            '日の出時刻　　時': row['日の出時刻　　時'],
            '日の出時刻　　分': row['日の出時刻　　分'],
            '日の入り時刻　　時': row['日の入り時刻　　時'],
            '日の入り時刻　　分': row['日の入り時刻　　分'],
            'オートマチック車（当事者A）': row['オートマチック車（当事者A）'],
            'オートマチック車（当事者B）': row['オートマチック車（当事者B）'],
            'サポカー（当事者A）': row['サポカー（当事者A）'],
            'サポカー（当事者B）': row['サポカー（当事者B）'],
            '認知機能検査経過日数（当事者A）': row['認知機能検査経過日数（当事者A）'],
            '認知機能検査経過日数（当事者B）': row['認知機能検査経過日数（当事者B）'],
            '運転練習の方法（当事者A）': row['運転練習の方法（当事者A）'],
            '運転練習の方法（当事者B）': row['運転練習の方法（当事者B）'],
        }
        rows.append(entry)

    return pd.DataFrame(rows, columns=OUTPUT_FIELDNAMES)
