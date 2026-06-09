import { useEffect, useState } from "react";
import { apiGet } from "../api.js";
import { Users, Calendar, CheckCircle2, XCircle, TrendingUp } from "lucide-react";

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

function LineChart({ data, title }) {
  if (!data || data.length === 0) {
    return <div style={{ padding: "20px", color: "#8490a3" }}>Không có dữ liệu</div>;
  }

  const maxValue = Math.max(...data.map((d) => d.value), 1);
  const padding = 40;
  const chartHeight = 280;
  const chartWidth = 600;
  const canvasHeight = chartHeight + 2 * padding;
  const canvasWidth = chartWidth + 2 * padding;

  const xStep = chartWidth / (data.length - 1 || 1);
  const yStep = chartHeight / maxValue;

  const points = data.map((d, i) => ({
    x: padding + i * xStep,
    y: canvasHeight - padding - d.value * yStep,
  }));

  const pathData = points.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ");

  return (
    <div style={{ padding: "20px" }}>
      <h3 style={{ margin: "0 0 15px", fontSize: "14px", fontWeight: 700, color: "#1f2937" }}>
        {title}
      </h3>
      <svg width="100%" height={canvasHeight} style={{ overflow: "visible" }} viewBox={`0 0 ${canvasWidth} ${canvasHeight}`}>
        {/* Grid lines */}
        {[...Array(5)].map((_, i) => {
          const y = canvasHeight - padding - (i * chartHeight) / 4;
          return (
            <g key={`grid-${i}`}>
              <line
                x1={padding}
                y1={y}
                x2={canvasWidth - padding}
                y2={y}
                stroke="#e5e7eb"
                strokeWidth={1}
              />
            </g>
          );
        })}

        {/* Axes */}
        <line
          x1={padding}
          y1={padding}
          x2={padding}
          y2={canvasHeight - padding}
          stroke="#d1d5db"
          strokeWidth={2}
        />
        <line
          x1={padding}
          y1={canvasHeight - padding}
          x2={canvasWidth - padding}
          y2={canvasHeight - padding}
          stroke="#d1d5db"
          strokeWidth={2}
        />

        {/* Line chart */}
        <path d={pathData} stroke="#15a34a" strokeWidth={2} fill="none" strokeLinecap="round" strokeLinejoin="round" />
        <path
          d={`${pathData} L ${points[points.length - 1].x} ${canvasHeight - padding} L ${points[0].x} ${
            canvasHeight - padding
          } Z`}
          fill="#15a34a"
          opacity={0.1}
        />

        {/* Failure line (if exists) */}
        {data[0].failureValue !== undefined && (
          <>
            <path
              d={data
                .map((d, i) => `${i === 0 ? "M" : "L"} ${points[i].x} ${canvasHeight - padding - (d.failureValue || 0) * yStep}`)
                .join(" ")}
              stroke="#dc2626"
              strokeWidth={2}
              fill="none"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </>
        )}

        {/* X-axis labels */}
        {data.map((d, i) => (
          <text
            key={`x-${i}`}
            x={points[i].x}
            y={canvasHeight - padding + 20}
            textAnchor="middle"
            fontSize={12}
            fill="#6b7280"
          >
            {d.date}
          </text>
        ))}
      </svg>
    </div>
  );
}

