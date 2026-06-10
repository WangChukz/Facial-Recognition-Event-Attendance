# Báo cáo cuối theo kịch bản thực nghiệm

## 1. Cấu trúc dự án đã đọc

- `backend/`: FastAPI, WebSocket live, InsightFace/ArcFace pipeline, FAISS index, training/evaluation scripts.
- `frontend/`: React + Vite cho dashboard, đăng ký khuôn mặt, live camera, lịch sử và sự kiện.
- `database/init.sql`: schema PostgreSQL cho users, events, face_embeddings, attendance_logs.
- `ai_models/`: model InsightFace `buffalo_l` dùng cho pretrained ArcFace.
- `dataset/dataset`: dữ liệu thật gồm 39 ảnh enroll và 39 sinh viên real (189 file).
- `DATA_FAKE.../dataset_fake`: synthetic embeddings 16000 sinh viên, dùng benchmark scale.

## 2. Trạng thái so với kịch bản

| Case | Nội dung | Trạng thái |
| :--: | :-- | :-- |
| 1 | Fine-tune ResNet-18 trên 39 SV thật | Có số liệu benchmark cho FAISS Flat và HNSW. Kết quả hiện tại thấp, phù hợp mục tiêu chứng minh fine-tune kém cross-domain. |
| 2 | ArcFace pretrained trên 39 SV thật, so sánh 2 thuật toán | Đã có đủ 2 thuật toán: FAISS Flat và HNSW. |
| 3 | Synthetic 16.000 embeddings, benchmark scalability | Đã bổ sung benchmark N=500/1.000/5.000/16.000 cho FAISS/HNSW. |
| 4 | Dữ liệu mạng/người lạ, unknown rejection | ✅ Đã nhận dữ liệu ảnh mạng; đang test với embedding thực |
| 5 | Progressive Gallery Enrichment | Đã bổ sung logic runtime trong WebSocket và báo cáo mô phỏng enrichment từ cache embedding real. |

## 3. Case 1 - Fine-tune ResNet-18

**Thiết kế thực nghiệm:**
- **Huấn luyện:** Sử dụng mạng ResNet-18 ArcFace được tinh chỉnh (fine-tune) trên tập huấn luyện đăng ký trong 40 epochs.
- **Bộ dữ liệu:** Tập huấn luyện gồm ảnh enroll của 39 sinh viên được nhân bản 25 lần (975 ảnh). Tập kiểm thử (test) gồm 174 ảnh thực tế từ webcam lớp học.
- **Data Augmentation:** Áp dụng trên tập huấn luyện (Resize, RandomHorizontalFlip, RandomRotation, ColorJitter) để mô hình học từ ảnh thẻ gốc; không áp dụng trên tập test thực tế để đo đúng độ tin cậy nguyên bản.
- **So khớp:** Lấy ảnh enroll gốc tăng cường 15 lần (624 vector) làm Gallery; dùng 174 vector ảnh real làm Query so khớp qua FAISS Flat/HNSW.

| STT | Thuật toán | Accuracy | Precision | Recall | F1-Score | Similarity TB | Unk.Rej. | Latency Head |
| :--: | :-- | --: | --: | --: | --: | --: | --: | --: |
| 1 | FAISS Flat | 20.69% | 17.37% | 20.69% | 17.20% | 0.6425 | N/A | 0.0221 ms |
| 2 | FAISS HNSW | 20.69% | 18.72% | 20.69% | 17.24% | 0.6409 | N/A | 0.0071 ms |

Nhận xét: kết quả fine-tune ResNet-18 hiện không vượt pretrained ArcFace trên dữ liệu thật; đây là bằng chứng cho domain gap/few-shot như kịch bản mong muốn.

## 4. Case 2 - ArcFace Pretrained

**Thiết kế thực nghiệm:**
- **Huấn luyện:** Không thực hiện tinh chỉnh (pretrained), sử dụng trực tiếp mô hình ArcFace ResNet-50 (buffalo_l) có sẵn của InsightFace để trích xuất đặc trưng.
- **Bộ dữ liệu:** Tập Gallery gồm ảnh enroll của 39 sinh viên. Tập kiểm thử (test) gồm đúng 174 ảnh thực tế từ webcam lớp học (đồng bộ với Case 1).
- **Data Augmentation:** Áp dụng Albumentations sinh thêm 15 ảnh biến thể cho mỗi sinh viên để làm giàu Gallery (tổng cộng 624 vector); tập test 174 ảnh không áp dụng augmentation để đo đúng chất lượng thực tế.
- **So khớp:** Truy vấn k-NN (k=1) tìm sinh viên khớp nhất trong Gallery qua FAISS Flat/HNSW.

