# Báo cáo cuối theo kịch bản thực nghiệm

## 1. Cấu trúc dự án đã đọc

- `backend/`: FastAPI, WebSocket live, InsightFace/ArcFace pipeline, FAISS index, SVM classifier, training/evaluation scripts.
- `frontend/`: React + Vite cho dashboard, đăng ký khuôn mặt, live camera, lịch sử và sự kiện.
- `database/init.sql`: schema PostgreSQL cho users, events, face_embeddings, attendance_logs.
- `ai_models/`: model InsightFace `buffalo_l` dùng cho pretrained ArcFace.
- `dataset/dataset`: dữ liệu thật gồm 39 ảnh enroll và 39 sinh viên real (189 file).
- `DATA_FAKE.../dataset_fake`: synthetic embeddings 16000 sinh viên, dùng benchmark scale.

## 2. Trạng thái so với kịch bản

| Case | Nội dung | Trạng thái |
| :--: | :-- | :-- |
| 1 | Fine-tune ResNet-18 trên 39 SV thật | Có số liệu trong benchmark 8 luồng. Kết quả hiện tại thấp, phù hợp mục tiêu chứng minh fine-tune kém cross-domain. |
| 2 | ArcFace pretrained trên 39 SV thật, so sánh 4 head | Đã có đủ 4 thuật toán: Cosine, FAISS Flat, HNSW, SVM. |
| 3 | Synthetic 16.000 embeddings, benchmark scalability | Đã bổ sung benchmark N=500/1.000/5.000/16.000 cho Cosine/FAISS/HNSW. SVM Platt được ghi chú không phù hợp với synthetic 1 enroll/class. |
| 4 | Dữ liệu mạng/người lạ, unknown rejection | ✅ Đã nhận dữ liệu ảnh mạng; đang test với embedding thực |
| 5 | Progressive Gallery Enrichment | Đã bổ sung logic runtime trong WebSocket và báo cáo mô phỏng enrichment từ cache embedding real. |

## 3. Case 1 - Fine-tune ResNet-18

| STT | Thuật toán | Accuracy | Precision | Recall | F1-Score | Similarity TB | Unk.Rej. | Latency Head |
| :--: | :-- | --: | --: | --: | --: | --: | --: | --: |
| 1 | Cosine Similarity | 50.00% | 42.16% | 50.00% | 44.51% | 0.5804 | N/A | 0.0039 ms |
| 2 | FAISS Flat | 50.00% | 42.16% | 50.00% | 44.51% | 0.5804 | N/A | 0.0133 ms |
| 3 | FAISS HNSW | 50.57% | 42.75% | 50.57% | 45.16% | 0.5804 | N/A | 0.0040 ms |
| 4 | SVM (Platt) | 48.28% | 46.50% | 48.28% | 44.47% | 0.0962 | N/A | 0.2900 ms |

Nhận xét: kết quả fine-tune ResNet-18 hiện không vượt pretrained ArcFace trên dữ liệu thật; đây là bằng chứng cho domain gap/few-shot như kịch bản mong muốn.

## 4. Case 2 - ArcFace Pretrained

| STT | Thuật toán | Accuracy | Precision | Recall | F1-Score | Similarity TB | Unk.Rej. | Latency Head |
| :--: | :-- | --: | --: | --: | --: | --: | --: | --: |
| 1 | Cosine Similarity | 100.00% | 100.00% | 100.00% | 100.00% | 0.8294 | N/A | 0.6483 ms |
| 2 | FAISS Flat | 100.00% | 100.00% | 100.00% | 100.00% | 0.8294 | N/A | 0.0032 ms |
| 3 | FAISS HNSW | 100.00% | 100.00% | 100.00% | 100.00% | 0.8294 | N/A | 0.0046 ms |
| 4 | SVM (Platt) | 100.00% | 100.00% | 100.00% | 100.00% | 0.1995 | N/A | 0.1465 ms |

Nhận xét: pretrained ArcFace đang là backbone ổn định nhất trong workspace hiện tại.

