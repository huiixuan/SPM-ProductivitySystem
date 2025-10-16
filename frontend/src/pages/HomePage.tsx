import { useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import TaskCreation from "@/components/TaskManagement/TaskCreation";
import TaskDashboard from "@/pages/TaskDashboard";
import NewProjectButton from "@/components/Project/NewProjectButton";
import ProjectList from "@/components/Project/ProjectList";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";

interface UserData {
    role: string,
    email: string
}

export default function HomePage() {
    const [dashboard, setDashboard] = useState("");
    const [userData, setUserData] = useState<UserData>({ role: "", email: "" });
    const [refreshKey, setRefreshKey] = useState(0);
    const navigate = useNavigate();

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

    const canCreateProject = userData.role === "manager" || userData.role === "director";

    return (
        <div style={{ padding: "2rem" }}>
            <h1>Dashboard</h1>
            <p>{dashboard}</p>

            {localStorage.getItem("rememberMe") === "true" && (
                <p style={{ color: "green", fontStyle: "italic" }}>
                    ✓ You are staying logged in (1 week session)
                </p>
            )}


            <div className="flex items-center gap-3 mb-4">
                <TaskCreation buttonName="New Task" currentUserData={userData} />
                <NewProjectButton
                    disabled={!canCreateProject}
                    onCreated={() => setRefreshKey((k) => k + 1)}
                />
                <Link to="/schedule">
                    <Button variant="outline">View Schedule</Button>
                </Link>
            </div>

      <TaskDashboard currentUserData={userData} project project_id={2} />
    </div>
  );
}