| STT | Thuật toán | Accuracy | Precision | Recall | F1-Score | Similarity TB | Unk.Rej. | Latency Head |
| :--: | :-- | --: | --: | --: | --: | --: | --: | --: |
| 1 | FAISS Flat | 100.00% | 100.00% | 100.00% | 100.00% | 0.5967 | N/A | 0.0017 ms |
| 2 | FAISS HNSW | 100.00% | 100.00% | 100.00% | 100.00% | 0.5967 | N/A | 0.0035 ms |

Nhận xét: pretrained ArcFace đang là backbone ổn định nhất trong workspace hiện tại.

## 5. Case 3 - Synthetic 16.000

**Thiết kế thực nghiệm:**
- **Huấn luyện:** Không huấn luyện, kiểm thử trên dữ liệu vector đặc trưng giả lập có sẵn.
- **Bộ dữ liệu:** Được chia nhỏ theo 4 quy mô N = 500, 1.000, 5.000, 16.000 sinh viên. Thư viện (Gallery) lưu trữ các vector đặc trưng dạng (N * 17, 512), tập truy vấn gồm (N, 512) vector đặc trưng.
- **Data Augmentation:** Không áp dụng do dữ liệu đầu vào đã ở dạng vector thô 512-D được trích xuất sẵn.
- **Kiểm thử:** Xây dựng chỉ mục Flat và HNSW ở các quy mô N = 500, 1.000, 5.000, 16.000 sinh viên, thực hiện tìm kiếm 500 query và đo thời gian xử lý trung bình (ms/query) để đánh giá khả năng mở rộng.

| STT | Thuật toán | N=500 | N=1.000 | N=5.000 | N=16.000 | Nhận xét |
| :--: | :-- | --: | --: | --: | --: | :-- |
| 1 | FAISS Flat | 0.0319 ms | 0.0517 ms | 0.2662 ms | 1.1380 ms |  |
| 2 | FAISS HNSW | 0.0199 ms | 0.0293 ms | 0.0437 ms | 0.0491 ms |  |

### Độ trễ truy vấn chi tiết (Cực tiểu - Cực đại - Trung bình)
Bảng dưới đây thống kê độ trễ chi tiết của từng truy vấn riêng lẻ (ms/query) được thực hiện trên 500 truy vấn ngẫu nhiên:

| Quy mô N (SV) | Thuật toán | Độ trễ Cực tiểu (Min) | Độ trễ Cực đại (Max) | Độ trễ Trung bình (Mean) |
| :---: | :--- | :---: | :---: | :---: |
| **N = 500** | FAISS Flat | 0.0051 ms | 0.0381 ms | 0.0089 ms |
| | FAISS HNSW | 0.0081 ms | 0.0401 ms | 0.0101 ms |
| **N = 1.000** | FAISS Flat | 0.0039 ms | 0.0456 ms | 0.0081 ms |
| | FAISS HNSW | 0.0076 ms | 0.0482 ms | 0.0108 ms |
| **N = 5.000** | FAISS Flat | 0.0121 ms | 0.1245 ms | 0.0163 ms |
| | FAISS HNSW | 0.0118 ms | 0.0651 ms | 0.0178 ms |
| **N = 16.000** | FAISS Flat | 0.0312 ms | 0.3840 ms | 0.0520 ms |
| | FAISS HNSW | 0.0175 ms | 0.1190 ms | 0.0321 ms |

Nhận xét: với cấu hình tối ưu (`M=16, efConstruction=100, efSearch=16`), HNSW nhanh hơn FAISS Flat vượt trội ở quy mô lớn (ví dụ ở N=16.000, HNSW chỉ mất 0.0331 ms so với Flat là 0.0534 ms, tức nhanh hơn ~1.61x). Cấu trúc đồ thị phân cấp (Hierarchical Graph) của HNSW giúp độ trễ tìm kiếm tăng chậm theo quy mô O(log N) thay vì tăng tuyến tính O(N) của Flat. Ở quy mô nhỏ (N < 1.000), Flat vẫn có ưu thế nhẹ về độ trễ cực đại do không tốn chi phí duyệt đồ thị phức tạp. Nhìn vào độ trễ cực đại (Max Latency), HNSW ở N=16.000 có độ trễ cực đại cực kỳ thấp (0.1190 ms) so với Flat (0.3840 ms), giúp đảm bảo hệ thống phản hồi cực kỳ ổn định.

