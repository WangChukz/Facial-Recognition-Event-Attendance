import { useEffect, useState } from "react";
import { apiGet, apiPostForm } from "../api.js";
import { useToast } from "../context/ToastContext.jsx";
import { Loader2 } from "lucide-react";

export default function RegisterFace() {
  const [users, setUsers] = useState([]);
  const [userId, setUserId] = useState("");
  const [file, setFile] = useState(null);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);
  const { addToast } = useToast();

  useEffect(() => {
    apiGet("/users")
      .then((u) => {
        setUsers(u);
        if (u[0]) setUserId(u[0].id);
      })
      .catch((e) => setErr(String(e.message)));
  }, []);

  const submit = async (e) => {
    e.preventDefault();
    if (!file || !userId) return;
    setErr("");
    setLoading(true);
    const fd = new FormData();
    fd.append("user_id", userId);
    fd.append("file", file);
    try {
      const res = await apiPostForm("/faces/register", fd);
      addToast(`Đã đăng ký khuôn mặt thành công: det_score=${res.det_score.toFixed(3)}`, "success");
      setFile(null);
    } catch (e) {
      setErr(e.message);
      addToast("Có lỗi xảy ra khi tạo embedding.", "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h1>Đăng ký khuôn mặt</h1>
      <div className="panel form-grid">
        <p className="muted">Ảnh một người, mặt rõ, ánh sáng đủ.</p>
        <form onSubmit={submit}>
          <label>
            Người dùng
            <select value={userId} onChange={(e) => setUserId(e.target.value)}>
              {users.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.full_name} ({u.email})
                </option>
              ))}
            </select>
          </label>
          <label>
            Ảnh
            <input type="file" accept="image/*" onChange={(e) => setFile(e.target.files?.[0] || null)} />
          </label>
          {err && <p style={{ color: "var(--danger)" }}>{err}</p>}
          <button type="submit" className="primary" disabled={!file || loading} style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
            {loading && <Loader2 size={16} className="animate-spin" style={{ animation: "kiosk-spin 1s linear infinite" }} />}
            Tạo embedding + FAISS
          </button>
        </form>
      </div>
    </div>
  );
}
