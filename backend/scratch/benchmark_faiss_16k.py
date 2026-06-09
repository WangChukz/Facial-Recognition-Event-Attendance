"""
benchmark_faiss_16k.py
======================
Benchmark FAISS Flat (IndexFlatIP) vs HNSW (IndexHNSWFlat) với
dữ liệu fake tổng hợp 16,000 sinh viên để đánh giá hiệu năng
ở quy mô lớn.

Dữ liệu đầu vào:
  enroll_embeddings.npy  — (16000, 512) float32, đã L2-normalize, không nhiễu
  real_embeddings.npy    — (80000, 512) float32, đã L2-normalize, noise σ=0.05
  metadata.json          — mapping SV_ID → enroll_embedding_idx + real_embedding_idxs

Chạy:
  python scratch/benchmark_faiss_16k.py
"""

import os
import sys
import json
import time
import random
import logging

import numpy as np
import faiss

# ─── Logging ────────────────────────────────────────────────────────────────
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("FAISS_16k_Benchmark")

# ─── Paths ──────────────────────────────────────────────────────────────────
FAKE_ROOT = r"c:\AI_event\DATA_FAKE-20260608T190448Z-3-001\DATA_FAKE\dataset_fake\dataset_fake"
ENROLL_NPY = os.path.join(FAKE_ROOT, "enroll_embeddings.npy")
REAL_NPY   = os.path.join(FAKE_ROOT, "real_embeddings.npy")
META_JSON  = os.path.join(FAKE_ROOT, "metadata.json")

# ─── Config ──────────────────────────────────────────────────────────────────
NUM_QUERY    = 500       # số real-embedding dùng để query benchmark
TOP_K_LIST   = [1, 3, 10]  # các giá trị top-K cần đánh giá
HNSW_M       = 32        # số kết nối mỗi node trong HNSW
HNSW_EF_C    = 200       # efConstruction — độ chính xác lúc xây dựng
HNSW_EF_S    = 64        # efSearch       — độ chính xác lúc tìm kiếm
DIM          = 512       # chiều vector

# ─── Helpers ─────────────────────────────────────────────────────────────────
def load_data():
    """Nạp embeddings fake và metadata."""
    logger.info(f"[1] Đang nạp enroll embeddings từ: {ENROLL_NPY}")
    enroll = np.load(ENROLL_NPY).astype(np.float32)
    logger.info(f"    ✓ enroll_embeddings: {enroll.shape}")  # (16000, 512)

    logger.info(f"[2] Đang nạp real embeddings từ: {REAL_NPY}")
    real = np.load(REAL_NPY).astype(np.float32)
    logger.info(f"    ✓ real_embeddings  : {real.shape}")    # (80000, 512)

    logger.info(f"[3] Đang nạp metadata từ: {META_JSON}")
    with open(META_JSON, encoding="utf-8") as f:
        meta = json.load(f)
    logger.info(f"    ✓ metadata         : {len(meta)} sinh viên")

    return enroll, real, meta


def build_flat_index(enroll: np.ndarray) -> faiss.IndexFlatIP:
    """Xây dựng FAISS Flat Inner-Product index."""
    index = faiss.IndexFlatIP(DIM)
    t0 = time.perf_counter()
    index.add(enroll)
    build_time = time.perf_counter() - t0
    logger.info(f"    ✓ FAISS Flat — xây dựng xong trong {build_time*1000:.1f} ms | ntotal={index.ntotal}")
    return index, build_time


def build_hnsw_index(enroll: np.ndarray) -> faiss.IndexHNSWFlat:
    """Xây dựng FAISS HNSW index (inner-product bằng cách đổi chiều)."""
    index = faiss.IndexHNSWFlat(DIM, HNSW_M)
    index.hnsw.efConstruction = HNSW_EF_C
    index.hnsw.efSearch = HNSW_EF_S
    t0 = time.perf_counter()
    index.add(enroll)
    build_time = time.perf_counter() - t0
    logger.info(f"    ✓ FAISS HNSW  — xây dựng xong trong {build_time*1000:.1f} ms | ntotal={index.ntotal}")
    return index, build_time


