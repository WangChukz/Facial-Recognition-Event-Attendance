import { Route, Routes, Navigate, useLocation } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext.jsx";
import { ToastProvider } from "./context/ToastContext.jsx";
import AdminLayout from "./components/AdminLayout.jsx";
import Login from "./pages/Login.jsx";
import ClientSimulation from "./pages/ClientSimulation.jsx";

import Users from "./pages/Users.jsx";
import Events from "./pages/Events.jsx";
import RegisterFace from "./pages/RegisterFace.jsx";
import History from "./pages/History.jsx";

export default function App() {
  const { pathname } = useLocation();
  const isAdminRoute = pathname.startsWith("/admin");

  return (
    <ToastProvider>
      <AuthProvider>
        <div className={isAdminRoute ? "app-shell app-shell--admin" : "layout"} style={{ display: "block" }}>
          <Routes>
          {/* Public Routes */}
          <Route path="/" element={<ClientSimulation />} />
          <Route path="/login" element={<Login />} />

          {/* Protected Admin Routes */}
          <Route path="/admin" element={<AdminLayout />}>
            <Route index element={<Navigate to="users" replace />} />
            <Route path="users" element={<Users />} />
            <Route path="events" element={<Events />} />
            <Route path="register-face" element={<RegisterFace />} />
            <Route path="history" element={<History />} />
          </Route>
        </Routes>
      </div>
    </AuthProvider>
    </ToastProvider>
  );
}
