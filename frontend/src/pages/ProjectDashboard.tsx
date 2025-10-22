import { useEffect, useState } from "react";
import { useAuth } from "@/hooks/useAuth";
import { Separator } from "@/components/ui/separator";
import ProjectInfoCard from "@/components/ProjectManagement/ProjectInfoCard";
import ProjectCreation from "@/components/ProjectManagement/ProjectCreation";

// Define the shape of the data for a single project
interface Project {
  id: number;
  name: string;
  deadline: string;
  status: string;
  owner_email: string;
}

export default function ProjectDashboard() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0); // Used to trigger re-fetch

  const { userData } = useAuth();
  const token = localStorage.getItem("token");

  // Determine if the current user can create projects
  const canCreateProject = userData.role === "manager" || userData.role === "director";

  // Callback function to refresh the dashboard when a new project is created
  const refreshDashboard = () => {
    setRefreshKey(prevKey => prevKey + 1);
  };

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
      } catch (err: unknown) {
          setError(err instanceof Error ? err.message : "An unknown error occurred");
      } finally {
        setLoading(false);
      }
    };

    fetchProjects();
  }, [refreshKey, token]); // Re-fetch when refreshKey changes

  if (loading) return <p className="p-8">Loading projects...</p>;
  if (error) return <p className="p-8 text-red-700">{error}</p>;

  return (
    <div className="p-4 md:p-8">
      {/* Page Header */}
      <div className="flex flex-wrap justify-between items-center mb-6 gap-4">
        <div>
          <h1 className="text-3xl font-bold">Projects</h1>
          <p className="text-gray-500">
            A complete overview of all ongoing and completed projects.
          </p>
        </div>
        
        {/* Action Button */}
        {canCreateProject && (
          <ProjectCreation 
            currentUserData={userData} 
            onProjectCreated={refreshDashboard} 
          />
        )}
      </div>
      
      <Separator className="my-6" />

      {/* Grid of Project Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {projects.map((project) => (
          <ProjectInfoCard
            key={project.id}
            project={project}
          />
        ))}
      </div>
    </div>
  );
}