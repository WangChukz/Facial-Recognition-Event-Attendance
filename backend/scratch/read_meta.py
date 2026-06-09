import os
import sys

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

real_dir = "c:/AI_event/dataset/dataset/real"
enroll_dir = "c:/AI_event/dataset/dataset/enroll"

print("Real subdirs (first 15):")
if os.path.exists(real_dir):
    subdirs = sorted([d for d in os.listdir(real_dir) if os.path.isdir(os.path.join(real_dir, d))])
    print(len(subdirs), "folders found.")
    print(subdirs[:15])
else:
    print("Real dir not found")

print("\nEnroll files (first 15):")
if os.path.exists(enroll_dir):
    files = sorted([f for f in os.listdir(enroll_dir) if os.path.isfile(os.path.join(enroll_dir, f))])
    print(len(files), "files found.")
    print(files[:15])
else:
    print("Enroll dir not found")
