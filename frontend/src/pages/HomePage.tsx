﻿import { useState } from "react";
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
    <div style={{ padding: "2rem" }}>
      <h1>Dashboard</h1>
      <p>{userData.role}</p>

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
          {/* <Link to="/schedule">
              <Button variant="outline">View Schedule</Button>
          </Link> */}
      </div>
      <TaskDashboard currentUserData={userData} project project_id={2} />
    </div>
  );
}
