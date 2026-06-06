import pandas as pd
import sys
import json

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

meta_path = "c:/AI_event/dataset/dataset/metadata.xlsx"
df = pd.read_excel(meta_path)
for idx, row in df.iterrows():
    name = row['Họ và tên']
    if "kiên" in name.lower() or "trung" in name.lower():
        d = row.to_dict()
        d['Ngày sinh'] = str(d['Ngày sinh'])
        print(json.dumps(d, ensure_ascii=False))
