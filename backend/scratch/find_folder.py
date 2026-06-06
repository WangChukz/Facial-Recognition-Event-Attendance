import os
real_dir = "c:/AI_event/dataset/dataset/real"
folders = sorted([d for d in os.listdir(real_dir) if os.path.isdir(os.path.join(real_dir, d))])
for f in folders:
    if "kien" in f.lower() or "trung" in f.lower():
        print(f)
