import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { toast } from "sonner"

interface UserData {
  role: string,
  email: string
}

export function useAuth() {
  const navigate = useNavigate();
  const [dashboard, setDashboard] = useState("");
  const [userData, setUserData] = useState<UserData>({ role: "", email: "" });

  useEffect(() => {
    const token = localStorage.getItem("token");
    const rememberMe = localStorage.getItem("rememberMe");
    if (!token) {
      if (rememberMe === "true") {
        alert("Your session has expired. Please login again.");
        localStorage.removeItem("rememberMe");
        localStorage.removeItem("rememberedEmail");
      }
      navigate("/");
      return;
    }

    fetch("http://127.0.0.1:5000/auth/dashboard", {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(async (res) => {
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
          if (res.status === 401 || res.status === 422) {
            localStorage.removeItem("token");
            if (localStorage.getItem("rememberMe") === "true") {
              toast.error("Your session has expired. Please login again.");
            }
            navigate("/");
            return;
          }
          throw new Error(data.error || "Unauthorized");
        }
        return data;
      })
      .then((data) => {
        if (!data) return;

        const roleLower = (data.role || "").toLowerCase();
        setUserData(data);

        if (roleLower === "staff") setDashboard("This is the Staff Dashboard");
        else if (roleLower === "hr") setDashboard("This is the HR Dashboard");
        else if (roleLower === "manager") setDashboard("This is the Manager Dashboard");
        else if (roleLower === "director") setDashboard("This is the Director Dashboard");
        else setDashboard("Unauthorized access");
      })
      .catch((err) => {
        console.error("Dashboard error:", err);
        setDashboard(err.message);
      });
  }, [navigate]);

  const handleLogout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("rememberMe");
    localStorage.removeItem("rememberedEmail");
    toast.success("Logged out successfully!");
    navigate("/");
  };

  return { userData, handleLogout }
}