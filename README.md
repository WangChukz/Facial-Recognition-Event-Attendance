# Hệ thống điểm danh sự kiện — nhận diện khuôn mặt (AI)

## Chạy nhanh (dev)

1. **PostgreSQL** (port 5432), tạo DB `attendance` hoặc dùng Docker Compose.
2. **Backend** (Python 3.11+):

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
set DATABASE_URL=postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/attendance
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Lần đầu **InsightFace** sẽ tải model `buffalo_l` (~ vài trăm MB).

3. **Frontend**:

```bash
cd frontend
npm install
npm run dev
```

Mở `http://127.0.0.1:5173` — API được proxy tới `http://127.0.0.1:8000`.

## Docker (tất cả trong một)

Từ thư mục `docker`:

```bash
docker compose up --build
```

### Windows: lỗi `dockerDesktopLinuxEngine` / `The system cannot find the file specified`

Docker CLI đang cố nối tới **Docker Desktop** qua pipe `//./pipe/dockerDesktopLinuxEngine`, nhưng **daemon không chạy** (hoặc chưa cài Docker Desktop).

1. Cài [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/) (bật WSL2 nếu trình cài yêu cầu).
2. Mở **Docker Desktop** và đợi tới khi trạng thái là **Running** (không còn “Starting…”).
3. Trong PowerShell chạy: `docker version` — phải thấy cả **Client** và **Server**; nếu chỉ có Client thì engine vẫn chưa lên.
4. Chạy lại: `cd docker` rồi `docker compose up --build`.

Nếu bạn dùng Docker qua WSL, hãy chạy `docker compose` **bên trong WSL** sau khi Docker Desktop tích hợp WSL đã bật.

- UI: `http://localhost:8080`
- API qua Nginx: `http://localhost:8080/api/...`
- WebSocket: `ws://localhost:8080/api/ws/live?...`

## Cấu trúc thư mục

- `backend/` — FastAPI, WebSocket, FAISS, InsightFace pipeline
- `frontend/` — React + Vite, webcam + dashboard
- `database/init.sql` — schema tham chiếu (ERD trong comment)
- `faiss_indexes/` — file index FAISS + metadata JSON (volume khi chạy Docker)
- `docker/` — Dockerfile + compose + nginx

Chi tiết kiến trúc AI, FAISS, API, bảo mật và mở rộng: xem phản hồi chi tiết trong chat (bài làm mô tả đầy đủ các mục 1–20).

## 🚀 Tính năng nổi bật mới (Nhánh Hieu)

Nhánh `Hieu` đã gộp (merge) và bổ sung các tính năng nâng cao sau:
1. **Thuật toán bỏ phiếu AI (Voting Logic):** Sử dụng Top-10 kết quả lân cận gần nhất trong FAISS và cơ chế biểu quyết để nhận diện chính xác, giảm thiểu tối đa sai số.
2. **Tự động làm phong phú thư viện ảnh (Gallery Enrichment):** Tự động học và lưu thêm các vector đặc trưng khuôn mặt của sinh viên trong quá trình điểm danh thực tế (khi độ tin cậy đạt mức $\ge 0.75$).
3. **Kiểm soát điểm danh chặt chẽ:** Chỉ cho phép điểm danh đối với những sinh viên đã được gán (assign) vào sự kiện đó trong phần quản trị Admin (chống điểm danh tự do / người ngoài).
4. **Tối ưu hóa Docker trên Windows:** Loại bỏ cơ chế auto-reload của uvicorn trong file compose để tránh lỗi crash I/O watchfiles trên hệ điều hành Windows.
