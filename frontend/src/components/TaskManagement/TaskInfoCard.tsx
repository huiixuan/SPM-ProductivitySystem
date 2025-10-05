import { useState, useEffect } from "react"
import UpdateTaskDialog from "@/components/TaskManagement/UpdateTaskDialog"
import {
  Card,
  CardContent,
  CardDescription,
  CardTitle,
} from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { toast } from "sonner"
import { FolderKanban } from 'lucide-react'

type TaskInfoCardProps = {
  task_id: number,
  currentUserRole: string
}

interface Task {
  id: number,
  title: string,
  description?: string,
  duedate: string,
  status: string,
  created_at: string,
  notes: string,
  owner_email: string,
  project: string
}

export default function TaskInfoCard({ task_id, currentUserRole }: TaskInfoCardProps) {
  const [task, setTask] = useState<Task | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState<boolean>(false)
  const [open, setOpen] = useState<boolean>(false)

  const fetchTask = async () => {
    setError(null)
    setLoading(true)

    try {
      const res = await fetch(`/api/task/get-task/${task_id}`)
      if (!res.ok) {
        throw new Error(`Failed to fetch task with ID ${task_id}: ${res.status}`)
      }

      const taskInfo = await res.json()
      setTask(taskInfo)

    } catch (e) {
      setError("Unable to load task. Please try again later.")

    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchTask()
  }, [task_id])

  const handleUpdateSuccess = () => {
    toast.success("Task updated successfully")
    setOpen(false)
    fetchTask() 
  }

  const badgeColor: Record<string, string> = {
    "Unassigned": "bg-gray-400",
    "Ongoing": "bg-blue-400",
    "Pending Review": "bg-amber-400",
    "Completed": "bg-green-400"
  }

  if (!task) return 

  return (
    <div>
      {loading ? (
        <p className="text-gray-600">Loading...</p>
      ) : error ? (
        <p className="text-red-700">{error}</p>
      ) : (
        <div>
          <Card className="rounded-none" onClick={() => setOpen(true)}>
            <CardContent>
              <CardTitle>{task.title}</CardTitle>          
              <CardDescription className="mt-1">
                Task Owner: {task.owner_email} <br/>
                Due Date: {task.duedate} 
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
          
          <UpdateTaskDialog open={open} setOpen={setOpen} task={task} currentUserRole={currentUserRole} onUpdateSuccess={handleUpdateSuccess} />
        </div>
      )}
    </div>
  )
}