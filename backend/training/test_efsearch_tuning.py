"""Test different efSearch values for HNSW tuning"""
from pathlib import Path
import time
import numpy as np
import faiss
from sklearn.metrics import accuracy_score

ROOT = Path(__file__).resolve().parents[2]
MODELS = ROOT / "backend" / "app" / "models"
TRAINING = ROOT / "backend" / "training"
FAKE_ROOT = Path(r"C:\AI_event\DATA_FAKE-20260608T190448Z-3-001\DATA_FAKE\dataset_fake\dataset_fake")

def normalize(x):
    return x / np.linalg.norm(x, axis=1, keepdims=True)

# Test Case 2: ArcFace Pretrained
print("=" * 80)
print("CASE 2 - ArcFace Pretrained (small dataset, 39 students)")
print("=" * 80)
split_path = MODELS / "dataset_split.npz"
if split_path.exists():
    data = np.load(split_path)
    gallery = normalize(data["X_train"].astype(np.float32))
    gallery_y = data["y_train"].astype(np.int32)
    queries = normalize(data["X_test"].astype(np.float32))
    query_y = data["y_test"].astype(np.int32)

    print(f"\nGallery: {gallery.shape}, Queries: {queries.shape}")
    print("\nTesting efSearch values: 4, 8, 12, 16, 20, 32")
    print(f"{'efSearch':<12} {'Accuracy':<12} {'Latency (ms)':<15} {'Comments'}")
    print("-" * 70)

    for ef in [4, 8, 12, 16, 20, 32]:
        index = faiss.IndexHNSWFlat(gallery.shape[1], 16)
        index.hnsw.efConstruction = 100
        index.hnsw.efSearch = ef
        index.add(gallery)

        t0 = time.perf_counter()
        distances, ids = index.search(queries, 1)
        latency = (time.perf_counter() - t0) / len(queries) * 1000

        pred = gallery_y[ids.reshape(-1)]
        acc = accuracy_score(query_y, pred) * 100

        status = "✓ OK" if acc == 100 else f"⚠ Low ({acc:.1f}%)"
        print(f"{ef:<12} {acc:>6.2f}%       {latency:>6.4f}            {status}")

print("\n" + "=" * 80)
print("CASE 3 - Synthetic Scalability (N=16k)")
print("=" * 80)

enroll_path = FAKE_ROOT / "enroll_embeddings.npy"
real_path = FAKE_ROOT / "real_embeddings.npy"

if enroll_path.exists() and real_path.exists():
    enroll_all = normalize(np.load(enroll_path, mmap_mode="r")[:16000].astype(np.float32))
    real_all = normalize(np.load(real_path, mmap_mode="r").astype(np.float32))

    n = 16000
    gallery = enroll_all[:n]
    query_pool = np.arange(n * 5)
    rng = np.random.RandomState(42)
    query_ids = rng.choice(query_pool, size=min(500, len(query_pool)), replace=False)
    queries = real_all[query_ids]

    print(f"\nGallery N={n}, Queries: {len(query_ids)}")
    print("\nTesting efSearch values: 4, 8, 12, 16, 20, 32")
    print(f"{'efSearch':<12} {'Latency (ms)':<15} {'vs FAISS':<15} {'Comments'}")
    print("-" * 70)

    # Baseline: FAISS Flat
    flat = faiss.IndexFlatIP(gallery.shape[1])
    flat.add(gallery)
    t0 = time.perf_counter()
    flat.search(queries, 1)
    faiss_latency = (time.perf_counter() - t0) / len(queries) * 1000
    print(f"{'BASELINE':<12} {faiss_latency:>6.4f}            {'1.0x (Flat)':>14}")

    for ef in [4, 8, 12, 16, 20, 32]:
        index = faiss.IndexHNSWFlat(gallery.shape[1], 16)
        index.hnsw.efConstruction = 100
        index.hnsw.efSearch = ef
        index.add(gallery)

        t0 = time.perf_counter()
        index.search(queries, 1)
        latency = (time.perf_counter() - t0) / len(queries) * 1000

        speedup = faiss_latency / latency
        status = f"{speedup:.2f}x faster" if speedup > 1 else f"{1/speedup:.2f}x slower"
        print(f"{ef:<12} {latency:>6.4f}            {status:>14}")

print("\n" + "=" * 80)
print("RECOMMENDATION:")
print("=" * 80)
print("""
efSearch Trade-off Analysis:
- efSearch=4:  Fastest, risk of recall loss
- efSearch=8:  Good speed, acceptable recall
- efSearch=12: Safe middle ground
- efSearch=16: Current (1.6-1.7x speedup on 16k) - RECOMMENDED
- efSearch=20: More recall, but slower
- efSearch=32: Original slow config

Production Recommendation:
- For latency < 0.03ms @ 16k: efSearch=8
- For balanced: efSearch=12-16 (current)
- For high accuracy: Keep efSearch=16
""")
