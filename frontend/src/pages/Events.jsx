import { useEffect, useState } from "react";
import { apiGet, apiPost } from "../api.js";
import { useToast } from "../context/ToastContext.jsx";
import { Loader2 } from "lucide-react";

export default function Events() {
  const [events, setEvents] = useState([]);
  const [users, setUsers] = useState([]);
  const [name, setName] = useState("");
  const [desc, setDesc] = useState("");
  const [createdBy, setCreatedBy] = useState("");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);
  const { addToast } = useToast();

  const load = async () => {
    const [ev, us] = await Promise.all([apiGet("/events"), apiGet("/users")]);
    setEvents(ev);
    setUsers(us);
    if (!createdBy && us[0]) setCreatedBy(us[0].id);
  };

  useEffect(() => {
    load().catch((e) => setErr(String(e.message)));
  }, []);

  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    setLoading(true);
    try {
      await apiPost("/events", {
        name,
        description: desc || null,
        created_by: createdBy || null,
      });
      setName("");
      setDesc("");
      addToast("Tạo sự kiện thành công!", "success");
      await load();
    } catch (e) {
      setErr(e.message);
      addToast("Có lỗi xảy ra khi tạo sự kiện.", "error");
    } finally {
      setLoading(false);
    }
  };

  const openSession = async (eventId) => {
    setErr("");
    try {
      await apiPost(`/events/${eventId}/sessions`, { name: "live" });
      addToast("Mở session thành công!", "success");
      await load();
    } catch (e) {
      setErr(e.message);
      addToast("Có lỗi xảy ra khi mở session.", "error");
    }
  };

  return (
    <div>
      <h1>Sự kiện</h1>
      <div className="row">
        <div className="panel form-grid">
          <h2>Tạo sự kiện</h2>
          <form onSubmit={submit}>
            <label>
              Tên
              <input value={name} onChange={(e) => setName(e.target.value)} required />
            </label>
            <label>
              Mô tả
              <input value={desc} onChange={(e) => setDesc(e.target.value)} />
            </label>
            <label>
              Người tạo (UUID)
              <select value={createdBy} onChange={(e) => setCreatedBy(e.target.value)}>
                <option value="">—</option>
                {users.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.full_name}
                  </option>
                ))}
              </select>
            </label>
            {err && <p style={{ color: "var(--danger)" }}>{err}</p>}
            <button type="submit" className="primary" disabled={loading} style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
              {loading && <Loader2 size={16} className="animate-spin" style={{ animation: "kiosk-spin 1s linear infinite" }} />}
              Tạo sự kiện
            </button>
          </form>
        </div>
        <div className="panel" style={{ minWidth: 0 }}>
          <h2>Danh sách & phiên</h2>
          <table className="table">
            <thead>
              <tr>
                <th>Tên</th>
                <th>ID</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {events.map((ev) => (
                <tr key={ev.id}>
                  <td>{ev.name}</td>
                  <td className="muted" style={{ fontSize: "0.72rem" }}>
                    {ev.id}
                  </td>
                  <td style={{ textAlign: "right" }}>
                    <button type="button" onClick={() => openSession(ev.id)} style={{ padding: "4px 12px", fontSize: "0.85rem", background: "var(--bg)", border: "1px solid var(--border)", color: "var(--text)" }}>
                      Mở session
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
