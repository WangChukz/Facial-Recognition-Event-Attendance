import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import { Shield, Eye, EyeOff, Lock, User, ArrowRight } from "lucide-react";

/* ── Color palette (same as client) ── */
const C = {
  navy:    "#1e3266",
  navyDk:  "#152550",
  navyLt:  "#243b7a",
  blue50:  "#eff6ff",
  blue100: "#dbeafe",
  blue600: "#2563eb",
  white:   "#ffffff",
  gray50:  "#f9fafb",
  gray100: "#f3f4f6",
  gray200: "#e5e7eb",
  gray300: "#d1d5db",
  gray400: "#9ca3af",
  gray500: "#6b7280",
  gray600: "#4b5563",
  gray700: "#374151",
  gray800: "#1f2937",
  red50:   "#fef2f2",
  red200:  "#fecaca",
  red700:  "#b91c1c",
};

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPwd,  setShowPwd]  = useState(false);
  const [err,      setErr]      = useState("");
  const [loading,  setLoading]  = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErr("");
    setLoading(true);
    await new Promise(r => setTimeout(r, 400)); // small UX delay
    if (login(username, password)) {
      navigate("/admin/users");
    } else {
      setErr("Sai tài khoản hoặc mật khẩu!");
    }
    setLoading(false);
  };

  return (
    <div style={{
      position: "fixed", inset: 0,
      fontFamily: "ui-sans-serif, system-ui, -apple-system, sans-serif",
      display: "flex",
    }}>

      {/* ── Left panel (branding) ── */}
      <div style={{
        width: "42%", minWidth: 340,
        backgroundColor: C.navy,
        display: "flex", flexDirection: "column",
        alignItems: "center", justifyContent: "center",
        padding: "40px 48px",
        position: "relative", overflow: "hidden",
      }}>
        {/* Decorative circles */}
        <div style={{ position:"absolute", top:-80, right:-80, width:280, height:280, borderRadius:"50%", backgroundColor:"rgba(255,255,255,0.04)" }} />
        <div style={{ position:"absolute", bottom:-60, left:-60, width:220, height:220, borderRadius:"50%", backgroundColor:"rgba(255,255,255,0.04)" }} />

        {/* Logo + name */}
        <img src="/logo.png" alt="BAV"
          style={{ height: 100, objectFit:"contain", marginBottom: 28, filter:"drop-shadow(0 4px 16px rgba(0,0,0,0.3))" }}
          onError={e => e.target.style.display="none"} />

        <h1 style={{
          color: C.white, margin: "0 0 10px", textAlign: "center",
          fontSize: 26, fontWeight: 800, lineHeight: 1.3, letterSpacing: 0.5,
        }}>
          HỌC VIỆN NGÂN HÀNG
        </h1>
        <p style={{ color: "rgba(255,255,255,0.6)", textAlign: "center", fontSize: 14, margin: "0 0 40px", lineHeight: 1.6 }}>
          Hệ thống Quản lý Điểm danh<br />bằng Nhận diện Khuôn mặt
        </p>

        {/* Feature badges */}
        {[
          { icon: "🎯", label: "Nhận diện khuôn mặt AI" },
          { icon: "📊", label: "Thống kê điểm danh realtime" },
          { icon: "🔒", label: "Bảo mật dữ liệu sinh viên" },
        ].map(({ icon, label }) => (
          <div key={label} style={{
            display: "flex", alignItems: "center", gap: 12,
            backgroundColor: "rgba(255,255,255,0.08)",
            borderRadius: 10, padding: "10px 18px",
            width: "100%", marginBottom: 10,
          }}>
            <span style={{ fontSize: 20 }}>{icon}</span>
            <span style={{ color: C.white, fontSize: 13, fontWeight: 500 }}>{label}</span>
          </div>
        ))}

        {/* Back to kiosk */}
        <Link to="/" style={{
          marginTop: 32, display: "flex", alignItems: "center", gap: 6,
          color: "rgba(255,255,255,0.5)", fontSize: 12, textDecoration: "none",
        }}>
          ← Quay lại trang điểm danh
        </Link>
      </div>

      {/* ── Right panel (form) ── */}
      <div style={{
        flex: 1, backgroundColor: C.gray50,
        display: "flex", alignItems: "center", justifyContent: "center",
        padding: "40px",
      }}>
        <div style={{
          width: "100%", maxWidth: 400,
          backgroundColor: C.white,
          borderRadius: 20, padding: "40px 36px",
          boxShadow: "0 8px 40px rgba(0,0,0,0.1)",
          border: `1px solid ${C.gray100}`,
        }}>

          {/* Header */}
          <div style={{ marginBottom: 32, textAlign: "center" }}>
            <div style={{
              display: "inline-flex", alignItems: "center", justifyContent: "center",
              width: 56, height: 56, backgroundColor: C.blue50, borderRadius: 14,
              marginBottom: 16,
            }}>
              <Shield size={28} color={C.blue600} />
            </div>
            <h2 style={{ margin: "0 0 6px", fontSize: 22, fontWeight: 800, color: C.gray800 }}>
              Đăng nhập Admin
            </h2>
            <p style={{ margin: 0, fontSize: 13, color: C.gray500 }}>
              Nhập thông tin để truy cập hệ thống quản lý
            </p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 16 }}>

            {/* Username */}
            <div>
              <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: C.gray700, marginBottom: 6 }}>
                Tài khoản
              </label>
              <div style={{ position: "relative" }}>
                <User size={16} color={C.gray400}
                  style={{ position:"absolute", left:12, top:"50%", transform:"translateY(-50%)", pointerEvents:"none" }} />
                <input
                  type="text"
                  value={username}
                  onChange={e => setUsername(e.target.value)}
                  placeholder="Nhập tên tài khoản"
                  required
                  style={{
                    width: "100%", padding: "11px 12px 11px 38px",
                    border: `1.5px solid ${C.gray200}`, borderRadius: 10,
                    fontSize: 14, color: C.gray800, fontFamily: "inherit",
                    backgroundColor: C.white, boxSizing: "border-box",
                    outline: "none", transition: "border-color 0.2s",
                  }}
                  onFocus={e => e.target.style.borderColor = C.blue600}
                  onBlur={e  => e.target.style.borderColor = C.gray200}
                />
              </div>
            </div>

            {/* Password */}
            <div>
              <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: C.gray700, marginBottom: 6 }}>
                Mật khẩu
              </label>
              <div style={{ position: "relative" }}>
                <Lock size={16} color={C.gray400}
                  style={{ position:"absolute", left:12, top:"50%", transform:"translateY(-50%)", pointerEvents:"none" }} />
                <input
                  type={showPwd ? "text" : "password"}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="Nhập mật khẩu"
                  required
                  style={{
                    width: "100%", padding: "11px 42px 11px 38px",
                    border: `1.5px solid ${C.gray200}`, borderRadius: 10,
                    fontSize: 14, color: C.gray800, fontFamily: "inherit",
                    backgroundColor: C.white, boxSizing: "border-box",
                    outline: "none", transition: "border-color 0.2s",
                  }}
                  onFocus={e => e.target.style.borderColor = C.blue600}
                  onBlur={e  => e.target.style.borderColor = C.gray200}
                />
                <button type="button" onClick={() => setShowPwd(v => !v)}
                  style={{
                    position: "absolute", right: 12, top: "50%", transform: "translateY(-50%)",
                    background: "none", border: "none", cursor: "pointer", color: C.gray400, display:"flex",
                  }}>
                  {showPwd ? <EyeOff size={16}/> : <Eye size={16}/>}
                </button>
              </div>
            </div>

            {/* Error */}
            {err && (
              <div style={{
                backgroundColor: C.red50, border: `1px solid ${C.red200}`,
                borderRadius: 8, padding: "10px 14px",
                color: C.red700, fontSize: 13, fontWeight: 500,
              }}>
                ⚠️ {err}
              </div>
            )}

            {/* Submit */}
            <button type="submit" disabled={loading}
              style={{
                display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
                width: "100%", padding: "13px 0", borderRadius: 10, border: "none",
                backgroundColor: loading ? C.gray300 : C.navy, color: C.white,
                fontWeight: 700, fontSize: 15, cursor: loading ? "not-allowed" : "pointer",
                fontFamily: "inherit", letterSpacing: 0.3, marginTop: 4,
                boxShadow: loading ? "none" : "0 4px 14px rgba(30,50,102,0.35)",
                transition: "all 0.2s",
              }}>
              {loading ? "Đang đăng nhập..." : <><span>Đăng nhập</span><ArrowRight size={17}/></>}
            </button>
          </form>

          {/* Hint */}
          <div style={{
            marginTop: 24, padding: "12px 16px",
            backgroundColor: C.blue50, borderRadius: 10, border: `1px solid ${C.blue100}`,
            fontSize: 12, color: C.gray600, lineHeight: 1.6,
          }}>
            <strong style={{ color: C.gray800 }}>Tài khoản demo:</strong><br />
            Tài khoản: <code style={{ backgroundColor: C.gray100, padding:"1px 5px", borderRadius:4 }}>admin</code>&nbsp;
            Mật khẩu: <code style={{ backgroundColor: C.gray100, padding:"1px 5px", borderRadius:4 }}>123456</code>
          </div>
        </div>
      </div>
    </div>
  );
}
