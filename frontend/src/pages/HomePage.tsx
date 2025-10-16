import { useState } from "react";
import { useAuth } from "@/hooks/useAuth";

import TaskCreation from "@/components/TaskManagement/TaskCreation";
import TaskDashboard from "@/pages/TaskDashboard";
import NewProjectButton from "@/components/Project/NewProjectButton";
import ProjectList from "@/components/Project/ProjectList";

export default function HomePage() {
  const { userData, handleLogout } = useAuth();
  const [refreshKey, setRefreshKey] = useState(0);

  const canCreateProject = userData.role === "manager" || userData.role === "director";

  return (
    <div className="p-6">
      <h1>Dashboard</h1>
      <p>this is the {userData.role} dashboard</p>

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
      </div>

      <ProjectList refreshKey={refreshKey} />

      <button
        onClick={handleLogout}
        style={{
          marginTop: "1rem",
          backgroundColor: "red",
          color: "white",
          padding: "0.5rem 1rem",
          border: "none",
          borderRadius: "4px",
          cursor: "pointer",
        }}
      >
        Logout
      </button>

      <TaskDashboard currentUserData={userData} />
    </div>
  );
}
