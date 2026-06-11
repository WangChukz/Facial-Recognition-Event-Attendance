import { useEffect, useState } from "react";
import { apiGet } from "../api.js";
import { Users, Calendar, CheckCircle2, XCircle, BarChart2 } from "lucide-react";

function StatCard({ icon: Icon, title, value, link, color = "#2257c2" }) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "12px",
        padding: "20px",
        backgroundColor: "#ffffff",
        border: "1px solid #dce3ee",
        borderRadius: "12px",
        boxShadow: "0 2px 8px rgba(38,57,89,0.04)",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        <div
          style={{
            width: 48,
            height: 48,
            borderRadius: "10px",
            backgroundColor: `${color}15`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <Icon size={24} color={color} />
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: "13px", color: "#8490a3", fontWeight: 500 }}>
            {title}
          </div>
        </div>
      </div>
      <div style={{ fontSize: "32px", fontWeight: 700, color: "#1f2937", lineHeight: 1 }}>
        {value.toLocaleString()}
      </div>
      {link && (
        <a href={link} style={{ fontSize: "13px", color: "#2257c2", textDecoration: "none", fontWeight: 600 }}>
          Xem chi tiết →
        </a>
      )}
    </div>
  );
}

function EventSummaryCharts({ selectedEvent, allUsers, allLogs, eventAssignments }) {
  if (!selectedEvent) return null;

  // 1. Total registered/assigned students for this event
  const assignedList = eventAssignments[selectedEvent.id] || [];
  const totalRegistered = assignedList.length;

  // 2. Filter logs relating to this event
  const eventLogs = allLogs.filter(l => l.event_id === selectedEvent.id);

  // 3. Count matching/recognized assigned users
  // An assigned user has scanned their face if they have an attendance log in this event
  const assignedUserIds = new Set(assignedList.map(u => u.id));
  const scannedAssignedUserIds = new Set(
    eventLogs
      .filter(l => assignedUserIds.has(l.user_id) && l.similarity !== null && l.similarity >= 0.45)
      .map(l => l.user_id)
  );

  const totalScannedRegistered = scannedAssignedUserIds.size;
  const totalNotScannedRegistered = Math.max(0, totalRegistered - totalScannedRegistered);

  // 4. Count unrecognized scans (similarity < 0.45 or user_id not registered in database at all)
  const allUserIds = new Set(allUsers.map(u => u.id));
  const unrecognizedLogsCount = eventLogs.filter(l => {
    const isRecognized = l.similarity !== null && l.similarity >= 0.45;
    const existsInDb = allUserIds.has(l.user_id);
    return !isRecognized || !existsInDb;
  }).length;

  const chartData = [
    { label: "Tổng HS/SV đăng ký tham gia", value: totalRegistered, color: "#2257c2" },
    { label: "Số HS/SV đăng ký đã quét điểm danh", value: totalScannedRegistered, color: "#15a34a" },
    { label: "Số HS/SV đăng ký chưa quét điểm danh", value: totalNotScannedRegistered, color: "#d97706" },
    { label: "Lượt quét không có trong CSDL (Người lạ)", value: unrecognizedLogsCount, color: "#dc2626" }
  ];

  const maxVal = Math.max(...chartData.map(c => c.value), 1);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, borderBottom: "1px solid #dce3ee", paddingBottom: 10 }}>
        <BarChart2 size={18} color="#2257c2" />
        <h3 style={{ margin: 0, fontSize: 14, fontWeight: 700, color: "#1e3266" }}>
          BIỂU ĐỒ BÁO CÁO: {selectedEvent.name.toUpperCase()}
        </h3>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 14, padding: "4px 0" }}>
        {chartData.map((item, idx) => {
          const percentage = Math.min(100, Math.round((item.value / maxVal) * 100));
          return (
            <div key={idx} style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, fontWeight: 600 }}>
                <span style={{ color: "#4b5563" }}>{item.label}</span>
                <span style={{ color: item.color }}>{item.value} sinh viên</span>
              </div>
              <div style={{ height: 24, backgroundColor: "#f3f4f6", borderRadius: 6, overflow: "hidden", position: "relative" }}>
                <div style={{
                  height: "100%",
                  width: `${percentage}%`,
                  backgroundColor: item.color,
                  borderRadius: 6,
                  transition: "width 0.5s ease-out-in"
                }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [stats, setStats] = useState({
    totalUsers: 0,
    totalEvents: 0,
    successfulAttendance: 0,
    failedAttendance: 0,
  });
  const [events, setEvents] = useState([]);
  const [allUsers, setAllUsers] = useState([]);
  const [allLogs, setAllLogs] = useState([]);
  const [eventAssignments, setEventAssignments] = useState({});
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    try {
      const [users, allEvents, attendance] = await Promise.all([
        apiGet("/users"),
        apiGet("/events"),
        apiGet("/attendance/history?limit=1000"),
      ]);

      setAllUsers(users);
      setAllLogs(attendance);
      setEvents(allEvents);

      // Fetch assignments for all events to compile charts
      const assignmentsMap = {};
      await Promise.all(
        allEvents.map(async (ev) => {
          try {
            const assignedList = await apiGet(`/events/${ev.id}/users`);
            assignmentsMap[ev.id] = assignedList;
          } catch {
            assignmentsMap[ev.id] = [];
          }
        })
      );
      setEventAssignments(assignmentsMap);

      const recognizedLogs = attendance.filter(a => a.similarity !== null && a.similarity >= 0.45);
      const unrecognizedLogs = attendance.filter(a => a.similarity === null || a.similarity < 0.45);

      setStats({
        totalUsers: users.length,
        totalEvents: allEvents.length,
        successfulAttendance: recognizedLogs.length,
        failedAttendance: unrecognizedLogs.length,
      });

      if (allEvents.length > 0) {
        setSelectedEvent(allEvents[0]);
      }
      setLoading(false);
    } catch (err) {
      console.error(err);
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  if (loading) {
    return (
      <div style={{ padding: "20px", textAlign: "center", color: "#8490a3" }}>
        Đang tải dữ liệu...
      </div>
    );
  }

  const recognizedLogs = allLogs.filter(a => a.similarity !== null && a.similarity >= 0.45);

  const getUserName = (userId) => {
    const u = allUsers.find(x => x.id === userId);
    return u ? u.full_name : "Người lạ";
  };

  const getEventName = (eventId) => {
    const e = events.find(x => x.id === eventId);
    return e ? e.name : "Sự kiện";
  };

  return (
    <div>
      <div style={{ marginBottom: "24px" }}>
        <h1 style={{ fontSize: "24px", fontWeight: 700, color: "#1e3266", margin: "0 0 8px" }}>
          Xin chào, Admin! 👋
        </h1>
        <p style={{ fontSize: "14px", color: "#8490a3", margin: 0 }}>
          Chào mừng bạn đến với hệ thống điểm danh bằng khuôn mặt.
        </p>
      </div>

      {/* Stats Grid */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
          gap: "16px",
          marginBottom: "24px",
        }}
      >
        <StatCard
          icon={Users}
          title="Tổng sinh viên"
          value={stats.totalUsers}
          link="/admin/users"
          color="#2257c2"
        />
        <StatCard
          icon={Calendar}
          title="Tổng sự kiện"
          value={stats.totalEvents}
          link="/admin/events"
          color="#7c3aed"
        />
        <StatCard
          icon={CheckCircle2}
          title="Lượt quét hợp lệ"
          value={stats.successfulAttendance}
          link="/admin/history"
          color="#15a34a"
        />
        <StatCard
          icon={XCircle}
          title="Lượt quét chưa xác định"
          value={stats.failedAttendance}
          link="/admin/history"
          color="#dc2626"
        />
      </div>

      {/* Charts and Events Selection Row */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1.6fr 1.4fr",
          gap: "20px",
          marginBottom: "24px",
          alignItems: "stretch"
        }}
      >
        {/* Dynamic Event Summary Charts */}
        <div
          style={{
            backgroundColor: "#ffffff",
            border: "1px solid #dce3ee",
            borderRadius: "12px",
            boxShadow: "0 2px 8px rgba(38,57,89,0.04)",
            padding: "20px",
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between"
          }}
        >
          {selectedEvent ? (
            <EventSummaryCharts
              selectedEvent={selectedEvent}
              allUsers={allUsers}
              allLogs={allLogs}
              eventAssignments={eventAssignments}
            />
          ) : (
            <div style={{ textAlign: "center", color: "#8490a3", padding: "40px 0" }}>
              Vui lòng chọn sự kiện bên cạnh để xem biểu đồ chi tiết
            </div>
          )}
        </div>

        {/* Event Selector List */}
        <div
          style={{
            backgroundColor: "#ffffff",
            border: "1px solid #dce3ee",
            borderRadius: "12px",
            boxShadow: "0 2px 8px rgba(38,57,89,0.04)",
            padding: "20px",
            display: "flex",
            flexDirection: "column",
            gap: "12px",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
            <h3 style={{ margin: 0, fontSize: "14px", fontWeight: 700, color: "#1f2937" }}>
              DANH SÁCH SỰ KIỆN (BẤM ĐỂ XEM BIỂU ĐỒ)
            </h3>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "10px", maxHeight: "320px", overflowY: "auto", paddingRight: 4 }}>
            {events.map((event, i) => {
              const isSelected = selectedEvent?.id === event.id;
              const participantsCount = (eventAssignments[event.id] || []).length;
              return (
                <div
                  key={i}
                  onClick={() => setSelectedEvent(event)}
                  style={{
                    display: "flex",
                    gap: "12px",
                    padding: "14px 12px",
                    backgroundColor: isSelected ? "#eef4ff" : "#f9fafb",
                    borderRadius: "8px",
                    border: isSelected ? "1px solid #2257c2" : "1px solid #e5e7eb",
                    cursor: "pointer",
                    transition: "all 0.2s ease",
                  }}
                >
                  <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", gap: "4px" }}>
                    <div style={{ fontSize: "14px", fontWeight: 700, color: isSelected ? "#2257c2" : "#1f2937" }}>
                      {event.name}
                    </div>
                    {event.description && (
                      <div className="muted" style={{ fontSize: "12px", textOverflow: "ellipsis", overflow: "hidden", whiteSpace: "nowrap" }}>
                        {event.description}
                      </div>
                    )}
                  </div>
                  <div style={{ textAlign: "right", display: "flex", flexDirection: "column", justifyContent: "center" }}>
                    <div style={{ fontSize: "13px", fontWeight: 700, color: isSelected ? "#2257c2" : "#4b5563" }}>
                      {participantsCount} sinh viên
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Latest Logs */}
      <div
        style={{
          backgroundColor: "#ffffff",
          border: "1px solid #dce3ee",
          borderRadius: "12px",
          boxShadow: "0 2px 8px rgba(38,57,89,0.04)",
          padding: "20px",
        }}
      >
        <h3 style={{ margin: "0 0 16px", fontSize: "14px", fontWeight: 700, color: "#1f2937" }}>
          NHẬT KÝ ĐIỂM DANH MỚI NHẤT
        </h3>
        <div style={{ overflowX: "auto" }}>
          <table
            style={{
              width: "100%",
              borderCollapse: "collapse",
              fontSize: "13px",
              color: "#1f2937",
            }}
          >
            <thead>
              <tr style={{ backgroundColor: "#f5f7fb", borderBottom: "1px solid #dce3ee" }}>
                <th style={{ padding: "10px 12px", textAlign: "left", fontWeight: 700, color: "#374151" }}>STT</th>
                <th style={{ padding: "10px 12px", textAlign: "left", fontWeight: 700, color: "#374151" }}>
                  Sự kiện
                </th>
                <th style={{ padding: "10px 12px", textAlign: "left", fontWeight: 700, color: "#374151" }}>
                  Họ tên
                </th>
                <th style={{ padding: "10px 12px", textAlign: "left", fontWeight: 700, color: "#374151" }}>
                  Thời gian
                </th>
                <th style={{ padding: "10px 12px", textAlign: "left", fontWeight: 700, color: "#374151" }}>
                  Similarity
                </th>
                <th style={{ padding: "10px 12px", textAlign: "left", fontWeight: 700, color: "#374151" }}>
                  Kết quả
                </th>
              </tr>
            </thead>
            <tbody>
              {allLogs.slice(0, 10).map((log, i) => {
                const isRecognized = log.similarity !== null && log.similarity >= 0.45;
                return (
                  <tr key={i} style={{ borderBottom: "1px solid #dce3ee" }}>
                    <td style={{ padding: "10px 12px" }}>{i + 1}</td>
                    <td style={{ padding: "10px 12px", fontWeight: 600 }}>{getEventName(log.event_id)}</td>
                    <td style={{ padding: "10px 12px", fontWeight: 600 }}>
                      {getUserName(log.user_id)}
                    </td>
                    <td style={{ padding: "10px 12px", fontSize: "12px", color: "#8490a3" }}>
                      {new Date(log.created_at).toLocaleString("vi-VN")}
                    </td>
                    <td style={{ padding: "10px 12px" }}>
                      {log.similarity != null ? log.similarity.toFixed(3) : "—"}
                    </td>
                    <td style={{ padding: "10px 12px" }}>
                      <span
                        style={{
                          display: "inline-block",
                          padding: "4px 10px",
                          borderRadius: "6px",
                          fontSize: "12px",
                          fontWeight: 600,
                          backgroundColor: isRecognized
                            ? "rgba(22, 163, 74, 0.12)"
                            : "rgba(220, 38, 38, 0.10)",
                          color: isRecognized
                            ? "#16a34a"
                            : "#dc2626",
                        }}
                      >
                        {isRecognized ? "Thành công" : "Thất bại"}
                      </span>
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
