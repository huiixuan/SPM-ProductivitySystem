import { useState } from "react";
import UpdateProjectDialog from "@/components/ProjectManagement/UpdateProjectDialog";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";

interface UserData {
  role: string;
  email: string;
}

interface Project {
  id: number;
  name: string;
  description?: string;
  deadline: string;
  status: string;
  owner_email: string;
  collaborators?: { id: number; email: string }[];
  attachments?: { id: number; filename: string }[];
}

type ProjectInfoCardProps = {
  project: Project;
  currentUserData: UserData;
  onUpdate?: (updatedProject: Project) => void;
};

export default function ProjectInfoCard({ project, currentUserData, onUpdate }: ProjectInfoCardProps) {
  const [open, setOpen] = useState<boolean>(false);

  const handleUpdateSuccess = (updatedProject: Project) => {
    if (onUpdate) onUpdate(updatedProject);
    toast.success("Project updated successfully");
    setOpen(false);
  };

  const badgeColor: Record<string, string> = {
    "Not Started": "bg-gray-400",
    "In Progress": "bg-blue-400",
    "Completed": "bg-emerald-400",
  };

  if (!project) return null;

  return (
    <div>
      <Card className="cursor-pointer hover:shadow-lg transition-shadow" onClick={() => setOpen(true)}>
        <CardHeader>
          <CardTitle>{project.name}</CardTitle>
          <CardDescription>Owner: {project.owner_email}</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-600">
            Deadline: {new Date(project.deadline).toLocaleDateString()}
          </p>
        </CardContent>
        <CardFooter>
          <Badge className={`${badgeColor[project.status]} text-white`}>{project.status}</Badge>
        </CardFooter>
      </Card>

      <UpdateProjectDialog
        isOpen={open}
        setIsOpen={setOpen}
        project={project}
        currentUserData={currentUserData}
        onUpdateSuccess={handleUpdateSuccess}
      />
    </div>
  );
}