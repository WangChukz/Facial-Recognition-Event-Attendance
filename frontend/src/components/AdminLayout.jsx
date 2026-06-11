import { NavLink, Outlet, Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import {
  Users,
  Calendar,
  History,
  LogOut,
  Shield,
  UserCheck,
  ChevronRight,
  LayoutDashboard,
} from "lucide-react";

const C = {
  sidebar: "#1a2942",
  page: "#f6f8fc",
  panel: "#ffffff",
  border: "#dce3ee",
  text: "#ffffff",
  muted: "#8fa3b8",
  active: "#60a5fa",
  activeBg: "rgba(96,165,250,0.15)",
  activeSoft: "#eef4ff",
  dangerBg: "#fff1f2",
  dangerText: "#be123c",
};

const SIDEBAR_W = 240;

function SideLink({ to, icon: Icon, label }) {
  return (
    <NavLink to={to} style={{ textDecoration: "none" }}>
      {({ isActive }) => (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            padding: "10px 16px",
            borderRadius: 8,
            margin: "2px 8px",
            backgroundColor: isActive ? C.activeBg : "transparent",
            color: isActive ? C.active : C.muted,
            fontWeight: isActive ? 700 : 500,
            fontSize: 14,
            cursor: "pointer",
            borderLeft: isActive ? `3px solid ${C.active}` : "3px solid transparent",
            transition: "background 0.16s ease, color 0.16s ease, transform 0.16s ease",
          }}
        >
          <Icon size={17} style={{ flexShrink: 0, opacity: isActive ? 1 : 0.72 }} />
          <span style={{ minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {label}
          </span>
        </div>
      )}
    </NavLink>
  );
}

function SideSection({ label }) {
  return (
    <div
      style={{
        padding: "16px 24px 6px",
        fontSize: 10,
        fontWeight: 800,
        letterSpacing: "0.12em",
        textTransform: "uppercase",
        color: C.muted,
      }}
    >
      {label}
    </div>
  );
}

const PAGE_TITLES = {
  "/admin": "Dashboard",
  "/admin/users": "Sinh viên",
  "/admin/events": "Sự kiện",
  "/admin/register-face": "Đăng ký Khuôn mặt",
  "/admin/assignments": "Gán Sinh viên",
  "/admin/history": "Lịch sử Điểm danh",
};

export default function AdminLayout() {
  const { isAuthenticated, logout } = useAuth();
  const { pathname } = useLocation();

  if (!isAuthenticated) return <Navigate to="/login" replace />;

  const pageTitle = PAGE_TITLES[pathname] ?? "Admin Panel";

  return (
    <div
      style={{
        display: "flex",
        height: "100dvh",
        width: "100%",
        overflow: "hidden",
        fontFamily: "ui-sans-serif, system-ui, -apple-system, sans-serif",
        backgroundColor: C.page,
      }}
    >
      <aside
        style={{
          width: SIDEBAR_W,
          minWidth: SIDEBAR_W,
          backgroundColor: C.sidebar,
          display: "flex",
          flexDirection: "column",
          overflowY: "auto",
          overflowX: "hidden",
          borderRight: `1px solid rgba(255,255,255,0.1)`,
          boxShadow: "2px 0 12px rgba(0,0,0,0.15)",
          zIndex: 10,
        }}
      >
        <div
          style={{
            padding: "18px 20px",
            display: "flex",
            alignItems: "center",
            gap: 12,
            borderBottom: `1px solid rgba(255,255,255,0.08)`,
          }}
        >
          <img 
            src="/logo.png" 
            alt="BAV" 
            style={{
              height: 44,
              width: "auto",
              objectFit: "contain",
              borderRadius: 4,
              backgroundColor: "#ffffff",
              padding: 2
            }} 
          />
          <div style={{ minWidth: 0 }}>
            <div style={{ fontSize: 12, fontWeight: 800, color: C.text, lineHeight: 1.3 }}>
              HỌC VIỆN NGÂN HÀNG
            </div>
            <div style={{ fontSize: 10, color: C.muted, marginTop: 2, lineHeight: 1.3 }}>
              HỆ THỐNG ĐIỂM DANH BẰNG KHUÔN MẶT
            </div>
          </div>
        </div>

        <nav style={{ flex: 1, display: "block", padding: "12px 0 16px", borderBottom: "none", marginBottom: 0 }}>
          <SideSection label="QUẢN LÝ" />
          <SideLink to="/admin" icon={LayoutDashboard} label="Dashboard" />
          <SideLink to="/admin/users" icon={Users} label="Sinh viên" />
          <SideLink to="/admin/events" icon={Calendar} label="Sự kiện" />

          <SideSection label="ĐIỂM DANH" />
          <SideLink to="/admin/register-face" icon={UserCheck} label="Đăng ký khuôn mặt" />
          <SideLink to="/admin/assignments" icon={Shield} label="Gán sinh viên" />
          <SideLink to="/admin/history" icon={History} label="Lịch sử điểm danh" />
        </nav>

        <div
          style={{
            borderTop: `1px solid rgba(255,255,255,0.08)`,
            padding: "12px 16px",
          }}
        >
          <button
            onClick={logout}
            style={{
              width: "100%",
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "9px 12px",
              borderRadius: 8,
              border: "none",
              backgroundColor: "rgba(239, 68, 68, 0.15)",
              color: "#fca5a5",
              fontWeight: 700,
              fontSize: 13,
              cursor: "pointer",
              fontFamily: "inherit",
              transition: "background 0.15s",
            }}
          >
            <LogOut size={16} /> Đăng xuất
          </button>
        </div>
      </aside>

      <div
        style={{
          flex: 1,
          minWidth: 0,
          display: "flex",
          flexDirection: "column",
          backgroundColor: C.page,
          overflow: "hidden",
        }}
      >
        <header
          style={{
            height: 56,
            flexShrink: 0,
            backgroundColor: C.panel,
            borderBottom: `1px solid ${C.border}`,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 16,
            padding: "0 clamp(16px, 2vw, 28px)",
            boxShadow: "0 1px 4px rgba(38,57,89,0.05)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 8, minWidth: 0 }}>
            <span style={{ fontSize: 12, color: "#8490a3" }}>Admin</span>
            <ChevronRight size={14} color="#8490a3" />
            <span
              style={{
                fontSize: 14,
                fontWeight: 700,
                color: "#1f2937",
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {pageTitle}
            </span>
          </div>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              backgroundColor: "#eef4ff",
              border: `1px solid #d5e2ff`,
              borderRadius: 999,
              padding: "5px 14px",
              flexShrink: 0,
            }}
          >
            <Shield size={15} color="#2257c2" />
            <span style={{ fontSize: 13, fontWeight: 700, color: "#2257c2" }}>Admin</span>
          </div>
        </header>

        <div
          className="admin-content"
          style={{
            flex: 1,
            overflowY: "auto",
            overflowX: "hidden",
            padding: "clamp(16px, 2.2vw, 28px)",
          }}
        >
          <Outlet />
        </div>
      </div>
    </div>
  );
}
