import { useEffect, useState } from "react";
import { apiGet } from "../api.js";

export default function History() {
  const [events, setEvents] = useState([]);
  const [eventId, setEventId] = useState("");
  const [logs, setLogs] = useState([]);

  useEffect(() => {
    apiGet("/events").then((ev) => {
      setEvents(ev);
      if (ev[0]) setEventId(ev[0].id);
    });
  }, []);

  useEffect(() => {
    if (!eventId) return;
    const q = new URLSearchParams({ event_id: eventId, limit: "100" });
    apiGet(`/attendance/history?${q.toString()}`).then(setLogs);
  }, [eventId]);

  return (
    <div>
      <h1>Lịch sử điểm danh</h1>
      <div className="panel">
        <label>
          Sự kiện
          <select value={eventId} onChange={(e) => setEventId(e.target.value)}>
            {events.map((ev) => (
              <option key={ev.id} value={ev.id}>
                {ev.name}
              </option>
            ))}
          </select>
        </label>
        <table className="table" style={{ marginTop: "1rem" }}>
          <thead>
            <tr>
              <th>Thời gian</th>
              <th>User</th>
              <th>Hướng</th>
              <th>Sim</th>
              <th>Nguồn</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((l) => (
              <tr key={l.id}>
                <td className="muted">{new Date(l.created_at).toLocaleString()}</td>
                <td style={{ fontSize: "0.75rem" }}>{l.user_id}</td>
                <td>{l.direction}</td>
                <td>{l.similarity != null ? l.similarity.toFixed(3) : "—"}</td>
                <td>{l.source}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
