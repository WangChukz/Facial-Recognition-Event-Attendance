import { NavLink, Route, Routes } from "react-router-dom";
import Home from "./pages/Home.jsx";
import Users from "./pages/Users.jsx";
import Events from "./pages/Events.jsx";
import RegisterFace from "./pages/RegisterFace.jsx";
import Live from "./pages/Live.jsx";
import History from "./pages/History.jsx";

const link = ({ isActive }) => (isActive ? "active" : "");

export default function App() {
  return (
    <div className="layout">
      <nav>
        <NavLink to="/" className={link} end>
          Trang chủ
        </NavLink>
        <NavLink to="/users" className={link}>
          Người dùng
        </NavLink>
        <NavLink to="/events" className={link}>
          Sự kiện
        </NavLink>
        <NavLink to="/register-face" className={link}>
          Đăng ký khuôn mặt
        </NavLink>
        <NavLink to="/live" className={link}>
          Webcam realtime
        </NavLink>
        <NavLink to="/history" className={link}>
          Lịch sử điểm danh
        </NavLink>
      </nav>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/users" element={<Users />} />
        <Route path="/events" element={<Events />} />
        <Route path="/register-face" element={<RegisterFace />} />
        <Route path="/live" element={<Live />} />
        <Route path="/history" element={<History />} />
      </Routes>
    </div>
  );
}