def build_ground_truth(meta: dict, real: np.ndarray, query_idxs: list) -> dict:
    """
    Xây dựng ground-truth: với mỗi query (real embedding),
    xác định enroll_embedding_idx đúng từ metadata.
    Trả về dict: real_emb_idx → enroll_idx đúng.
    """
    # Đảo ngược metadata: real_emb_idx → (sv_id, enroll_idx)
    real_to_enroll = {}
    for sv_id, info in meta.items():
        enroll_idx = info["enroll_embedding_idx"]
        for real_idx in info["real_embedding_idxs"]:
            real_to_enroll[real_idx] = enroll_idx
    return real_to_enroll


def run_benchmark(flat_index, hnsw_index, enroll, real, real_to_enroll, query_real_idxs):
    """Thực thi benchmark và trả về kết quả."""
    queries = real[query_real_idxs]   # (NUM_QUERY, 512)

    results = {}

    for top_k in TOP_K_LIST:
        # ── FAISS Flat ───────────────────────────────────────────
        t0 = time.perf_counter()
        sims_flat, ids_flat = flat_index.search(queries, top_k)
        flat_time = (time.perf_counter() - t0) / len(query_real_idxs) * 1000  # ms/query

        recall_flat = 0
        for qi, real_idx in enumerate(query_real_idxs):
            gt_enroll = real_to_enroll.get(real_idx, -1)
            if gt_enroll in ids_flat[qi]:
                recall_flat += 1
        recall_flat = recall_flat / len(query_real_idxs) * 100

        # ── HNSW ─────────────────────────────────────────────────
        t0 = time.perf_counter()
        sims_hnsw, ids_hnsw = hnsw_index.search(queries, top_k)
        hnsw_time = (time.perf_counter() - t0) / len(query_real_idxs) * 1000

        recall_hnsw = 0
        for qi, real_idx in enumerate(query_real_idxs):
            gt_enroll = real_to_enroll.get(real_idx, -1)
            if gt_enroll in ids_hnsw[qi]:
                recall_hnsw += 1
        recall_hnsw = recall_hnsw / len(query_real_idxs) * 100

        results[top_k] = {
            "flat_latency_ms":  flat_time,
            "hnsw_latency_ms":  hnsw_time,
            "flat_recall_pct":  recall_flat,
            "hnsw_recall_pct":  recall_hnsw,
        }

    return results


