import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import TaskDashboard from "@/pages/TaskDashboard";
import UpdateProjectDialog from "@/components/ProjectManagement/UpdateProjectDialog";
import TaskCreation from "@/components/TaskManagement/TaskCreation";
import AddExistingTaskDialog from "@/components/ProjectManagement/AddExistingTaskDialog";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { ArrowLeft, Edit, Plus, Link as LinkIcon } from "lucide-react";
import { toast } from "sonner";

// Define the shape of a Project object for this page
interface Project {
  id: number;
  name: string;
  description?: string;
  notes?: string;
  deadline: string;
  status: string;
  owner_email: string;
  collaborators?: { id: number; email: string }[];
  attachments?: { id: number; filename: string }[];
}

export default function ProjectDetailPage() {
  const { projectId } = useParams<{ projectId: string }>(); // Get project ID from URL
  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  
  // State to control all the dialogs on this page
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [isCreateTaskOpen, setIsCreateTaskOpen] = useState(false);
  const [isAddTaskOpen, setIsAddTaskOpen] = useState(false);
  const [refreshTasksKey, setRefreshTasksKey] = useState(0); // Used to force TaskDashboard to refresh

  const navigate = useNavigate();
  const { userData } = useAuth();
  const token = localStorage.getItem("token");

  // Fetch the project's details when the page loads
  useEffect(() => {
    const fetchProject = async () => {
      setLoading(true);
      try {
        const res = await fetch(`/api/project/get-project/${projectId}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error("Failed to fetch project details.");
        const data = await res.json();
        setProject(data);
      } catch (error: any) {
        toast.error(error.message);
      } finally {
        setLoading(false);
      }
    };
    fetchProject();
  }, [projectId, token]);

  // This function is called when a task is created or linked, triggering a refresh
  const handleTaskChange = () => {
    setRefreshTasksKey(prev => prev + 1);
  };
  
  // This function updates the project details after editing
  const handleUpdateSuccess = (updatedProject: Project) => {
    setProject(updatedProject);
    setIsEditDialogOpen(false);
  };

  if (loading) return <p className="p-8">Loading project details...</p>;
  if (!project) return <p className="p-8 text-red-600">Project not found.</p>;

  return (
    <div className="p-4 md:p-8">
      <Button variant="ghost" onClick={() => navigate(-1)} className="mb-4">
        <ArrowLeft className="mr-2 h-4 w-4" /> Back to Projects
      </Button>

      {/* Project Header with Action Buttons */}
      <div className="flex flex-wrap justify-between items-start gap-4">
        <div>
          <h1 className="text-3xl font-bold">{project.name}</h1>
          <p className="text-gray-500">Owned by: {project.owner_email}</p>
          <Badge className="mt-2">{project.status}</Badge>
        </div>
        <div className="flex items-center gap-2">
            <Button onClick={() => setIsCreateTaskOpen(true)}>
                <Plus className="mr-2 h-4 w-4" /> New Task
            </Button>
            <Button variant="outline" onClick={() => setIsAddTaskOpen(true)}>
                <LinkIcon className="mr-2 h-4 w-4" /> Add Existing Task
            </Button>
            <Button variant="outline" onClick={() => setIsEditDialogOpen(true)}>
                <Edit className="mr-2 h-4 w-4" /> Edit Project
            </Button>
        </div>
      </div>

      {/* Project Details Section */}
      <div className="mt-6 grid gap-4 md:grid-cols-2">
        <div>
          <h3 className="font-semibold">Description</h3>
          <p className="text-gray-700 whitespace-pre-wrap">{project.description || "No description provided."}</p>
        </div>
        <div>
          <h3 className="font-semibold">Notes</h3>
          <p className="text-gray-700 whitespace-pre-wrap">{project.notes || "No notes provided."}</p>
        </div>
      </div>
      
      <Separator className="my-8" />
      
      {/* Task Dashboard for this project */}
      <h2 className="text-2xl font-bold mb-4">Project Tasks</h2>
      <TaskDashboard project={true} project_id={project.id} refreshKey={refreshTasksKey} />

      {/* Render all the dialogs (they are invisible until opened) */}
      {userData && (
          <>
            <UpdateProjectDialog isOpen={isEditDialogOpen} setIsOpen={setIsEditDialogOpen} project={project} currentUserData={userData} onUpdateSuccess={handleUpdateSuccess}/>
            
            <TaskCreation isOpen={isCreateTaskOpen} setIsOpen={setIsCreateTaskOpen} buttonName="" currentUserData={userData} projectId={project.id} onTaskCreated={handleTaskChange} />

            <AddExistingTaskDialog isOpen={isAddTaskOpen} setIsOpen={setIsAddTaskOpen} projectId={project.id} onTaskLinked={handleTaskChange} />
          </>
      )}
    </div>
  );
}