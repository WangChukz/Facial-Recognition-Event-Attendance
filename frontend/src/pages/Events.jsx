import { useEffect, useState } from "react";
import { apiGet, apiPost, apiDelete } from "../api.js";
import { useToast } from "../context/ToastContext.jsx";
import { Loader2, Play, Square, Trash2 } from "lucide-react";

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
    const evWithSessions = await Promise.all(
      ev.map(async (e) => {
        try {
          const sessions = await apiGet(`/events/${e.id}/sessions`);
          return { ...e, sessions };
        } catch {
          return { ...e, sessions: [] };
        }
      })
    );
    setEvents(evWithSessions);
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
      addToast("Mở phiên điểm danh thành công!", "success");
      await load();
    } catch (e) {
      setErr(e.message);
      addToast("Có lỗi xảy ra khi mở phiên.", "error");
    }
  };

  const closeSession = async (sessionId) => {
    setErr("");
    try {
      await apiPost(`/events/sessions/${sessionId}/close`, {});
      addToast("Đóng phiên điểm danh thành công!", "success");
      await load();
    } catch (e) {
      setErr(e.message);
      addToast("Có lỗi xảy ra khi đóng phiên.", "error");
    }
  };

  const deleteEvent = async (eventId, eventName) => {
    if (!confirm(`Bạn có chắc muốn xóa sự kiện "${eventName}"? Các phiên và lịch sử điểm danh liên quan sẽ bị xóa sạch.`)) return;
    setErr("");
    try {
      await apiDelete(`/events/${eventId}`);
      addToast("Xóa sự kiện thành công!", "success");
      await load();
    } catch (e) {
      setErr(e.message);
      addToast("Có lỗi xảy ra khi xóa sự kiện.", "error");
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
            {err && <p style={{ color: "var(--danger)" }}>{err}</p>}
            <button type="submit" className="primary" disabled={loading} style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
              {loading && <Loader2 size={16} className="animate-spin" style={{ animation: "kiosk-spin 1s linear infinite" }} />}
              Tạo sự kiện
            </button>
          </form>
        </div>
        <div className="panel" style={{ minWidth: 0 }}>
          <h2>Danh sách & Phiên điểm danh</h2>
          <table className="table">
            <thead>
              <tr>
                <th>Tên sự kiện</th>
                <th>Phiên điểm danh</th>
                <th>Hành động</th>
              </tr>
            </thead>
            <tbody>
              {events.map((ev) => {
                const activeSession = ev.sessions?.find((s) => !s.closed_at);

                return (
                  <tr key={ev.id}>
                    <td>
                      <div style={{ fontWeight: 600 }}>{ev.name}</div>
                    </td>
                    <td>
                      {activeSession ? (
                        <div style={{ display: "flex", alignItems: "center", gap: 8, color: "#16a34a", fontWeight: 600 }}>
                          <span style={{ height: 8, width: 8, borderRadius: "50%", backgroundColor: "#16a34a", display: "inline-block" }}></span>
                          Đang mở (live)
                          <button
                            type="button"
                            onClick={() => closeSession(activeSession.id)}
                            style={{
                              display: "flex",
                              alignItems: "center",
                              gap: 4,
                              padding: "4px 8px",
                              fontSize: "0.8rem",
                              backgroundColor: "#fef2f2",
                              color: "#dc2626",
                              border: "1px solid #fecaca",
                              borderRadius: 4,
                              cursor: "pointer"
                            }}
                          >
                            <Square size={12} /> Đóng
                          </button>
                        </div>
                      ) : (
                        <button
                          type="button"
                          onClick={() => openSession(ev.id)}
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: 4,
                            padding: "4px 8px",
                            fontSize: "0.8rem",
                            backgroundColor: "#f0fdf4",
                            color: "#16a34a",
                            border: "1px solid #bbf7d0",
                            borderRadius: 4,
                            cursor: "pointer"
                          }}
                        >
                          <Play size={12} /> Mở phiên
                        </button>
                      )}
                    </td>
                    <td>
                      <button
                        type="button"
                        onClick={() => deleteEvent(ev.id, ev.name)}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 4,
                          padding: "4px 8px",
                          fontSize: "0.8rem",
                          backgroundColor: "#fef2f2",
                          color: "#dc2626",
                          border: "none",
                          borderRadius: 4,
                          cursor: "pointer"
                        }}
                      >
                        <Trash2 size={12} /> Xóa
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
