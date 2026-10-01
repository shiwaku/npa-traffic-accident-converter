"""チェックスクリプト共通の初期化（各スクリプトの先頭で import する）

- リポジトリルートを sys.path に追加し、未インストールでも converter を import 可能にする
- 標準出力を UTF-8 にする（Windows のパイプ出力は cp932 になり絵文字で落ちるため）
"""
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, 'reconfigure'):
        _stream.reconfigure(encoding='utf-8')

from converter import KNOWN_YEARS  # noqa: E402

# コード表xlsx・ファイル定義書xlsxが公開されている年次（2022年以降）
KNOWN_YEARS_WITH_XLSX = [y for y in KNOWN_YEARS if y >= 2022]
