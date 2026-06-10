import { useEffect, useState } from "react";
import { apiGet, apiPost, apiDelete } from "../api.js";
import { useToast } from "../context/ToastContext.jsx";
import { Loader2, UserPlus, UserMinus } from "lucide-react";

export default function EventAssignments() {
  const [events, setEvents] = useState([]);
  const [selectedEventId, setSelectedEventId] = useState("");
  const [assignedUsers, setAssignedUsers] = useState([]);
  const [allUsers, setAllUsers] = useState([]);
  const [selectedUserIds, setSelectedUserIds] = useState([]);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [err, setErr] = useState("");
  const { addToast } = useToast();

  useEffect(() => {
    // Fetch events and all users
    Promise.all([apiGet("/events"), apiGet("/users")])
      .then(([evs, usr]) => {
        setEvents(evs);
        setAllUsers(usr);
        if (evs[0]) {
          setSelectedEventId(evs[0].id);
        }
      })
      .catch((e) => setErr(String(e.message)));
  }, []);

  useEffect(() => {
    if (!selectedEventId) return;
    loadAssignedUsers(selectedEventId);
  }, [selectedEventId]);

  const loadAssignedUsers = (eventId) => {
    setLoading(true);
    apiGet(`/events/${eventId}/users`)
      .then(setAssignedUsers)
      .catch((e) => addToast("Không thể tải danh sách sinh viên: " + e.message, "error"))
      .finally(() => setLoading(false));
  };

  const handleAssign = async (e) => {
    e.preventDefault();
    if (selectedUserIds.length === 0) {
      addToast("Vui lòng chọn ít nhất 1 sinh viên", "error");
      return;
    }
    setActionLoading(true);
    try {
      await apiPost(`/events/${selectedEventId}/users`, {
        user_ids: selectedUserIds,
      });
      addToast("Gán sinh viên vào sự kiện thành công!", "success");
      setSelectedUserIds([]);
      loadAssignedUsers(selectedEventId);
    } catch (e) {
      addToast(e.message, "error");
    } finally {
      setActionLoading(false);
    }
  };

  const handleUnassign = async (userId, name) => {
    if (!confirm(`Bạn có chắc chắn muốn gỡ sinh viên "${name}" khỏi sự kiện này?`)) return;
    setActionLoading(true);
    try {
      await apiDelete(`/events/${selectedEventId}/users/${userId}`);
      addToast("Đã gỡ sinh viên thành công!", "success");
      loadAssignedUsers(selectedEventId);
    } catch (e) {
      addToast(e.message, "error");
    } finally {
      setActionLoading(false);
    }
  };

  const toggleSelectUser = (userId) => {
    setSelectedUserIds((prev) =>
      prev.includes(userId) ? prev.filter((id) => id !== userId) : [...prev, userId]
    );
  };

  // Filter out users who are already assigned to show in the "Available" list
  const assignedIds = new Set(assignedUsers.map((u) => u.id));
  const availableUsers = allUsers.filter((u) => u.role === "student" && !assignedIds.has(u.id));

  return (
    <div>
      <h1>Gán sinh viên theo sự kiện</h1>
      {err && <p style={{ color: "var(--danger)" }}>{err}</p>}

      <div className="panel" style={{ marginBottom: 20 }}>
        <label style={{ fontWeight: 700, fontSize: 16 }}>
          Chọn Sự Kiện
          <select
            value={selectedEventId}
            onChange={(e) => {
              setSelectedEventId(e.target.value);
              setSelectedUserIds([]);
            }}
            style={{ marginTop: 8, padding: 10, fontSize: 15 }}
          >
            {events.length === 0 && <option value="">Chưa có sự kiện nào...</option>}
            {events.map((ev) => (
              <option key={ev.id} value={ev.id}>
                {ev.name} ({ev.location || "Chưa có địa điểm"})
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="row" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
        {/* Left: Available Students to Assign */}
        <div className="panel">
          <h2>Sinh viên chưa tham gia ({availableUsers.length})</h2>
          {availableUsers.length === 0 ? (
            <p className="muted">Tất cả sinh viên học sinh đã được gán vào sự kiện này.</p>
          ) : (
            <form onSubmit={handleAssign}>
              <div
                style={{
                  maxHeight: 400,
                  overflowY: "auto",
                  border: "1px solid var(--border)",
                  borderRadius: 6,
                  padding: 8,
                  marginBottom: 16,
                }}
              >
                {availableUsers.map((u) => (
                  <label
                    key={u.id}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 10,
                      padding: "8px 12px",
                      borderBottom: "1px solid var(--border)",
                      cursor: "pointer",
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={selectedUserIds.includes(u.id)}
                      onChange={() => toggleSelectUser(u.id)}
                    />
                    <div>
                      <div style={{ fontWeight: 600 }}>{u.full_name}</div>
                      <div className="muted" style={{ fontSize: 12 }}>
                        {u.student_code ? `Mã SV: ${u.student_code}` : u.email}
                      </div>
                    </div>
                  </label>
                ))}
              </div>
              <button
                type="submit"
                className="primary"
                disabled={selectedUserIds.length === 0 || actionLoading}
                style={{ display: "flex", alignItems: "center", gap: 8, justifyContent: "center", width: "100%" }}
              >
                {actionLoading ? (
                  <Loader2 size={16} className="animate-spin" />
                ) : (
                  <UserPlus size={16} />
                )}
                Gán {selectedUserIds.length > 0 ? `${selectedUserIds.length} sinh viên` : ""} vào sự kiện
              </button>
            </form>
          )}
        </div>

        {/* Right: Assigned Students List */}
        <div className="panel">
          <h2>Danh sách đã gán ({assignedUsers.length})</h2>
          {loading ? (
            <div style={{ display: "flex", justifyContent: "center", padding: 40 }}>
              <Loader2 size={32} className="animate-spin" />
            </div>
          ) : assignedUsers.length === 0 ? (
            <p className="muted">Chưa có sinh viên nào tham gia sự kiện này.</p>
          ) : (
            <div style={{ maxHeight: 460, overflowY: "auto" }}>
              <table className="table">
                <thead>
                  <tr>
                    <th>Họ tên</th>
                    <th>Mã SV</th>
                    <th>Hành động</th>
                  </tr>
                </thead>
                <tbody>
                  {assignedUsers.map((u) => (
                    <tr key={u.id}>
                      <td style={{ fontWeight: 600 }}>{u.full_name}</td>
                      <td>{u.student_code || <span className="muted">Không có</span>}</td>
                      <td>
                        <button
                          type="button"
                          className="danger-btn"
                          disabled={actionLoading}
                          onClick={() => handleUnassign(u.id, u.full_name)}
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: 4,
                            padding: "4px 8px",
                            backgroundColor: "var(--danger-bg)",
                            color: "var(--danger-text)",
                            border: "none",
                            borderRadius: 4,
                            cursor: "pointer",
                            fontSize: 12,
                          }}
                        >
                          <UserMinus size={14} /> Gỡ
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
