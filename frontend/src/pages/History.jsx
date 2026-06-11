import { useEffect, useState } from "react";
import { apiGet } from "../api.js";

export default function History() {
  const [events, setEvents] = useState([]);
  const [eventId, setEventId] = useState("");
  const [logs, setLogs] = useState([]);
  const [users, setUsers] = useState([]);
  const [assignments, setAssignments] = useState([]);

  useEffect(() => {
    Promise.all([apiGet("/events"), apiGet("/users")]).then(([ev, usr]) => {
      setEvents(ev);
      setUsers(usr);
      if (ev[0]) setEventId(ev[0].id);
    });
  }, []);

  useEffect(() => {
    if (!eventId) return;
    const q = new URLSearchParams({ event_id: eventId, limit: "100" });
    Promise.all([
      apiGet(`/attendance/history?${q.toString()}`),
      apiGet(`/events/${eventId}/users`)
    ]).then(([historyLogs, assignedList]) => {
      setLogs(historyLogs);
      setAssignments(assignedList);
    }).catch(console.error);
  }, [eventId]);

  const getUserInfo = (userId) => {
    const u = users.find((x) => x.id === userId);
    return u ? { name: u.full_name, code: u.student_code } : { name: "Người lạ", code: "--" };
  };

  const getStatus = (log) => {
    const { similarity, user_id } = log;
    
    // Check if user is recognized (similarity >= 0.45, matching RECOGNITION_THRESHOLD)
    const isRecognized = similarity !== null && similarity >= 0.45;
    if (!isRecognized) {
      return { text: "Chưa có trong danh sách sinh viên ban đầu", color: "#dc2626" };
    }

    // Check if the recognized user is assigned to this event
    const isAssigned = assignments.some((x) => x.id === user_id);
    if (!isAssigned) {
      return { text: "Chưa đăng ký sự kiện", color: "#d97706" };
    }

    return { text: "Hợp lệ", color: "#16a34a" };
  };

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
              <th>MSSV</th>
              <th>Sim</th>
              <th>Trạng thái</th>
              <th>Nguồn</th>
              <th>Ghi chú</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((l) => {
              const uInfo = getUserInfo(l.user_id);
              const status = getStatus(l);
              return (
                <tr key={l.id}>
                  <td className="muted">{new Date(l.created_at).toLocaleString()}</td>
                  <td style={{ fontWeight: 600 }}>{uInfo.name}</td>
                  <td>{uInfo.code || "--"}</td>
                  <td>{l.similarity != null ? l.similarity.toFixed(3) : "—"}</td>
                  <td>
                    <span style={{
                      display: "inline-block",
                      padding: "4px 8px",
                      borderRadius: "6px",
                      fontSize: "12px",
                      fontWeight: 600,
                      backgroundColor: status.color + "15",
                      color: status.color
                    }}>
                      {status.text}
                    </span>
                  </td>
                  <td>{l.source}</td>
                  <td className="muted">—</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
