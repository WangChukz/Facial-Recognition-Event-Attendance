import { useState, useRef, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import { apiGet, apiPostForm, apiPost } from "../api.js";
import {
  Camera, Calendar, MapPin, Clock, Info, CheckCircle2,
  XCircle, RotateCcw, ImagePlus, User, Loader2, Shield
} from "lucide-react";

function wsUrl(path) {
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${window.location.host}${path}`;
}

/* ── Inline style constants ─────────────────────────── */
const COLOR = {
  navy:    "#1e3266",
  navyDk:  "#152550",
  blue50:  "#eff6ff",
  blue100: "#dbeafe",
  blue600: "#2563eb",
  green50: "#f0fdf4",
  green200:"#bbf7d0",
  green500:"#22c55e",
  green700:"#15803d",
  red50:   "#fef2f2",
  red200:  "#fecaca",
  red500:  "#ef4444",
  red700:  "#b91c1c",
  gray50:  "#f9fafb",
  gray100: "#f3f4f6",
  gray200: "#e5e7eb",
  gray300: "#d1d5db",
  gray400: "#9ca3af",
  gray500: "#6b7280",
  gray700: "#374151",
  gray800: "#1f2937",
  white:   "#ffffff",
};

const s = {
  /* Root shell */
  root: {
    position: "fixed", inset: 0,
    display: "flex", flexDirection: "column",
    backgroundColor: COLOR.gray50,
    fontFamily: "ui-sans-serif, system-ui, -apple-system, sans-serif",
    color: COLOR.gray800, overflow: "hidden",
  },

  /* Header */
  header: {
    backgroundColor: COLOR.navy, color: COLOR.white,
    padding: "10px 24px",
    display: "flex", justifyContent: "space-between", alignItems: "center",
    flexShrink: 0, boxShadow: "0 2px 8px rgba(0,0,0,0.25)",
  },
  logoRow: { display: "flex", alignItems: "center", gap: 12 },
  logoImg: {
    height: 48, padding: 4, borderRadius: 6,
    backgroundColor: COLOR.white, objectFit: "contain",
  },
  headerTitle: { margin: 0, fontSize: 18, fontWeight: 700, letterSpacing: 1 },
  headerSub:   { margin: 0, fontSize: 12, color: "#93c5fd" },
  clockBox: { textAlign: "right" },
  clockTime: { display: "flex", alignItems: "center", gap: 6, fontSize: 20, fontWeight: 700, fontVariantNumeric: "tabular-nums" },
  clockDate: { fontSize: 12, color: "#93c5fd", marginTop: 2 },

  /* Main */
  main: {
    flex: 1, minHeight: 0,
    display: "flex", flexDirection: "column",
    padding: "12px 24px 8px", gap: 10, overflow: "hidden",
  },

  /* Title */
  titleBox: { textAlign: "center", flexShrink: 0 },
  titleH:   { margin: 0, fontSize: 20, fontWeight: 800, color: COLOR.navy, textTransform: "uppercase", letterSpacing: 1 },
  titleSub: { margin: "2px 0 0", fontSize: 13, color: COLOR.gray500 },

  /* Event bar */
  eventBar: {
    backgroundColor: COLOR.white, border: `1px solid ${COLOR.gray200}`,
    borderRadius: 12, padding: "10px 16px",
    display: "flex", justifyContent: "space-between", alignItems: "center",
    flexShrink: 0, boxShadow: "0 1px 4px rgba(0,0,0,0.06)",
  },
  eventLeft:  { display: "flex", alignItems: "center", gap: 12 },
  eventIcon:  { backgroundColor: COLOR.blue50, borderRadius: "50%", padding: 10, color: COLOR.blue600, display:"flex" },
  eventName:  { margin: 0, fontWeight: 700, fontSize: 15, textTransform: "uppercase" },
  eventMeta:  { display: "flex", gap: 16, marginTop: 3, fontSize: 12, color: COLOR.gray500 },
  eventMetaItem: { display: "flex", alignItems: "center", gap: 4 },
  btnOutline: {
    display: "flex", alignItems: "center", gap: 6,
    padding: "8px 16px", border: `1px solid ${COLOR.blue100}`,
    borderRadius: 8, backgroundColor: COLOR.white, color: COLOR.blue600,
    fontWeight: 600, fontSize: 13, cursor: "pointer",
  },

  /* Grid */
  grid: {
    flex: 1, minHeight: 0,
    display: "grid", gridTemplateColumns: "1fr 340px", gap: 16,
  },

  /* Left column */
  leftCol: { display: "flex", flexDirection: "column", gap: 10, minHeight: 0 },

  /* Video wrapper */
  videoWrap: {
    flex: 1, minHeight: 0,
    backgroundColor: "#0a0e14", borderRadius: 16,
    overflow: "hidden", position: "relative",
    border: `3px solid ${COLOR.white}`,
    boxShadow: "0 4px 20px rgba(0,0,0,0.18)",
  },
  videoEl: { width: "100%", height: "100%", objectFit: "cover", display: "block" },
  videoOverlay: {
    position: "absolute",
    inset: 0,
    width: "100%",
    height: "100%",
    pointerEvents: "none",
  },
  cameraStatus: {
    position: "absolute", top: 12, left: 12,
    backgroundColor: "rgba(0,0,0,0.55)", backdropFilter: "blur(8px)",
    color: COLOR.white, padding: "5px 12px", borderRadius: 999,
    display: "flex", alignItems: "center", gap: 6, fontSize: 12,
  },
  realtimeStatus: {
    position: "absolute", top: 12, right: 12,
    backgroundColor: "rgba(0,0,0,0.55)", backdropFilter: "blur(8px)",
    color: COLOR.white, padding: "5px 12px", borderRadius: 999,
    display: "flex", alignItems: "center", gap: 6, fontSize: 12,
  },
  dot: (on) => ({
    width: 9, height: 9, borderRadius: "50%",
    backgroundColor: on ? "#22c55e" : "#ef4444",
    boxShadow: on ? "0 0 0 3px rgba(34,197,94,0.3)" : "none",
    animation: on ? "kiosk-pulse 2s infinite" : "none",
  }),
  bracketWrap: {
    position: "absolute", inset: 0,
    display: "flex", alignItems: "center", justifyContent: "center",
    pointerEvents: "none",
  },
  bracketInner: { width: 220, height: 220, position: "relative" },
  corner: (pos) => {
    const [t,r,b,l] = pos;
    return {
      position: "absolute",
      top:    t != null ? t : undefined,
      right:  r != null ? r : undefined,
      bottom: b != null ? b : undefined,
      left:   l != null ? l : undefined,
      width: 28, height: 28,
      borderTop:    t != null ? "3px solid rgba(255,255,255,0.75)" : undefined,
      borderBottom: b != null ? "3px solid rgba(255,255,255,0.75)" : undefined,
      borderLeft:   l != null ? "3px solid rgba(255,255,255,0.75)" : undefined,
      borderRight:  r != null ? "3px solid rgba(255,255,255,0.75)" : undefined,
      borderTopLeftRadius:     (t != null && l != null) ? 6 : undefined,
      borderTopRightRadius:    (t != null && r != null) ? 6 : undefined,
      borderBottomLeftRadius:  (b != null && l != null) ? 6 : undefined,
      borderBottomRightRadius: (b != null && r != null) ? 6 : undefined,
    };
  },
  uploadPlaceholder: {
    display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
    color: COLOR.gray400, height: "100%",
  },

  /* Loading overlay */
  loadingOverlay: {
    position: "absolute", inset: 0,
    backgroundColor: "rgba(0,0,0,0.6)", backdropFilter: "blur(4px)",
    display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
    color: COLOR.white, zIndex: 10,
  },
  loadingText: { marginTop: 12, fontSize: 18, fontWeight: 600 },

  /* Action row */
  actionRow: { display: "flex", gap: 12, flexShrink: 0 },
  btnCapture: (disabled) => ({
    flex: 1, display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
    padding: "12px 0", borderRadius: 12, border: "none",
    backgroundColor: disabled ? COLOR.gray300 : COLOR.navy,
    color: disabled ? COLOR.gray500 : COLOR.white,
    fontWeight: 700, fontSize: 16, cursor: disabled ? "not-allowed" : "pointer",
    boxShadow: "0 3px 10px rgba(0,0,0,0.15)", letterSpacing: 0.5,
    fontFamily: "inherit",
  }),
  hintText: { textAlign: "center", fontSize: 12, color: COLOR.gray400, margin: 0 },
  switchLink: {
    display: "block", textAlign: "center",
    fontSize: 12, color: COLOR.blue600, cursor: "pointer",
    textDecoration: "underline", background: "none", border: "none",
    fontFamily: "inherit",
  },

  /* Right column */
  rightCol: { display: "flex", flexDirection: "column", gap: 12, minHeight: 0, overflow: "hidden" },

  /* Cards */
  card: {
    backgroundColor: COLOR.white, border: `1px solid ${COLOR.gray200}`,
    borderRadius: 14, boxShadow: "0 1px 6px rgba(0,0,0,0.07)",
    overflow: "hidden",
  },
  cardHead: {
    padding: "10px 18px", backgroundColor: COLOR.gray50,
    borderBottom: `1px solid ${COLOR.gray100}`,
    fontWeight: 700, fontSize: 13, textTransform: "uppercase", letterSpacing: 0.5,
  },
  cardBody: { padding: "14px 18px" },
  guideList: { listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: 10 },
  guideItem: { display: "flex", alignItems: "flex-start", gap: 10, fontSize: 13, color: COLOR.gray600 },

  /* Result section */
  resultCard: {
    backgroundColor: COLOR.white, border: `1px solid ${COLOR.gray200}`,
    borderRadius: 14, boxShadow: "0 1px 6px rgba(0,0,0,0.07)",
    overflow: "hidden", flex: 1, display: "flex", flexDirection: "column",
    minHeight: 0,
  },
  resultBody: { padding: "16px 18px", flex: 1, display: "flex", flexDirection: "column", justifyContent: "center", overflow: "auto" },
  waitBox:  { textAlign: "center", color: COLOR.gray400, padding: "24px 0" },
  spinner:  {
    width: 48, height: 48, borderRadius: "50%",
    border: `4px solid ${COLOR.gray100}`, borderTopColor: COLOR.gray300,
    animation: "kiosk-spin 1s linear infinite",
    margin: "0 auto 10px",
  },

  /* Success / Fail box */
  resultBanner: (ok) => ({
    backgroundColor: ok ? COLOR.green50  : COLOR.red50,
    border: `1px solid ${ok ? COLOR.green200 : COLOR.red200}`,
    borderRadius: 12, padding: "12px 16px",
    display: "flex", alignItems: "center", gap: 12, marginBottom: 14,
  }),
  resultIconWrap: (ok) => ({
    backgroundColor: ok ? COLOR.green500 : COLOR.red500,
    color: COLOR.white, borderRadius: "50%", padding: 6,
    display: "flex", flexShrink: 0,
  }),
  resultTitle: (ok) => ({ margin: 0, fontWeight: 700, fontSize: 15, textTransform: "uppercase", color: ok ? COLOR.green700 : COLOR.red700 }),
  resultSub:   (ok) => ({ margin: "3px 0 0", fontSize: 13, color: ok ? COLOR.green700 : COLOR.red700 }),

  detailRow: { display: "flex", justifyContent: "space-between", padding: "6px 0", borderBottom: `1px dashed ${COLOR.gray200}`, fontSize: 13 },
  detailLabel: { color: COLOR.gray500 },
  detailValue: { fontWeight: 600 },

  thanksBox: {
    backgroundColor: COLOR.green50, border: `1px solid ${COLOR.green200}`,
    borderRadius: 8, padding: "8px 12px",
    display: "flex", alignItems: "flex-start", gap: 8,
    fontSize: 12, color: COLOR.green700, marginTop: 10,
  },
  btnReset: {
    width: "100%", marginTop: 12, padding: "9px 0",
    border: `1px solid ${COLOR.blue100}`, borderRadius: 8,
    backgroundColor: COLOR.white, color: COLOR.blue600,
    fontWeight: 600, fontSize: 13, cursor: "pointer",
    display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
    fontFamily: "inherit",
  },

  /* Footer */
  footer: {
    backgroundColor: "#eff6ff", borderTop: `1px solid ${COLOR.blue100}`,
    padding: "6px 24px", fontSize: 12, color: "#1d4ed8",
    display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
    flexShrink: 0,
  },

  /* Modal */
  modalBackdrop: {
    position: "fixed", inset: 0,
    backgroundColor: "rgba(0,0,0,0.5)", backdropFilter: "blur(4px)",
    display: "flex", alignItems: "center", justifyContent: "center",
    zIndex: 100, padding: 16,
  },
  modalBox: {
    backgroundColor: COLOR.white, borderRadius: 16,
    boxShadow: "0 20px 60px rgba(0,0,0,0.3)",
    width: "100%", maxWidth: 420, overflow: "hidden",
  },
  modalHead: {
    padding: "14px 20px", backgroundColor: COLOR.gray50,
    borderBottom: `1px solid ${COLOR.gray100}`,
    display: "flex", justifyContent: "space-between", alignItems: "center",
  },
  modalTitle: { margin: 0, fontWeight: 700, fontSize: 16 },
  modalBody:  { padding: 20, display: "flex", flexDirection: "column", gap: 14 },
  modalLabel: { display: "block", fontSize: 13, fontWeight: 600, color: COLOR.gray700, marginBottom: 4 },
  modalSelect: {
    width: "100%", padding: "9px 12px", borderRadius: 8,
    border: `1px solid ${COLOR.gray300}`, fontSize: 14,
    backgroundColor: COLOR.white, color: COLOR.gray800, fontFamily: "inherit",
    outline: "none",
  },
  btnPrimary: (disabled) => ({
    width: "100%", padding: "11px 0", borderRadius: 8, border: "none",
    backgroundColor: disabled ? COLOR.gray300 : COLOR.navy,
    color: disabled ? COLOR.gray500 : COLOR.white,
    fontWeight: 700, fontSize: 15, cursor: disabled ? "not-allowed" : "pointer",
    fontFamily: "inherit",
  }),
  iconBtn: {
    background: "none", border: "none", cursor: "pointer",
    color: COLOR.gray400, display: "flex", alignItems: "center",
    padding: 4,
  },
};

/* Keyframes injected once */
if (!document.getElementById("kiosk-keyframes")) {
  const el = document.createElement("style");
  el.id = "kiosk-keyframes";
  el.textContent = `
    @keyframes kiosk-spin  { to { transform: rotate(360deg); } }
    @keyframes kiosk-pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
  `;
  document.head.appendChild(el);
}

/* ── Component ───────────────────────────────────────── */
export default function ClientSimulation() {
  const [events,   setEvents]   = useState([]);
  const [sessions, setSessions] = useState([]);
  const [selEvent,  setSelEvent]  = useState(null);
  const [selSession,setSelSession]= useState(null);
  const [time,     setTime]     = useState(new Date());
  const [mode,     setMode]     = useState("camera");
  const [loading,  setLoading]  = useState(false);
  const [result,   setResult]   = useState(null);
  const [showModal,setShowModal]= useState(false);
  const [camOk,    setCamOk]    = useState(false);
  const [liveState,setLiveState]= useState("idle");
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const wsRef = useRef(null);
  const capRef = useRef(null);
  const lastFrameRef = useRef(null);
  const lastSuccessRef = useRef("");
  const lastFailureAtRef = useRef(0);

  /* Clock */
  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  const fmtTime = d => d.toLocaleTimeString("vi-VN", { hour:"2-digit", minute:"2-digit", second:"2-digit" });
  const fmtDate = d => {
    const days = ["Chủ Nhật","Thứ Hai","Thứ Ba","Thứ Tư","Thứ Năm","Thứ Sáu","Thứ Bảy"];
    return `${days[d.getDay()]}, ${d.toLocaleDateString("vi-VN")}`;
  };

  /* Load events */
  useEffect(() => {
    apiGet("/events").then(evs => {
      setEvents(evs);
      if (evs.length) { setSelEvent(evs[0]); loadSessions(evs[0].id); }
      else setShowModal(true);
    }).catch(console.error);
  }, []);

  const loadSessions = id => {
    apiGet(`/events/${id}/sessions`).then(ss => {
      setSessions(ss);
      setSelSession(ss.length ? ss[0] : null);
    }).catch(console.error);
  };

  /* Camera */
  useEffect(() => {
    if (mode !== "camera") { stopCam(); return; }
    startCam();
    return stopCam;
  }, [mode]);

  const startCam = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { width:1280, height:720 }, audio:false });
      if (videoRef.current) { videoRef.current.srcObject = stream; await videoRef.current.play(); setCamOk(true); }
    } catch { setCamOk(false); }
  };

  const stopCam = () => {
    videoRef.current?.srcObject?.getTracks().forEach(t => t.stop());
    setCamOk(false);
  };

  const clearOverlay = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    canvas.getContext("2d")?.clearRect(0, 0, canvas.width, canvas.height);
  }, []);

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
    const scale = Math.max(w / fw, h / fh);
    const ox = (w - fw * scale) / 2;
    const oy = (h - fh * scale) / 2;

    data.faces.forEach((f) => {
      if (!f.bbox) return;
      const [x1, y1, x2, y2] = f.bbox;
      const px = x1 * scale + ox;
      const py = y1 * scale + oy;
      const pw = (x2 - x1) * scale;
      const ph = (y2 - y1) * scale;
      const stroke = f.status === "known" ? COLOR.green500 : f.status === "uncertain" ? "#f59e0b" : COLOR.red500;
      const label = f.full_name || (f.status === "unknown" ? "Chưa xác định" : "Đang xác minh");
      const sim = f.similarity != null ? f.similarity.toFixed(2) : "";
      const text = `${label} ${sim}`.trim();
      const barH = 28;
      const padX = 8;

      ctx.strokeStyle = stroke;
      ctx.lineWidth = 3;
      ctx.strokeRect(px, py, pw, ph);
      ctx.font = "700 14px system-ui, sans-serif";
      const textW = Math.min(ctx.measureText(text).width + padX * 2, w - Math.max(4, px) - 4);
      const bx = Math.max(4, px);
      const by = Math.max(4, py - barH - 5);

      ctx.fillStyle = "rgba(15,23,42,0.82)";
      ctx.fillRect(bx, by, textW, barH);
      ctx.strokeStyle = stroke;
      ctx.lineWidth = 1;
      ctx.strokeRect(bx, by, textW, barH);
      ctx.fillStyle = COLOR.white;
      ctx.fillText(text, bx + padX, by + 19);
    });
  }, []);

  const updateRealtimeResult = useCallback((data) => {
    const faces = data?.faces || [];
    const known = faces.find((f) => f.status === "known");
    if (known) {
      const key = `${selSession?.id || ""}:${known.user_id || known.full_name || ""}`;
      if (lastSuccessRef.current !== key) {
        lastSuccessRef.current = key;
        if (known.attendance_logged) {
          setResult({
            ok: true,
            data: {
              name: known.full_name || "Sinh viên",
              code: known.student_code || "N/A",
              time: new Date().toLocaleTimeString("vi-VN"),
              sim: known.similarity ? known.similarity.toFixed(2) : "N/A",
            },
          });
        } else {
          const reasonMsg = known.skip_reason === "not_assigned"
            ? `Chưa được gán vào sự kiện (${known.full_name}).`
            : known.skip_reason === "dedupe_window"
            ? `Bạn vừa mới điểm danh xong (${known.full_name}).`
            : `Không thể điểm danh (${known.full_name}).`;
          setResult({ ok: false, msg: reasonMsg });
        }
      }
      return;
    }

    if (faces.length > 0 && Date.now() - lastFailureAtRef.current > 1500) {
      lastFailureAtRef.current = Date.now();
      setResult({ ok: false, msg: "Khuôn mặt chưa được đăng ký trong hệ thống." });
    }
  }, [selSession?.id]);

  const sendRealtimeFrame = useCallback((ws) => {
    const video = videoRef.current;
    if (!video || video.readyState < 2 || ws.readyState !== WebSocket.OPEN) return;
    const w = video.videoWidth;
    const h = video.videoHeight;
    if (!w || !h) return;
    const c = document.createElement("canvas");
    c.width = w;
    c.height = h;
    c.getContext("2d")?.drawImage(video, 0, 0, w, h);
    const b64 = c.toDataURL("image/jpeg", 0.55).split(",")[1];
    ws.send(JSON.stringify({ type: "frame", image: b64 }));
  }, []);

  /* Process attendance */
  const processAttendance = async blob => {
    if (!selEvent || !selSession) { setShowModal(true); return; }
    setLoading(true); setResult(null);
    try {
      const fd = new FormData();
      fd.append("file", blob, "capture.jpg");
      const mr = await apiPostForm("/faces/match-debug", fd);

      if (mr.message === "no_face") {
        setResult({ ok: false, msg: "Không tìm thấy khuôn mặt trong ảnh!" });
        setLoading(false); return;
      }
      const match = mr.match;
      if (!match || match.status !== "known") {
        setResult({ ok: false, msg: "Khuôn mặt chưa được đăng ký trong hệ thống!" });
        setLoading(false); return;
      }
      await apiPost("/attendance/check-in", {
        user_id: match.user_id, event_id: selEvent.id,
        session_id: selSession.id, similarity: match.similarity, source: mode,
      });
      const users = await apiGet("/users");
      const user  = users.find(u => u.id === match.user_id);
      setResult({
        ok: true,
        data: {
          name:  user?.full_name  ?? "Sinh viên",
          code:  user?.student_code ?? "N/A",
          time:  new Date().toLocaleTimeString("vi-VN"),
          sim:   match.similarity ? match.similarity.toFixed(2) : "N/A",
        },
      });
    } catch (e) {
      setResult({ ok: false, msg: `Lỗi: ${e.message}` });
    }
    setLoading(false);
  };

  const capture = useCallback(() => {
    if (!videoRef.current || !camOk || loading) return;
    const c = document.createElement("canvas");
    c.width  = videoRef.current.videoWidth;
    c.height = videoRef.current.videoHeight;
    c.getContext("2d").drawImage(videoRef.current, 0, 0);
    c.toBlob(blob => processAttendance(blob), "image/jpeg", 0.85);
  }, [camOk, loading, selEvent, selSession]);

  useEffect(() => {
    const h = e => { if (e.code === "Space" && mode === "camera" && !showModal && !loading) { e.preventDefault(); capture(); } };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [capture, mode, showModal, loading]);

  useEffect(() => {
    if (mode !== "camera" || !camOk || !selEvent?.id || !selSession?.id || showModal) {
      wsRef.current?.close();
      if (capRef.current) clearTimeout(capRef.current);
      clearOverlay();
      setLiveState(camOk ? "idle" : "off");
      return;
    }

    const params = new URLSearchParams({
      event_id: selEvent.id,
      session_id: selSession.id,
      auto_attendance: "true",
    });
    const ws = new WebSocket(wsUrl(`/api/ws/live?${params.toString()}`));
    wsRef.current = ws;
    let active = true;

    setLiveState("connecting");

    ws.onopen = () => {
      if (!active) return;
      setLiveState("running");
      sendRealtimeFrame(ws);
    };

    ws.onmessage = (ev) => {
      if (!active) return;
      const data = JSON.parse(ev.data);
      lastFrameRef.current = data;
      requestAnimationFrame(() => drawOverlay(data));
      updateRealtimeResult(data);

      capRef.current = setTimeout(() => {
        if (active && ws.readyState === WebSocket.OPEN) {
          sendRealtimeFrame(ws);
        }
      }, 120);
    };

    ws.onerror = () => {
      if (active) setLiveState("error");
    };

    ws.onclose = () => {
      if (capRef.current) clearTimeout(capRef.current);
      if (active) setLiveState("idle");
    };

    return () => {
      active = false;
      ws.close();
      if (capRef.current) clearTimeout(capRef.current);
    };
  }, [
    camOk,
    clearOverlay,
    drawOverlay,
    mode,
    selEvent?.id,
    selSession?.id,
    sendRealtimeFrame,
    showModal,
    updateRealtimeResult,
  ]);

  useEffect(() => {
    const onResize = () => {
      if (lastFrameRef.current) drawOverlay(lastFrameRef.current);
      else clearOverlay();
    };
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, [clearOverlay, drawOverlay]);

  /* ── Render ────────────────────────────────────────── */
  return (
    <div style={s.root}>
      {/* ── Header ── */}
      <header style={s.header}>
        <div style={s.logoRow}>
          <img src="/logo.png" alt="BAV" style={s.logoImg} onError={e => e.target.style.display="none"} />
          <div>
            <h1 style={s.headerTitle}>Học viện Ngân hàng</h1>
            <p style={s.headerSub}>Hệ thống điểm danh bằng khuôn mặt</p>
          </div>
        </div>
        <div style={s.clockBox}>
          <div style={s.clockTime}><Clock size={18} color="#93c5fd" />{fmtTime(time)}</div>
          <div style={s.clockDate}>{fmtDate(time)}</div>
        </div>
      </header>

      {/* ── Main ── */}
      <main style={s.main}>

        {/* Title */}
        <div style={s.titleBox}>
          <h2 style={s.titleH}>Điểm danh sự kiện bằng khuôn mặt</h2>
          <p style={s.titleSub}>Vui lòng nhìn thẳng vào camera để hệ thống xác thực</p>
        </div>

        {/* Event bar */}
        <div style={s.eventBar}>
          <div style={s.eventLeft}>
            <div style={s.eventIcon}><Calendar size={22} /></div>
            <div>
              <h3 style={s.eventName}>Sự kiện: {selEvent ? selEvent.name : "Chưa chọn sự kiện"}</h3>
              <div style={s.eventMeta}>
                <span style={s.eventMetaItem}><MapPin size={13}/>&nbsp;{selEvent?.location || "N/A"}</span>
                <span style={s.eventMetaItem}><Clock size={13}/>&nbsp;Phiên: {selSession?.name || "N/A"}</span>
              </div>
            </div>
          </div>
          <button style={s.btnOutline} onClick={() => setShowModal(true)}>
            <RotateCcw size={14}/> Đổi sự kiện
          </button>
        </div>

        {/* Grid */}
        <div style={s.grid}>

          {/* ── Left column ── */}
          <div style={s.leftCol}>
            {/* Video / Upload viewport */}
            <div style={s.videoWrap}>
              {mode === "camera" ? (
                <>
                  <video ref={videoRef} playsInline muted style={s.videoEl} />

                  {/* Status badge */}
                  <div style={s.cameraStatus}>
                    <span style={s.dot(camOk)} />
                    {camOk ? "Camera đang hoạt động" : "Camera đang tắt"}
                  </div>

                  {/* Brackets */}
                  <div style={s.bracketWrap}>
                    <div style={s.bracketInner}>
                      <div style={s.corner([0,null,null,0])} />
                      <div style={s.corner([0,0,null,null])} />
                      <div style={s.corner([null,null,0,0])} />
                      <div style={s.corner([null,0,0,null])} />
                    </div>
                  </div>
                </>
              ) : (
                <div style={s.uploadPlaceholder}>
                  <ImagePlus size={56} style={{ opacity: 0.4 }} />
                  <p style={{ marginTop: 12, fontSize: 15 }}>Chế độ tải ảnh lên</p>
                </div>
              )}

              {loading && (
                <div style={s.loadingOverlay}>
                  <Loader2 size={48} style={{ animation: "kiosk-spin 1s linear infinite", color: "#60a5fa" }} />
                  <p style={s.loadingText}>Đang xử lý khuôn mặt...</p>
                </div>
              )}
            </div>

            {/* Action */}
            <div style={s.actionRow}>
              {mode === "camera" ? (
                <button style={s.btnCapture(!camOk || loading)} onClick={capture} disabled={!camOk || loading}>
                  <Camera size={20}/> Chụp ảnh xác thực
                </button>
              ) : (
                <label style={{ ...s.btnCapture(loading), flex:1, cursor: loading ? "not-allowed":"pointer" }}>
                  <ImagePlus size={20}/> Chọn ảnh tải lên
                  <input type="file" accept="image/*" style={{ display:"none" }}
                    onChange={e => e.target.files[0] && processAttendance(e.target.files[0])}
                    disabled={loading} />
                </label>
              )}
            </div>

            {mode === "camera" && (
              <p style={s.hintText}>
                Hoặc nhấn phím <kbd style={{ backgroundColor:"#e5e7eb", padding:"1px 7px", borderRadius:4, fontFamily:"monospace" }}>Space</kbd> để chụp
              </p>
            )}
            <button style={s.switchLink}
              onClick={() => setMode(m => m === "camera" ? "upload" : "camera")}>
              Chuyển sang chế độ {mode === "camera" ? "Tải ảnh lên" : "Quét Camera"}
            </button>
          </div>

          {/* ── Right column ── */}
          <div style={s.rightCol}>

            {/* Guide card */}
            <div style={s.card}>
              <div style={s.cardHead}>Hướng dẫn</div>
              <div style={s.cardBody}>
                <ul style={s.guideList}>
                  {[
                    [Camera,       "Nhìn thẳng vào camera"],
                    [Info,         "Đảm bảo đủ ánh sáng"],
                    [User,         "Không đeo khẩu trang, kính râm"],
                    [CheckCircle2, "Giữ khuôn mặt trong khung hình"],
                    [XCircle,      "Không di chuyển khi chụp ảnh"],
                  ].map(([Icon, text], i) => (
                    <li key={i} style={s.guideItem}>
                      <Icon size={18} color={COLOR.blue600} style={{ flexShrink:0 }} /> {text}
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            {/* Result card */}
            <div style={s.resultCard}>
              <div style={s.cardHead}>Kết quả xác thực</div>
              <div style={s.resultBody}>
                {!result ? (
                  <div style={s.waitBox}>
                    <div style={s.spinner} />
                    <p style={{ margin:0, fontSize:13 }}>Đang chờ xác thực...</p>
                  </div>
                ) : result.ok ? (
                  <div>
                    <div style={s.resultBanner(true)}>
                      <div style={s.resultIconWrap(true)}><CheckCircle2 size={28}/></div>
                      <div>
                        <p style={s.resultTitle(true)}>Điểm danh thành công</p>
                        <p style={s.resultSub(true)}>Xin chào, <strong>{result.data.name}</strong></p>
                      </div>
                    </div>
                    {[
                      ["Mã sinh viên", result.data.code],
                      ["Thời gian",    result.data.time],
                      ["Sự kiện",      selEvent?.name],
                      ["Độ tương đồng",result.data.sim],
                    ].map(([label, val]) => (
                      <div key={label} style={s.detailRow}>
                        <span style={s.detailLabel}>{label}</span>
                        <span style={s.detailValue}>{val}</span>
                      </div>
                    ))}
                    <div style={s.thanksBox}>
                      <CheckCircle2 size={16} style={{ flexShrink:0, marginTop:1 }}/>
                      <div>
                        <p style={{ margin:0, fontWeight:600 }}>Cảm ơn bạn đã tham gia!</p>
                        <p style={{ margin:"2px 0 0", opacity:0.7 }}>Thông tin điểm danh đã ghi nhận.</p>
                      </div>
                    </div>
                    <button style={s.btnReset} onClick={() => setResult(null)}>
                      <RotateCcw size={14}/> Quay lại chờ xác thực
                    </button>
                  </div>
                ) : (
                  <div>
                    <div style={s.resultBanner(false)}>
                      <div style={s.resultIconWrap(false)}><XCircle size={28}/></div>
                      <div>
                        <p style={s.resultTitle(false)}>Thất bại</p>
                        <p style={s.resultSub(false)}>{result.msg}</p>
                      </div>
                    </div>
                    <button style={s.btnReset} onClick={() => setResult(null)}>
                      <RotateCcw size={14}/> Thử lại
                    </button>
                  </div>
                )}
              </div>
            </div>

          </div>
        </div>
      </main>

      {/* ── Footer ── */}
      <footer style={s.footer}>
        <Info size={14}/> Nếu gặp khó khăn, vui lòng liên hệ Ban tổ chức để được hỗ trợ.
        <span style={{ marginLeft:"auto" }}>
          <Link to="/admin" style={{ color:"#1d4ed8", fontWeight:600, fontSize:12, textDecoration:"none" }}>
            🔑 Quản trị viên
          </Link>
        </span>
      </footer>

      {/* ── Modal ── */}
      {showModal && (
        <div style={s.modalBackdrop}>
          <div style={s.modalBox}>
            <div style={s.modalHead}>
              <h3 style={s.modalTitle}>Cấu hình Hệ thống Điểm danh</h3>
              {events.length > 0 && (
                <button style={s.iconBtn} onClick={() => setShowModal(false)}>
                  <XCircle size={22}/>
                </button>
              )}
            </div>
            <div style={s.modalBody}>
              {events.length === 0 ? (
                <div style={{ textAlign: "center", padding: "10px 0" }}>
                  <p style={{ color: COLOR.gray500, marginBottom: 20, fontSize: 14, lineHeight: 1.5 }}>
                    Hệ thống chưa có sự kiện nào đang diễn ra, hoặc không thể kết nối tới máy chủ.
                  </p>
                  <Link 
                    to="/admin/events" 
                    style={{
                      display: "inline-block",
                      padding: "10px 20px",
                      borderRadius: 8,
                      backgroundColor: COLOR.navy,
                      color: COLOR.white,
                      fontWeight: 600,
                      textDecoration: "none",
                      fontSize: 14
                    }}
                  >
                    Vào trang Quản trị để thêm Sự kiện
                  </Link>
                </div>
              ) : (
                <>
                  <div>
                    <label style={s.modalLabel}>Chọn Sự kiện</label>
                    <select style={s.modalSelect}
                      value={selEvent?.id ?? ""}
                      onChange={e => { const ev=events.find(x=>x.id===e.target.value); setSelEvent(ev); if(ev) loadSessions(ev.id); }}>
                      <option value="" disabled>-- Vui lòng chọn --</option>
                      {events.map(ev => <option key={ev.id} value={ev.id}>{ev.name}</option>)}
                    </select>
                  </div>
                  <div>
                    <label style={s.modalLabel}>Chọn Phiên điểm danh</label>
                    <select style={s.modalSelect}
                      value={selSession?.id ?? ""}
                      disabled={!selEvent}
                      onChange={e => setSelSession(sessions.find(x=>x.id===e.target.value))}>
                      <option value="" disabled>-- Vui lòng chọn --</option>
                      {sessions.map(ss => <option key={ss.id} value={ss.id}>{ss.name}</option>)}
                    </select>
                  </div>
                  <button style={s.btnPrimary(!selEvent || !selSession)}
                    disabled={!selEvent || !selSession}
                    onClick={() => setShowModal(false)}>
                    Xác nhận &amp; Bắt đầu
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
