import { useEffect, useState } from "react";
import { apiGet, apiPostForm } from "../api.js";
import { useToast } from "../context/ToastContext.jsx";
import { Loader2, Search, UploadCloud, ArrowLeft, HelpCircle } from "lucide-react";

export default function RegisterFace() {
  const [users, setUsers] = useState([]);
  const [userId, setUserId] = useState("");
  const [file, setFile] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  
  // Search query inputs
  const [searchName, setSearchName] = useState("");
  const [searchStudentCode, setSearchStudentCode] = useState("");
  const [filteredUsers, setFilteredUsers] = useState([]);

  // Registration options
  const [userSearchQuery, setUserSearchQuery] = useState("");
  const [userDropdownOpen, setUserDropdownOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);
  const [userRole, setUserRole] = useState("student");
  const [studentCode, setStudentCode] = useState("");
  const [isActive, setIsActive] = useState(true);

  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);
  const { addToast } = useToast();

  useEffect(() => {
    apiGet("/users")
      .then((u) => {
        setUsers(u);
        setFilteredUsers(u);
        if (u[0]) {
          setUserId(u[0].id);
          setSelectedUser(u[0]);
          setStudentCode(u[0].student_code || "");
          setUserRole(u[0].role || "student");
        }
      })
      .catch((e) => setErr(String(e.message)));
  }, []);

  // Handle Search Query filtering
  const handleSearch = () => {
    let result = users;
    if (searchName) {
      result = result.filter(u => u.full_name.toLowerCase().includes(searchName.toLowerCase()));
    }
    if (searchStudentCode) {
      result = result.filter(u => u.student_code && u.student_code.toLowerCase().includes(searchStudentCode.toLowerCase()));
    }
    setFilteredUsers(result);
    if (result.length > 0) {
      handleSelectUser(result[0]);
    } else {
      setSelectedUser(null);
      setUserId("");
    }
  };

  const handleSelectUser = (u) => {
    setSelectedUser(u);
    setUserId(u.id);
    setStudentCode(u.student_code || "");
    setUserRole(u.role || "student");
    setUserSearchQuery(`${u.full_name} (${u.email})`);
    setUserDropdownOpen(false);
  };

  // Drag & Drop event handlers
  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  const submit = async (e) => {
    e.preventDefault();
    if (!file || !userId) {
      addToast("Vui lòng chọn đầy đủ thông tin người dùng và ảnh", "error");
      return;
    }
    setErr("");
    setLoading(true);
    const fd = new FormData();
    fd.append("user_id", userId);
    fd.append("file", file);
    try {
      const res = await apiPostForm("/faces/register", fd);
      addToast(`Đã đăng ký khuôn mặt thành công: det_score=${res.det_score.toFixed(3)}`, "success");
      setFile(null);
    } catch (e) {
      setErr(e.message);
      addToast("Có lỗi xảy ra khi tạo embedding: " + e.message, "error");
    } finally {
      setLoading(false);
    }
  };

  // Dropdown list matching search
  const dropdownFilteredUsers = userSearchQuery
    ? users.filter(u => 
        u.full_name.toLowerCase().includes(userSearchQuery.toLowerCase()) || 
        u.email.toLowerCase().includes(userSearchQuery.toLowerCase()) ||
        (u.student_code && u.student_code.toLowerCase().includes(userSearchQuery.toLowerCase()))
      )
    : users;

  return (
    <div style={{ fontFamily: "ui-sans-serif, system-ui, -apple-system, sans-serif", color: "#1f2937" }}>
      {/* Navigation Breadcrumb */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px", fontSize: "13px", color: "#6b7280" }}>
        <div>
          <span>Admin</span> &gt; <span style={{ fontWeight: 600, color: "#1f2937" }}>Đăng ký Khuôn mặt</span>
        </div>
        <button style={{ background: "none", border: "none", color: "#2563eb", cursor: "pointer", display: "flex", alignItems: "center", gap: 4 }}>
          <HelpCircle size={16} />
        </button>
      </div>

      <h1 style={{ fontSize: "24px", fontWeight: 700, color: "#1e3266", marginBottom: "20px" }}>
        Đăng ký khuôn mặt
      </h1>

      {/* Top Filter Bar */}
      <div style={{
        backgroundColor: "#ffffff",
        border: "1px solid #dce3ee",
        borderRadius: "12px",
        padding: "16px 20px",
        display: "grid",
        gridTemplateColumns: "1fr 1fr auto",
        gap: "16px",
        alignItems: "end",
        boxShadow: "0 2px 8px rgba(38,57,89,0.02)",
        marginBottom: "20px"
      }}>
        <div>
          <label style={{ fontSize: "12px", fontWeight: 700, color: "#4b5563", display: "block", marginBottom: 6 }}>Họ và tên</label>
          <input 
            type="text" 
            placeholder="Nhập họ và tên" 
            value={searchName}
            onChange={(e) => setSearchName(e.target.value)}
            style={{ width: "100%", padding: "8px 12px", borderRadius: "8px", border: "1px solid #d1d5db" }}
          />
        </div>
        <div>
          <label style={{ fontSize: "12px", fontWeight: 700, color: "#4b5563", display: "block", marginBottom: 6 }}>Mã sinh viên</label>
          <input 
            type="text" 
            placeholder="Nhập mã sinh viên" 
            value={searchStudentCode}
            onChange={(e) => setSearchStudentCode(e.target.value)}
            style={{ width: "100%", padding: "8px 12px", borderRadius: "8px", border: "1px solid #d1d5db" }}
          />
        </div>
        <button 
          onClick={handleSearch}
          style={{
            padding: "9px 20px",
            backgroundColor: "#ffffff",
            color: "#2563eb",
            border: "1.5px solid #2563eb",
            borderRadius: "8px",
            fontWeight: 600,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: 6
          }}
        >
          <Search size={15} /> Tìm kiếm
        </button>
      </div>

      {/* Main Form Area */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "1.2fr 1.2fr 1.6fr",
        gap: "20px",
        backgroundColor: "#ffffff",
        border: "1px solid #dce3ee",
        borderRadius: "12px",
        padding: "24px 20px",
        boxShadow: "0 4px 12px rgba(38,57,89,0.03)",
        position: "relative",
        marginBottom: "24px"
      }}>
        
        {/* Left Column: User details search & select */}
        <div style={{ borderRight: "1px solid #e5e7eb", paddingRight: "20px" }}>
          <h3 style={{ margin: "0 0 16px", fontSize: "14px", fontWeight: 700, color: "#1e3266" }}>
            Thông tin người dùng
          </h3>
          
          <div style={{ display: "flex", flexDirection: "column", gap: "14px", position: "relative" }}>
            <div>
              <label style={{ fontSize: "12px", fontWeight: 700, color: "#4b5563", display: "block", marginBottom: 6 }}>
                Người dùng <span style={{ color: "#ef4444" }}>*</span>
              </label>
              <div style={{ display: "flex", position: "relative" }}>
                <input 
                  type="text"
                  placeholder="Nhập hoặc chọn người dùng"
                  value={userSearchQuery}
                  onChange={(e) => {
                    setUserSearchQuery(e.target.value);
                    setUserDropdownOpen(true);
                  }}
                  onFocus={() => setUserDropdownOpen(true)}
                  style={{ width: "100%", padding: "8px 12px", borderRadius: "8px", border: "1px solid #d1d5db", paddingRight: "36px" }}
                />
                <Search size={16} style={{ position: "absolute", right: 12, top: 11, color: "#9ca3af" }} />
              </div>
              
              {/* Dropdown list for matching search */}
              {userDropdownOpen && (
                <div style={{
                  position: "absolute",
                  top: "64px",
                  left: 0,
                  right: 0,
                  backgroundColor: "#ffffff",
                  border: "1px solid #d1d5db",
                  borderRadius: "8px",
                  maxHeight: "200px",
                  overflowY: "auto",
                  zIndex: 20,
                  boxShadow: "0 4px 12px rgba(0,0,0,0.1)"
                }}>
                  {dropdownFilteredUsers.length === 0 ? (
                    <div style={{ padding: "8px 12px", fontSize: "13px", color: "#9ca3af" }}>Không tìm thấy người dùng</div>
                  ) : (
                    dropdownFilteredUsers.map((u) => (
                      <div 
                        key={u.id}
                        onClick={() => handleSelectUser(u)}
                        style={{
                          padding: "8px 12px",
                          fontSize: "13px",
                          cursor: "pointer",
                          borderBottom: "1px solid #f3f4f6",
                          backgroundColor: selectedUser?.id === u.id ? "#eff6ff" : "transparent"
                        }}
                        onMouseEnter={(e) => e.target.style.backgroundColor = "#f3f4f6"}
                        onMouseLeave={(e) => e.target.style.backgroundColor = selectedUser?.id === u.id ? "#eff6ff" : "transparent"}
                      >
                        <div style={{ fontWeight: 600 }}>{u.full_name}</div>
                        <div style={{ fontSize: "11px", color: "#6b7280" }}>{u.email}</div>
                      </div>
                    ))
                  )}
                </div>
              )}
              <p style={{ fontSize: "11px", color: "#9ca3af", marginTop: 4, marginBlockEnd: 0 }}>
                Nhập để tìm theo họ tên, email hoặc chọn từ danh sách.
              </p>
            </div>

            <div>
              <label style={{ fontSize: "12px", fontWeight: 700, color: "#4b5563", display: "block", marginBottom: 6 }}>Vai trò</label>
              <input 
                type="text" 
                value={userRole === "student" ? "Sinh viên" : userRole === "admin" ? "Quản trị viên" : "Staff"} 
                disabled 
                style={{ width: "100%", padding: "8px 12px", borderRadius: "8px", border: "1px solid #e5e7eb", backgroundColor: "#f9fafb", color: "#6b7280" }}
              />
            </div>

            {/* Note badge */}
            <div style={{
              backgroundColor: "#eff6ff",
              border: "1px solid #dbeafe",
              borderRadius: "8px",
              padding: "12px 14px",
              fontSize: "12px",
              color: "#1e40af",
              lineHeight: 1.5,
              marginTop: 10
            }}>
              <span style={{ fontWeight: 600 }}>ℹ️</span> Sau khi tạo embedding, hệ thống sẽ sử dụng FAISS để lưu và tìm kiếm khuôn mặt nhanh chóng, chính xác.
            </div>
          </div>
        </div>

        {/* Middle Column: Class and Role configuration */}
        <div style={{ borderRight: "1px solid #e5e7eb", paddingRight: "20px" }}>
          <h3 style={{ margin: "0 0 16px", fontSize: "14px", fontWeight: 700, color: "#1e3266" }}>
            Lớp và vai trò
          </h3>
          
          <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
            <div>
              <label style={{ fontSize: "12px", fontWeight: 700, color: "#4b5563", display: "block", marginBottom: 6 }}>
                Lớp <span style={{ color: "#ef4444" }}>*</span>
              </label>
              <input 
                type="text" 
                value={selectedUser?.class_name || "—"} 
                disabled 
                style={{ width: "100%", padding: "8px 12px", borderRadius: "8px", border: "1px solid #e5e7eb", backgroundColor: "#f9fafb", color: "#6b7280" }}
              />
            </div>

            <div>
              <label style={{ fontSize: "12px", fontWeight: 700, color: "#4b5563", display: "block", marginBottom: 6 }}>
                Vai trò <span style={{ color: "#ef4444" }}>*</span>
              </label>
              <input 
                type="text" 
                value={userRole === "student" ? "Sinh viên" : userRole === "admin" ? "Quản trị viên" : userRole === "staff" ? "Nhân viên/Cán bộ" : "Staff"} 
                disabled 
                style={{ width: "100%", padding: "8px 12px", borderRadius: "8px", border: "1px solid #e5e7eb", backgroundColor: "#f9fafb", color: "#6b7280" }}
              />
            </div>

            <div>
              <label style={{ fontSize: "12px", fontWeight: 700, color: "#4b5563", display: "block", marginBottom: 6 }}>Mã sinh viên</label>
              <input 
                type="text" 
                value={studentCode || "—"} 
                disabled 
                style={{ width: "100%", padding: "8px 12px", borderRadius: "8px", border: "1px solid #e5e7eb", backgroundColor: "#f9fafb", color: "#6b7280" }}
              />
            </div>

            <div>
              <label style={{ fontSize: "12px", fontWeight: 700, color: "#4b5563", display: "block", marginBottom: 6 }}>Trạng thái</label>
              <div style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
                backgroundColor: "#ecfdf5",
                border: "1px solid #a7f3d0",
                color: "#047857",
                padding: "4px 12px",
                borderRadius: "999px",
                fontSize: "12px",
                fontWeight: 600
              }}>
                <span style={{ width: 6, height: 6, borderRadius: "50%", backgroundColor: "#10b981" }}></span>
                Đang hoạt động
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: File/Image Drag and Drop */}
        <div style={{ paddingLeft: "10px" }}>
          <h3 style={{ margin: "0 0 16px", fontSize: "14px", fontWeight: 700, color: "#1e3266" }}>
            Ảnh khuôn mặt
          </h3>
          
          <div 
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            onClick={() => document.getElementById("file-upload").click()}
            style={{
              border: dragActive ? "2px dashed #2563eb" : "2px dashed #d1d5db",
              borderRadius: "12px",
              padding: "36px 20px",
              textAlign: "center",
              backgroundColor: dragActive ? "#eff6ff" : "#ffffff",
              cursor: "pointer",
              transition: "all 0.2s ease",
              height: "240px",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              gap: 12
            }}
          >
            <input 
              type="file" 
              id="file-upload" 
              accept="image/*" 
              onChange={(e) => {
                const selectedFile = e.target.files?.[0];
                if (selectedFile) {
                  setFile(selectedFile);
                }
              }}
              style={{ display: "none" }}
            />
            
            <div 
              style={{ 
                display: "flex", 
                flexDirection: "column", 
                alignItems: "center", 
                gap: 10,
                width: "100%",
                height: "100%",
                justifyContent: "center"
              }}
            >
              {file ? (
                <>
                  <img 
                    src={URL.createObjectURL(file)} 
                    alt="Preview" 
                    style={{ 
                      maxHeight: "120px", 
                      maxWidth: "100%", 
                      objectFit: "contain", 
                      borderRadius: "6px",
                      border: "1px solid #d1d5db",
                      boxShadow: "0 2px 4px rgba(0,0,0,0.05)"
                    }} 
                  />
                  <div style={{ fontSize: "13px", fontWeight: 600, color: "#10b981" }}>
                    ✓ Đã chọn: {file.name}
                  </div>
                  <div style={{ fontSize: "11px", color: "#9ca3af" }}>
                    (Nhấp để đổi ảnh khác)
                  </div>
                </>
              ) : (
                <>
                  <UploadCloud size={48} color="#2563eb" />
                  <div style={{ fontSize: "14px", fontWeight: 600, color: "#4b5563" }}>
                    Kéo thả ảnh vào đây hoặc
                  </div>
                  <span style={{
                    padding: "8px 18px",
                    backgroundColor: "#2563eb",
                    color: "#ffffff",
                    borderRadius: "8px",
                    fontWeight: 600,
                    fontSize: "13px"
                  }}>
                    Chọn ảnh từ máy
                  </span>
                </>
              )}
            </div>
            {!file && (
              <p style={{ fontSize: "11px", color: "#9ca3af", margin: 0 }}>
                Định dạng: JPG, PNG, JPEG - Tối đa 5MB
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Bottom Buttons Action Row */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <button 
          onClick={() => window.history.back()}
          style={{
            padding: "10px 20px",
            border: "1px solid #d1d5db",
            borderRadius: "8px",
            backgroundColor: "#ffffff",
            fontWeight: 600,
            fontSize: "14px",
            display: "flex",
            alignItems: "center",
            gap: 6,
            cursor: "pointer"
          }}
        >
          <ArrowLeft size={16} /> Quay lại
        </button>

        <button 
          onClick={submit}
          disabled={!file || loading || !userId}
          style={{
            padding: "10px 24px",
            border: "none",
            borderRadius: "8px",
            backgroundColor: (!file || !userId) ? "#93c5fd" : "#2563eb",
            color: "#ffffff",
            fontWeight: 600,
            fontSize: "14px",
            display: "flex",
            alignItems: "center",
            gap: 8,
            cursor: (!file || !userId) ? "not-allowed" : "pointer"
          }}
        >
          {loading && <Loader2 size={16} className="animate-spin" style={{ animation: "kiosk-spin 1s linear infinite" }} />}
          Tạo embedding + FAISS
        </button>
      </div>

      {err && (
        <div style={{ marginTop: "16px", padding: "12px", backgroundColor: "#fef2f2", border: "1px solid #fecaca", borderRadius: "8px", color: "#dc2626", fontSize: "13px" }}>
          ⚠️ Lỗi: {err}
        </div>
      )}
    </div>
  );
}