function EventCard({ event }) {
  return (
    <div
      style={{
        display: "flex",
        gap: "12px",
        padding: "12px",
        backgroundColor: "#f9fafb",
        borderRadius: "8px",
        border: "1px solid #e5e7eb",
      }}
    >
      <div
        style={{
          width: 64,
          height: 64,
          borderRadius: "8px",
          backgroundColor: "#2257c2",
          flexShrink: 0,
        }}
      />
      <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", gap: "4px" }}>
        <div style={{ fontSize: "14px", fontWeight: 700, color: "#1f2937" }}>
          {event.name}
        </div>
        <div style={{ fontSize: "12px", color: "#8490a3" }}>
          📅 {new Date(event.date).toLocaleDateString("vi-VN")}
        </div>
        <div style={{ fontSize: "12px", color: "#8490a3" }}>
          📍 {event.location || "Chưa xác định"}
        </div>
      </div>
      <div style={{ textAlign: "right", display: "flex", flexDirection: "column", justifyContent: "center" }}>
        <div style={{ fontSize: "13px", fontWeight: 700, color: "#2257c2" }}>
          {event.participant_count || 0} sinh viên
        </div>
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
  const [chartData, setChartData] = useState([]);
  const [events, setEvents] = useState([]);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const [users, allEvents, attendance] = await Promise.all([
          apiGet("/users"),
          apiGet("/events"),
          apiGet("/attendance/history?limit=1000"),
        ]);

        setStats({
          totalUsers: users.length,
          totalEvents: allEvents.length,
          successfulAttendance: attendance.filter((a) => a.direction === "in").length,
          failedAttendance: attendance.filter((a) => a.direction === "out").length,
        });

        // Process chart data - attendance by date
        const dateMap = {};
        attendance.forEach((log) => {
          const date = new Date(log.created_at).toLocaleDateString("vi-VN", {
            month: "2-digit",
            day: "2-digit",
          });
          if (!dateMap[date]) {
            dateMap[date] = { success: 0, failure: 0 };
          }
          if (log.direction === "in") {
            dateMap[date].success++;
          } else {
            dateMap[date].failure++;
          }
        });

        const chartDataArray = Object.entries(dateMap)
          .map(([date, data]) => ({
            date,
            value: data.success,
            failureValue: data.failure,
          }))
          .slice(-7); // Last 7 days

        setChartData(chartDataArray);
        setEvents(allEvents.slice(0, 3));
        setLogs(attendance.slice(0, 10));
        setLoading(false);
      } catch (err) {
        console.error(err);
        setLoading(false);
      }
    };

    load();
  }, []);

  if (loading) {
    return (
      <div style={{ padding: "20px", textAlign: "center", color: "#8490a3" }}>
        Đang tải dữ liệu...
      </div>
    );
  }

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
          title="Điểm danh thành công"
          value={stats.successfulAttendance}
          link="/admin/history"
          color="#15a34a"
        />
        <StatCard
          icon={XCircle}
          title="Điểm danh thất bại"
          value={stats.failedAttendance}
          link="/admin/history"
          color="#dc2626"
        />
      </div>

      {/* Charts and Events Row */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "2fr 1fr",
          gap: "16px",
          marginBottom: "24px",
        }}
      >
        {/* Chart */}
        <div
          style={{
            backgroundColor: "#ffffff",
            border: "1px solid #dce3ee",
            borderRadius: "12px",
            boxShadow: "0 2px 8px rgba(38,57,89,0.04)",
            overflow: "hidden",
          }}
        >
          <LineChart data={chartData} title="THỐNG KÊ ĐIỂM DANH" />
          <div style={{ display: "flex", gap: "24px", padding: "0 20px 20px", fontSize: "12px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <div style={{ width: 12, height: 12, borderRadius: 2, backgroundColor: "#15a34a" }} />
              <span style={{ color: "#374151" }}>Thành công</span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <div style={{ width: 12, height: 12, borderRadius: 2, backgroundColor: "#dc2626" }} />
              <span style={{ color: "#374151" }}>Thất bại</span>
            </div>
          </div>
        </div>

        {/* Upcoming Events */}
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
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
            <h3 style={{ margin: 0, fontSize: "14px", fontWeight: 700, color: "#1f2937" }}>
              SỰ KIỆN SẮP DIỄN RA
            </h3>
            <a href="/admin/events" style={{ fontSize: "13px", color: "#2257c2", textDecoration: "none" }}>
              Xem tất cả
            </a>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            {events.length > 0 ? (
              events.map((event, i) => <EventCard key={i} event={event} />)
            ) : (
              <div style={{ padding: "12px", color: "#8490a3", fontSize: "13px" }}>
                Không có sự kiện
              </div>
            )}
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
          NHẬT KỲ ĐIỂM DANH MỚI NHẤT
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
                  Mã sinh viên
                </th>
                <th style={{ padding: "10px 12px", textAlign: "left", fontWeight: 700, color: "#374151" }}>
                  Hướng
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
              {logs.map((log, i) => (
                <tr key={i} style={{ borderBottom: "1px solid #dce3ee" }}>
                  <td style={{ padding: "10px 12px" }}>{i + 1}</td>
                  <td style={{ padding: "10px 12px" }}>Event</td>
                  <td style={{ padding: "10px 12px", fontSize: "12px", color: "#8490a3" }}>
                    {log.user_id?.substring(0, 8)}...
                  </td>
                  <td style={{ padding: "10px 12px" }}>{log.direction}</td>
                  <td style={{ padding: "10px 12px", fontSize: "12px", color: "#8490a3" }}>
                    {new Date(log.created_at).toLocaleString("vi-VN")}
                  </td>
                  <td style={{ padding: "10px 12px" }}>
                    {log.similarity != null ? log.similarity.toFixed(2) : "—"}
                  </td>
                  <td style={{ padding: "10px 12px" }}>
                    <span
                      style={{
                        display: "inline-block",
                        padding: "4px 10px",
                        borderRadius: "6px",
                        fontSize: "12px",
                        fontWeight: 600,
                        backgroundColor:
                          log.similarity != null && log.similarity > 0.7
                            ? "rgba(22, 163, 74, 0.12)"
                            : "rgba(220, 38, 38, 0.10)",
                        color:
                          log.similarity != null && log.similarity > 0.7
                            ? "#16a34a"
                            : "#dc2626",
                      }}
                    >
                      {log.similarity != null && log.similarity > 0.7 ? "Thành công" : "Thất bại"}
                    </span>
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
