import { useEffect, useState } from "react";
import { apiGet, apiPostForm } from "../api.js";

export default function RegisterFace() {
  const [users, setUsers] = useState([]);
  const [userId, setUserId] = useState("");
  const [file, setFile] = useState(null);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");

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
    setMsg("");
    const fd = new FormData();
    fd.append("user_id", userId);
    fd.append("file", file);
    try {
      const res = await apiPostForm("/faces/register", fd);
      setMsg(`Đã đăng ký: faiss_id=${res.faiss_id}, det_score=${res.det_score.toFixed(3)}`);
      setFile(null);
    } catch (e) {
      setErr(e.message);
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
          {msg && <p style={{ color: "var(--ok)" }}>{msg}</p>}
          <button type="submit" className="primary" disabled={!file}>
            Tạo embedding + FAISS
          </button>
        </form>
      </div>
    </div>
  );
}
