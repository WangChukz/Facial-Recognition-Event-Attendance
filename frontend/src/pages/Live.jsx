import { useCallback, useEffect, useRef, useState } from "react";
import { apiGet } from "../api.js";

function wsUrl(path) {
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${window.location.host}${path}`;
}

export default function Live() {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const lastFrameRef = useRef(null);
  const [events, setEvents] = useState([]);
  const [eventId, setEventId] = useState("");
  const [sessionId, setSessionId] = useState("");
  const [running, setRunning] = useState(false);
  const [last, setLast] = useState(null);
  const [err, setErr] = useState("");
  const wsRef = useRef(null);
  const capRef = useRef(null);

  const drawOverlay = useCallback((data) => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;

    const rect = video.getBoundingClientRect();
    const w = Math.max(1, Math.floor(rect.width));
    const h = Math.max(1, Math.floor(rect.height));
    canvas.width = w;
    canvas.height = h;

    const ctx = canvas.getContext("2d", { alpha: true });
    if (!ctx) return;
    ctx.clearRect(0, 0, w, h);

    if (!data?.faces?.length) return;

    const fw = data.frame_shape?.[1] || video.videoWidth || w;
    const fh = data.frame_shape?.[0] || video.videoHeight || h;
    const sx = w / fw;
    const sy = h / fh;

    data.faces.forEach((f) => {
      const [x1, y1, x2, y2] = f.bbox;
      const px = x1 * sx;
      const py = y1 * sy;
      const pw = (x2 - x1) * sx;
      const ph = (y2 - y1) * sy;

      const stroke =
        f.status === "known" ? "#3fb950" : f.status === "uncertain" ? "#d29922" : "#f85149";
      ctx.strokeStyle = stroke;
      ctx.lineWidth = 2.5;
      ctx.strokeRect(px, py, pw, ph);

      const label =
        f.full_name ||
        (f.status === "unknown" ? "Unknown" : f.status === "uncertain" ? "Uncertain" : "");
      const sim = f.similarity != null ? f.similarity.toFixed(2) : "";
      const text = `${label} ${sim}`.trim();

      const padX = 8;
      const padY = 5;
      const barH = 26;
      ctx.font = "600 14px DM Sans, system-ui, sans-serif";
      const tw = Math.min(ctx.measureText(text).width + padX * 2, w - px - 4);
      const bx = px;
      const by = Math.max(4, py - barH - 4);

      ctx.fillStyle = "rgba(13, 17, 23, 0.82)";
      ctx.fillRect(bx, by, tw, barH);
      ctx.strokeStyle = stroke;
      ctx.lineWidth = 1;
      ctx.strokeRect(bx, by, tw, barH);

      ctx.fillStyle = "#f0f3f6";
      ctx.fillText(text, bx + padX, by + barH - padY - 2);
    });
  }, []);

  const clearOverlay = useCallback(() => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;
    const rect = video.getBoundingClientRect();
    canvas.width = Math.max(1, Math.floor(rect.width));
    canvas.height = Math.max(1, Math.floor(rect.height));
    canvas.getContext("2d")?.clearRect(0, 0, canvas.width, canvas.height);
  }, []);

  useEffect(() => {
    apiGet("/events")
      .then((ev) => {
        setEvents(ev);
        if (ev[0]) setEventId(ev[0].id);
      })
      .catch((e) => setErr(String(e.message)));
  }, []);

  useEffect(() => {
    if (!eventId) return;
    apiGet(`/events/${eventId}/sessions`)
      .then((s) => {
        if (s[0]) setSessionId(s[0].id);
        else setSessionId("");
      })
      .catch(() => setSessionId(""));
  }, [eventId]);

  useEffect(() => {
    let stream;
    (async () => {
      try {
        stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          await videoRef.current.play();
        }
      } catch (e) {
        setErr("Không mở được webcam: " + e.message);
      }
    })();
    return () => {
      stream?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  useEffect(() => {
    if (!running) {
      wsRef.current?.close();
      if (capRef.current) clearTimeout(capRef.current);
      clearOverlay();
      return;
    }
    const params = new URLSearchParams();
    if (eventId) params.set("event_id", eventId);
    if (sessionId) params.set("session_id", sessionId);
    params.set("auto_attendance", "true");
    const ws = new WebSocket(wsUrl(`/api/ws/live?${params.toString()}`));
    wsRef.current = ws;

    let active = true;

    ws.onopen = () => {
      if (active) {
        sendFrame(ws);
      }
    };
    ws.onmessage = (ev) => {
      if (!active) return;
      const data = JSON.parse(ev.data);
      lastFrameRef.current = data;
      setLast(data);
      requestAnimationFrame(() => drawOverlay(data));

      // Gửi khung hình tiếp theo chỉ sau khi backend đã xử lý xong khung hình trước
      capRef.current = setTimeout(() => {
        if (active && ws.readyState === WebSocket.OPEN) {
          sendFrame(ws);
        }
      }, 80); // Khoảng nghỉ 80ms giúp CPU bớt tải và tránh dồn ứ hàng đợi
    };
    ws.onerror = () => setErr("WebSocket lỗi");
    ws.onclose = () => {
      if (capRef.current) clearTimeout(capRef.current);
    };
    return () => {
      active = false;
      ws.close();
      if (capRef.current) clearTimeout(capRef.current);
    };
  }, [running, eventId, sessionId, drawOverlay, clearOverlay]);

  useEffect(() => {
    const onResize = () => {
      if (lastFrameRef.current) drawOverlay(lastFrameRef.current);
      else clearOverlay();
    };
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, [drawOverlay, clearOverlay]);

  const sendFrame = (ws) => {
    const video = videoRef.current;
    if (!video || video.readyState < 2 || ws.readyState !== WebSocket.OPEN) return;
    const w = video.videoWidth;
    const h = video.videoHeight;
    if (!w || !h) return;
    const c = document.createElement("canvas");
    c.width = w;
    c.height = h;
    const ctx = c.getContext("2d");
    ctx.drawImage(video, 0, 0, w, h);
    const b64 = c.toDataURL("image/jpeg", 0.55).split(",")[1];
    ws.send(JSON.stringify({ type: "frame", image: b64 }));
  };

  return (
    <div className="live-page">
      <header>
        <h1>Webcam realtime</h1>
        <p className="live-lead muted">
          Luồng camera vẫn hiển thị phía dưới; khung và nhãn được vẽ trên lớp canvas trong suốt. Bật gửi khung hình để
          nhận diện và (tuỳ chọn) ghi check-in theo sự kiện.
        </p>
      </header>

      <div className="panel live-shell">
        <div className="live-grid">
          <div className="live-stage">
            <div className="live-stage-inner">
              <video
                ref={videoRef}
                className="live-video"
                playsInline
                muted
                onLoadedMetadata={() => {
                  if (lastFrameRef.current) requestAnimationFrame(() => drawOverlay(lastFrameRef.current));
                }}
              />
              <canvas ref={canvasRef} className="live-overlay" aria-hidden />
            </div>
          </div>

          <aside className="live-aside">
            <div className={`live-status ${running ? "on" : ""}`}>
              <span className="live-status-dot" />
              {running ? "Đang gửi & nhận diện" : "Chờ bật"}
            </div>

            <label>
              Sự kiện (auto check-in)
              <select value={eventId} onChange={(e) => setEventId(e.target.value)}>
                {events.map((ev) => (
                  <option key={ev.id} value={ev.id}>
                    {ev.name}
                  </option>
                ))}
              </select>
            </label>

            <div>
              <div className="muted" style={{ fontSize: "0.78rem", marginBottom: "0.35rem" }}>
                Session hiện tại
              </div>
              <div className="live-session">{sessionId || "— Chưa có session — mở từ trang Sự kiện"}</div>
            </div>

            <button type="button" className="primary" onClick={() => setRunning((r) => !r)}>
              {running ? "Dừng nhận diện" : "Bắt đầu gửi khung hình"}
            </button>

            {err && <p style={{ color: "var(--danger)", margin: 0, fontSize: "0.9rem" }}>{err}</p>}

            {last?.faces?.length > 0 && (
              <div className="live-results">
                <h2 style={{ margin: "0.25rem 0 0.5rem", fontSize: "0.95rem" }}>Khung gần nhất</h2>
                {last.faces.map((f, i) => (
                  <div key={i} className="live-result-row">
                    <span className={`badge ${f.status}`}>{f.status}</span>
                    <span className="live-result-name">{f.full_name || "—"}</span>
                    <span className="live-result-meta">
                      sim {f.similarity?.toFixed?.(3) ?? "—"}
                      {f.attendance_logged ? " · đã check-in" : ""}
                      {f.gallery_enriched && (
                        <span style={{
                          color: "#1d4ed8",
                          backgroundColor: "#eff6ff",
                          border: "1px solid #bfdbfe",
                          padding: "1px 6px",
                          borderRadius: "4px",
                          fontSize: "0.7rem",
                          fontWeight: 600,
                          marginLeft: "6px",
                          display: "inline-flex",
                          alignItems: "center",
                          gap: 2
                        }}>
                          ✨ Tối ưu mẫu
                        </span>
                      )}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </aside>
        </div>
      </div>
    </div>
  );
}