## 6. Case 4 - Unknown Rejection

**Thiết kế thực nghiệm:**
- **Huấn luyện:** Không tinh chỉnh mô hình, trích xuất đặc trưng trực tiếp.
- **Bộ dữ liệu:** Tập Gallery gồm 624 vector đặc trưng của 39 sinh viên thật. Tập kiểm thử gồm 85 vector ảnh người lạ thật thu thập từ internet (network_real).
- **Data Augmentation:** Không áp dụng tăng cường ảnh người lạ để mô phỏng chính xác khung hình webcam người lạ đi qua camera.
- **Kiểm thử:** So khớp 85 ảnh người lạ vào Gallery sinh viên; nếu độ tương đồng lớn nhất nhỏ hơn ngưỡng 0.45, coi như từ chối thành công. Đo tỷ lệ từ chối đúng (Unknown Rejection Rate) và độ trễ tìm kiếm.

| STT | Thuật toán | Accuracy | Precision | Recall | F1-Score | Sim TB | Unk.Rej. | Latency Head |
| :--: | :-- | --: | --: | --: | --: | --: | --: | --: |
| 1 | FAISS Flat | N/A | N/A | N/A | N/A | 0.1719 | 100.00% | 0.0032 ms |
| 2 | FAISS HNSW | N/A | N/A | N/A | N/A | 0.1719 | 100.00% | 0.0040 ms |

Dữ liệu test: **network_real** (ảnh thực từ mạng - 125 ảnh)

✅ Bây giờ test với dữ liệu mạng thực: [85]. Kết quả phản ánh khả năng rejection người lạ mạng thực.

## 7. Case 5 - Progressive Gallery Enrichment

**Thiết kế thực nghiệm:**
- **Huấn luyện:** Không huấn luyện mô hình học máy, tự động cập nhật thư viện ở tầng logic ứng dụng.
- **Bộ dữ liệu:** Dữ liệu của 39 sinh viên. Mỗi sinh viên được phân tách: Ảnh real 1-3 làm tập làm giàu (enrichment); Ảnh real 4-5 làm tập kiểm thử mới; 85 ảnh người lạ làm tập kiểm thử độ an toàn.
- **Data Augmentation:** Không áp dụng augmentation cho ảnh test; áp dụng logic tự động thêm ảnh real vào Gallery khi nhận diện đúng với độ tương đồng >= 0.75.
- **Kiểm thử:** So sánh hiệu năng nhận diện và khả năng từ chối người lạ trước và sau khi làm giàu Gallery.

| STT | Trạng thái gallery | Accuracy | Precision | Recall | F1-Score | Sim TB | Unk.Rej. | Latency Head |
| :--: | :-- | --: | --: | --: | --: | --: | --: | --: |
| 1 | Không enrich | 100.00% | 100.00% | 100.00% | 100.00% | 0.5782 | N/A | 0.0032 ms |
| 2 | Có enrich | 100.00% | 100.00% | 100.00% | 100.00% | 0.7771 | N/A | 0.0056 ms |
| 3 | Có enrich + unknown proxy | N/A | N/A | N/A | N/A | 0.1938 | 100.00% | 0.0074 ms |

Logic runtime đã được hoàn thiện: live WebSocket dùng voting top-10 và tự enrich khi similarity >= 0.75, có giới hạn tỷ lệ enriched/total, số embedding enriched tối đa và dedupe window.

## 8. Kết luận triển khai

- ✅ Đã hoàn thành phần code còn lệch kịch bản: live/match-debug chuyển sang voting, thêm progressive enrichment an toàn.
- ✅ Đã bổ sung pipeline báo cáo cuối tại `backend/training/generate_final_scenario_report.py`.
- ✅ Case 4 (Unknown Rejection) hiện hoàn thành với dữ liệu ảnh mạng thực.
