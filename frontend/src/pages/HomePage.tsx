import { useAuth } from "@/hooks/useAuth";
import TaskCreation from "@/components/TaskManagement/TaskCreation";
import ProjectCreation from "@/components/ProjectManagement/ProjectCreation";

export default function HomePage() {
    const { userData } = useAuth();

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

                {canCreateProject && (
                    <ProjectCreation
                        currentUserData={userData}
                        onProjectCreated={() => window.location.reload()}
                    />
                )}
            </div>
        </div>
    );
}