import { useState } from "react"
import UpdateTaskDialog from "@/components/TaskManagement/UpdateTaskDialog"
import {
  Card,
  CardContent,
  CardDescription,
  CardTitle,
} from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { toast } from "sonner"
import { FolderKanban } from "lucide-react"

interface UserData {
  role: string,
  email: string
}

interface Task {
  id: number,
  title: string,
  description?: string,
  duedate: string,
  status: string,
  priority: number,
  created_at: string,
  notes: string,
  owner_email: string,
  project: string,
  collaborators?: {
    id: number,
    email: string,
    name?: string
  }[],
  attachments?: {
    id: number,
    filename: string
  }[]
}

type TaskInfoCardProps = {
  task: Task,
  currentUserData: UserData,
  onUpdate?: (updatedTask: Task) => void
}

export default function TaskInfoCard({ task, currentUserData, onUpdate }: TaskInfoCardProps) {
  const [open, setOpen] = useState<boolean>(false)

  const handleUpdateSuccess = (updatedTask: Task) => {
    if (onUpdate) onUpdate(updatedTask)

    toast.success("Task updated successfully")
    setOpen(false)
  }

  const badgeColor: Record<string, string> = {
    "Unassigned": "bg-gray-400",
    "Ongoing": "bg-blue-400",
    "Pending Review": "bg-amber-400",
    "Completed": "bg-emerald-400"
  }

  if (!task) return 

  return (
    <div>
      <Card className="rounded-none bg-white" onClick={() => setOpen(true)}>
        <CardContent>
          <CardTitle>{task.title}</CardTitle>          
          <CardDescription className="mt-1">
            Task Owner: {task.owner_email} <br/>
            Due Date: {task.duedate} <br />
            Priority: {task.priority} 
          </CardDescription>

          <Badge className={`${badgeColor[task.status]} text-white mt-3`}>{task.status}</Badge>

          {task.project && (
            <div className="flex flex-row gap-1 items-center mt-3 text-gray-600">
              <FolderKanban size={18} />
              {task.project}
            </div>
          )}
        </CardContent>
      </Card>

      <UpdateTaskDialog open={open} setOpen={setOpen} task={task} currentUserData={currentUserData} onUpdateSuccess={handleUpdateSuccess} />
    </div>
  )
}