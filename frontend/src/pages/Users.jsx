import { useEffect, useState } from "react";
import { apiGet, apiPost } from "../api.js";

export default function Users() {
  const [users, setUsers] = useState([]);
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState("student");
  const [code, setCode] = useState("");
  const [err, setErr] = useState("");

  const load = () => apiGet("/users").then(setUsers).catch((e) => setErr(String(e.message)));

  useEffect(() => {
    load();
  }, []);

  const submit = async (e) => {
    e.preventDefault();
    setErr("");
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
      await load();
    } catch (e) {
      setErr(e.message);
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
            <button type="submit" className="primary">
              Lưu
            </button>
          </form>
        </div>
        <div className="panel" style={{ flex: 1, minWidth: 280 }}>
          <h2>Danh sách</h2>
          <table className="table">
            <thead>
              <tr>
                <th>Họ tên</th>
                <th>Email</th>
                <th>ID</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td>{u.full_name}</td>
                  <td>{u.email}</td>
                  <td className="muted" style={{ fontSize: "0.75rem" }}>
                    {u.id}
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
