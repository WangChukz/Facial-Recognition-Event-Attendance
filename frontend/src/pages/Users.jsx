import { useEffect, useState } from "react";
import { apiGet, apiPost, apiDelete } from "../api.js";
import { useToast } from "../context/ToastContext.jsx";
import { Loader2, Trash2 } from "lucide-react";

export default function Users() {
  const [users, setUsers] = useState([]);
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState("student");
  const [code, setCode] = useState("");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);
  const { addToast } = useToast();

  const load = () => apiGet("/users").then(setUsers).catch((e) => setErr(String(e.message)));

  useEffect(() => {
    load();
  }, []);

  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    setLoading(true);
    try {
      await apiPost("/users", {
        email,
        full_name: fullName,
        role,
        student_code: code || null,
      });
      setEmail("");
      setFullName("");
      setCode("");
      addToast("Tạo người dùng thành công!", "success");
      await load();
    } catch (e) {
      setErr(e.message);
      addToast("Có lỗi xảy ra khi tạo người dùng.", "error");
    } finally {
      setLoading(false);
    }
  };

  const deleteUser = async (userId, userName) => {
    if (!confirm(`Bạn có chắc muốn xóa sinh viên/nhân sự "${userName}"? Thao tác này sẽ xóa sạch ảnh thẻ, dữ liệu đặc trưng nhận diện (FAISS) và lịch sử điểm danh của họ.`)) return;
    try {
      await apiDelete(`/users/${userId}`);
      addToast("Xóa người dùng thành công!", "success");
      await load();
    } catch (e) {
      addToast("Có lỗi xảy ra khi xóa người dùng: " + e.message, "error");
    }
  };

  return (
    <div>
      <h1>Người dùng / sinh viên</h1>
      <div className="row">
        <div className="panel form-grid">
          <h2>Tạo mới</h2>
          <form onSubmit={submit}>
            <label>
              Email
              <input value={email} onChange={(e) => setEmail(e.target.value)} required type="email" />
            </label>
            <label>
              Họ tên
              <input value={fullName} onChange={(e) => setFullName(e.target.value)} required />
            </label>
            <label>
              Vai trò
              <select value={role} onChange={(e) => setRole(e.target.value)}>
                <option value="student">student</option>
                <option value="staff">staff</option>
                <option value="admin">admin</option>
              </select>
            </label>
            <label>
              Mã SV (tuỳ chọn)
              <input value={code} onChange={(e) => setCode(e.target.value)} />
            </label>
            {err && <p className="muted" style={{ color: "var(--danger)" }}>{err}</p>}
            <button type="submit" className="primary" disabled={loading} style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
              {loading && <Loader2 size={16} className="animate-spin" style={{ animation: "kiosk-spin 1s linear infinite" }} />}
              Lưu người dùng
            </button>
          </form>
        </div>
        <div className="panel" style={{ minWidth: 0 }}>
          <h2>Danh sách</h2>
          <table className="table">
            <thead>
              <tr>
                <th>Họ tên</th>
                <th>Email / MSSV</th>
                <th>ID</th>
                <th>Hành động</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td>
                    <div style={{ fontWeight: 600 }}>{u.full_name}</div>
                    <div className="muted" style={{ fontSize: "0.8rem" }}>Vai trò: {u.role}</div>
                  </td>
                  <td>
                    <div>{u.email}</div>
                    {u.student_code && <div className="muted" style={{ fontSize: "0.8rem" }}>MSSV: {u.student_code}</div>}
                  </td>
                  <td className="muted" style={{ fontSize: "0.72rem" }}>
                    {u.id}
                  </td>
                  <td>
                    <button
                      type="button"
                      onClick={() => deleteUser(u.id, u.full_name)}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 4,
                        padding: "6px 10px",
                        backgroundColor: "#fef2f2",
                        color: "#dc2626",
                        border: "none",
                        borderRadius: 4,
                        cursor: "pointer",
                        fontSize: "0.8rem"
                      }}
                    >
                      <Trash2 size={13} /> Xóa
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
