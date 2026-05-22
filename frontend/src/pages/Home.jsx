export default function Home() {
  return (
    <div>
      <h1>Điểm danh sự kiện — nhận diện khuôn mặt (AI)</h1>
      <p className="muted">
        Pipeline: Camera → Detection (SCRFD) → Alignment → Embedding (ArcFace) → FAISS ANN → Ngưỡng → Ghi log →
        Dashboard.
      </p>
      <div className="panel">
        <h2>Luồng demo nhanh</h2>
        <ol className="muted">
          <li>Tạo người dùng (tab Người dùng).</li>
          <li>Tạo sự kiện (tab Sự kiện) và mở phiên (session).</li>
          <li>Đăng ký khuôn mặt với ảnh rõ nét một người.</li>
          <li>Mở Webcam realtime, chọn sự kiện, bật gửi khung hình qua WebSocket.</li>
          <li>Xem lịch sử điểm danh.</li>
        </ol>
      </div>
    </div>
  );
}
