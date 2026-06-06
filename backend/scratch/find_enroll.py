import os
enroll_dir = "c:/AI_event/dataset/dataset/enroll"
files = sorted([f for f in os.listdir(enroll_dir) if os.path.isfile(os.path.join(enroll_dir, f))])
for f in files:
    if "kien" in f.lower() or "trung" in f.lower():
        print(f)
