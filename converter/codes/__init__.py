def get_codes(year: int):
    if year in (2019, 2020, 2021):
        from converter.codes import y2019_2021 as c
    elif year == 2022:
        from converter.codes import y2022 as c
    elif year == 2023:
        from converter.codes import y2023 as c
    else:
        # 2024以降は y2024 を使用（新年次追加まで最新年をフォールバック）
        from converter.codes import y2024 as c
    return c
