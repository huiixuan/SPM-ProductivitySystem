import { useState } from "react";
import { useAuth } from "@/hooks/useAuth";

// Import the Task Creation component you already had
import TaskCreation from "@/components/TaskManagement/TaskCreation";

// Import the new Project Creation component
import ProjectCreation from "@/components/ProjectManagement/ProjectCreation";

export default function HomePage() {
  const { userData, handleLogout } = useAuth();
  const [refreshKey, setRefreshKey] = useState(0);

  // This logic correctly determines who can see the "New Project" button
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
          {/* This is your existing Task Creation button - unchanged */}
          <TaskCreation buttonName="New Task" currentUserData={userData} />
        
          {/* This adds the New Project button, only if the user has the correct role */}
          {canCreateProject && (
              <ProjectCreation 
                  currentUserData={userData} 
                  onProjectCreated={() => setRefreshKey((k) => k + 1)} 
              />
          )}
      </div>

    </div>
  );
}