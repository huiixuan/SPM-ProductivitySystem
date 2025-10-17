import { useEffect, useState, useRef } from "react";
import { useAuth } from "@/hooks/useAuth";
import ProjectInfoCard from "@/components/ProjectManagement/ProjectInfoCard";

interface Project {
  id: number;
  name: string;
  description?: string;
  deadline: string;
  status: string;
  owner_email: string;
  collaborators?: { id: number; email: string; }[];
  attachments?: { id: number; filename: string; }[];
}

interface UserData {
  role: string;
  email: string;
}

interface DashboardProps {
  refreshKey: number; // Add this prop to trigger re-fetch
}


export default function ProjectDashboard({ refreshKey }: DashboardProps) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { userData } = useAuth();
  const token = localStorage.getItem("token");

  useEffect(() => {
    const fetchProjects = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch("/api/project/get-all-projects", {
          method: "GET",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
        });
        if (!res.ok) throw new Error("Failed to fetch projects");
        const data = await res.json();
        setProjects(data);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchProjects();
  }, [refreshKey, token]); // Re-fetch when refreshKey changes

  const handleProjectUpdate = (updatedProject: Project) => {
    setProjects((prev) =>
      prev.map((p) => (p.id === updatedProject.id ? updatedProject : p))
    );
  };

  if (loading) return <p>Loading projects...</p>;
  if (error) return <p className="text-red-700">{error}</p>;

  return (
    <div className="p-4">
      <h2 className="font-bold text-lg pl-4 mb-4">Project Overview</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 p-4">
        {projects.map((project) => (
          <ProjectInfoCard
            key={project.id}
            project={project}
            currentUserData={userData as UserData}
            onUpdate={handleProjectUpdate}
          />
        ))}
      </div>
    </div>
  );
}