def print_results(results: dict, flat_build_ms, hnsw_build_ms):
    """In bảng kết quả so sánh."""
    print("\n" + "=" * 90)
    print("   BENCHMARK KẾT QUẢ: FAISS Flat vs HNSW — Quy mô 16,000 Sinh viên (Fake Data)")
    print("=" * 90)
    print(f"  Số sinh viên   : 16,000")
    print(f"  Số vector enroll: 16,000  |  Số vector real (query): {NUM_QUERY} / 80,000")
    print(f"  Thời gian build FAISS Flat: {flat_build_ms*1000:.1f} ms")
    print(f"  Thời gian build HNSW      : {hnsw_build_ms*1000:.1f} ms")
    print(f"  HNSW params: M={HNSW_M}, efConstruction={HNSW_EF_C}, efSearch={HNSW_EF_S}")
    print("-" * 90)
    print(f"  {'Chỉ số':<28} | {'FAISS Flat (IndexFlatIP)':<26} | {'HNSW (IndexHNSWFlat)':<26}")
    print("-" * 90)
    for top_k in TOP_K_LIST:
        r = results[top_k]
        speedup = r['flat_latency_ms'] / r['hnsw_latency_ms'] if r['hnsw_latency_ms'] > 0 else 0
        print(f"  {'Latency  @top-' + str(top_k) + ' (ms/query)':<28} | {r['flat_latency_ms']:<26.4f} | {r['hnsw_latency_ms']:<26.4f}")
        print(f"  {'Recall   @top-' + str(top_k) + ' (%)':<28} | {r['flat_recall_pct']:<26.2f} | {r['hnsw_recall_pct']:<26.2f}")
        if top_k < TOP_K_LIST[-1]:
            print(f"  {'':28} |                           |")
    print("=" * 90)

    # Nhận xét
    r1 = results[1]
    speedup_1nn = r1['flat_latency_ms'] / r1['hnsw_latency_ms'] if r1['hnsw_latency_ms'] > 0 else 0
    print("\n📌 Nhận xét:")
    print(f"  • HNSW nhanh hơn FAISS Flat ×{speedup_1nn:.1f} lần ở top-1")
    print(f"  • FAISS Flat: Recall@1 = {r1['flat_recall_pct']:.2f}% (exact search — luôn tối ưu)")
    print(f"  • HNSW:       Recall@1 = {r1['hnsw_recall_pct']:.2f}% (approximate search)")
    recall_drop = r1['flat_recall_pct'] - r1['hnsw_recall_pct']
    if recall_drop < 0.5:
        print(f"  • Độ giảm Recall chỉ {recall_drop:.2f}% — chấp nhận được cho production")
    else:
        print(f"  • Độ giảm Recall {recall_drop:.2f}% — nên tăng efSearch để cải thiện")
    print()


def main():
    logger.info("=" * 60)
    logger.info("FAISS 16k Benchmark — Khởi động")
    logger.info("=" * 60)

    # 1. Load data
    enroll, real, meta = load_data()

    # 2. Normalize (đảm bảo đã normalize, fake data đã normalize sẵn)
    faiss.normalize_L2(enroll)
    faiss.normalize_L2(real)

    # 3. Build indexes
    logger.info("[4] Đang xây dựng các chỉ mục...")
    flat_index, flat_build_s = build_flat_index(enroll)
    hnsw_index, hnsw_build_s = build_hnsw_index(enroll)

    # 4. Chuẩn bị query set — lấy 500 real embedding ngẫu nhiên
    logger.info(f"[5] Chuẩn bị {NUM_QUERY} query vectors ngẫu nhiên từ real embeddings...")
    random.seed(42)
    all_real_idxs = list(range(len(real)))
    query_real_idxs = random.sample(all_real_idxs, NUM_QUERY)

    # 5. Build ground truth
    real_to_enroll = build_ground_truth(meta, real, query_real_idxs)
    logger.info(f"    ✓ Ground truth đã xây dựng cho {len(real_to_enroll)} real embeddings")

    # 6. Run benchmark
    logger.info(f"[6] Đang thực thi benchmark với {NUM_QUERY} queries × top-K = {TOP_K_LIST}...")
    results = run_benchmark(flat_index, hnsw_index, enroll, real, real_to_enroll, query_real_idxs)

    # 7. Print results
    print_results(results, flat_build_s, hnsw_build_s)

    # 8. Save JSON
    out_path = os.path.join(os.path.dirname(__file__), "benchmark_16k_results.json")
    import json as _json
    summary = {
        "num_students": 16000,
        "num_queries": NUM_QUERY,
        "flat_build_ms": flat_build_s * 1000,
        "hnsw_build_ms": hnsw_build_s * 1000,
        "hnsw_config": {"M": HNSW_M, "efConstruction": HNSW_EF_C, "efSearch": HNSW_EF_S},
        "results_by_topk": results
    }
    with open(out_path, 'w', encoding='utf-8') as f:
        _json.dump(summary, f, ensure_ascii=False, indent=4)
    logger.info(f"✅ Kết quả đã lưu tại: {out_path}")


if __name__ == "__main__":
    main()
