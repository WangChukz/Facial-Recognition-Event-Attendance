import { useEffect, useState } from "react";
import { apiGet, apiPost } from "../api.js";

export default function Events() {
  const [events, setEvents] = useState([]);
  const [users, setUsers] = useState([]);
  const [name, setName] = useState("");
  const [desc, setDesc] = useState("");
  const [createdBy, setCreatedBy] = useState("");
  const [err, setErr] = useState("");

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
    try {
      await apiPost("/events", {
        name,
        description: desc || null,
        created_by: createdBy || null,
      });
      setName("");
      setDesc("");
      await load();
    } catch (e) {
      setErr(e.message);
    }
  };

  const openSession = async (eventId) => {
    setErr("");
    try {
      await apiPost(`/events/${eventId}/sessions`, { name: "live" });
      await load();
    } catch (e) {
      setErr(e.message);
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
            <button type="submit" className="primary">
              Tạo
            </button>
          </form>
        </div>
        <div className="panel" style={{ flex: 1, minWidth: 320 }}>
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
                  <td>
                    <button type="button" onClick={() => openSession(ev.id)}>
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
