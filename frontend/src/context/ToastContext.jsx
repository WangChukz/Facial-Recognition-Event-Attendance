import { createContext, useContext, useState, useCallback } from "react";
import { CheckCircle2, XCircle, X } from "lucide-react";

const ToastContext = createContext();

export const useToast = () => useContext(ToastContext);

export const ToastProvider = ({ children }) => {
  const [toasts, setToasts] = useState([]);

  const addToast = useCallback((message, type = "success") => {
    const id = Date.now();
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 3000);
  }, []);

  const removeToast = (id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  return (
    <ToastContext.Provider value={{ addToast }}>
      {children}
      <div style={{
        position: "fixed", top: 24, right: 24, zIndex: 9999, display: "flex", flexDirection: "column", gap: 10
      }}>
        {toasts.map((t) => (
          <div key={t.id} className="animate-in" style={{
            display: "flex", alignItems: "center", gap: 12, padding: "12px 16px", borderRadius: 8,
            backgroundColor: t.type === "success" ? "#f0fdf4" : "#fef2f2",
            border: `1px solid ${t.type === "success" ? "#bbf7d0" : "#fecaca"}`,
            boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
            minWidth: 280,
          }}>
            {t.type === "success" ? <CheckCircle2 size={20} color="#16a34a" /> : <XCircle size={20} color="#dc2626" />}
            <span style={{ fontSize: 14, fontWeight: 600, color: t.type === "success" ? "#15803d" : "#b91c1c", flex: 1 }}>{t.message}</span>
            <button onClick={() => removeToast(t.id)} style={{ background: "none", border: "none", cursor: "pointer", color: "#9ca3af", padding: 0 }}>
              <X size={16} />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
};