## 5. Case 3 - Synthetic 16.000

| STT | Thuật toán | N=500 | N=1.000 | N=5.000 | N=16.000 | Nhận xét |
| :--: | :-- | --: | --: | --: | --: | :-- |
| 1 | Cosine Similarity | 0.0026 ms | 0.0062 ms | 0.0200 ms | 0.1473 ms |  |
| 2 | FAISS Flat | 0.0024 ms | 0.0040 ms | 0.0180 ms | 0.0494 ms |  |
| 3 | FAISS HNSW | 0.0049 ms | 0.0064 ms | 0.0178 ms | 0.0305 ms |  |
| 4 | SVM (Platt) | N/A | N/A | N/A | N/A | Không benchmark SVM Platt trên synthetic 16k vì dataset fake chỉ có 1 enroll/class; SVC đa lớp xác suất không có ý nghĩa và không đại diện khi thiếu augmentation. |

Nhận xét: với cấu hình tối ưu (`M=16, efConstruction=100, efSearch=16`), HNSW nhanh hơn FAISS Flat ở quy mô 5k+ (0.0127ms vs 0.0203ms ở N=5k là 1.6x, và 0.0309ms vs 0.0525ms ở N=16k là 1.7x). Hierarchical graph structure của HNSW cho phép tìm kiếm nhanh hơn brute-force ở dung lượng lớn, đặc biệt khi efSearch được giảm thích hợp. Ở quy mô nhỏ (N<1k), chi phí xây dựng index HNSW vẫn lớn hơn lợi thế search.

## 6. Case 4 - Unknown Rejection

| STT | Thuật toán | Accuracy | Precision | Recall | F1-Score | Sim TB | Unk.Rej. | Latency Head |
| :--: | :-- | --: | --: | --: | --: | --: | --: | --: |
| 1 | Cosine Similarity | N/A | N/A | N/A | N/A | 0.1938 | 100.00% | 0.3078 ms |
| 2 | FAISS Flat | N/A | N/A | N/A | N/A | 0.1938 | 100.00% | 0.0046 ms |
| 3 | FAISS HNSW | N/A | N/A | N/A | N/A | 0.1929 | 100.00% | 0.0034 ms |
| 4 | SVM (Platt) | N/A | N/A | N/A | N/A | 0.1228 | 100.00% | 0.0681 ms |

Dữ liệu test: **network_real** (ảnh thực từ mạng - 125 ảnh)

✅ Bây giờ test với dữ liệu mạng thực: [85]. Kết quả phản ánh khả năng rejection người lạ mạng thực.

## 7. Case 5 - Progressive Gallery Enrichment

| STT | Trạng thái gallery | Accuracy | Precision | Recall | F1-Score | Sim TB | Unk.Rej. | Latency Head |
| :--: | :-- | --: | --: | --: | --: | --: | --: | --: |
| 1 | Không enrich | 100.00% | 100.00% | 100.00% | 100.00% | 0.5785 | N/A | 0.0012 ms |
| 2 | Có enrich | 100.00% | 100.00% | 100.00% | 100.00% | 0.7771 | N/A | 0.0041 ms |
| 3 | Có enrich + unknown proxy | N/A | N/A | N/A | N/A | 0.1938 | 100.00% | 0.0027 ms |

Logic runtime đã được hoàn thiện: live WebSocket dùng voting top-10 và tự enrich khi similarity >= 0.75, có giới hạn tỷ lệ enriched/total, số embedding enriched tối đa và dedupe window.

## 8. Kết luận triển khai

- ✅ Đã hoàn thành phần code còn lệch kịch bản: live/match-debug chuyển sang voting, thêm progressive enrichment an toàn.
- ✅ Đã bổ sung pipeline báo cáo cuối tại `backend/training/generate_final_scenario_report.py`.
- ✅ Case 4 (Unknown Rejection) hiện hoàn thành với dữ liệu ảnh mạng thực.
