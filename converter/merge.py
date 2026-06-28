"""Step3: 複数年のDataFrameをマージ"""
import pandas as pd


def merge(dfs):
    """複数DataFrameをconcat。列が違っても欠損をNaNで埋める。"""
    if not dfs:
        raise ValueError("No DataFrames to merge")
    return pd.concat(dfs, ignore_index=True)
