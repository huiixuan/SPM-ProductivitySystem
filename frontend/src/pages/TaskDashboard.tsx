import { useEffect, useState, useRef } from "react"
import { useAuth } from "@/hooks/useAuth"
import TaskInfoCard from "@/components/TaskManagement/TaskInfoCard"

interface DashboardProps {
  project?: boolean,
  project_id?: number
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

export default function TaskDashboard({ project = false, project_id }: DashboardProps) {
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const refreshTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  const { userData } = useAuth()
  const token = localStorage.getItem("token")

  const statuses = ["Unassigned", "Ongoing", "Pending Review", "Completed"]

  const fetchTasks = async (silent: boolean = false) => {
    if (!silent) setLoading(true)
    setError(null)

    try {
      let res

      if (project) {
        res = await fetch(`/api/task/get-project-tasks/${project_id}`, {
          method: "GET",
          headers: {
            Authorization: `Bearer ${token}`
          }
        })
      } else {
        res = await fetch("/api/task/get-user-tasks", {
          method: "GET",
          headers: {
            Authorization: `Bearer ${token}`
          }
        })
      }

      if (!res.ok) throw new Error("Failed to fetch tasks")
      const data = await res.json()

      setTasks(data)

    } catch (e) {
      setError("Unable to load tasks.")

    } finally {
      if (!silent) setLoading(false)
    }
  }

  const handleTaskUpdate = (updatedTask: Task) => {
    setTasks((prev) => prev.map((t) => (t.id === updatedTask.id ? updatedTask : t)))
    
    if (refreshTimeoutRef.current) {
      clearTimeout(refreshTimeoutRef.current)
    }
    
    refreshTimeoutRef.current = setTimeout(() => {
      fetchTasks(true)
    }, 1500)
  }

  useEffect(() => {
    fetchTasks()
    
    return () => {
      if (refreshTimeoutRef.current) {
        clearTimeout(refreshTimeoutRef.current)
      }
    }
  }, [])

  if (loading) return <p>Loading tasks...</p>
  if (error) return <p className="text-red-700">{error}</p>

  return (
    <div className="p-4">
      <p className="font-bold text-lg pl-4">Task Overview</p>
      <div className="flex gap-4 p-4 overflow-x-auto justify-center">
        {statuses.map((status) => (
          <div key={status} className="flex-1 min-w-[250px] bg-gray-100 p-2 rounded-md">
            <p className="font-bold mb-2">
              {status} ({tasks.filter(t => t.status === status).length})
            </p>

            {tasks
              .filter(task => task.status === status)
              .map(task => (
                <div key={task.id} className="mb-2 cursor-pointer">
                  <TaskInfoCard 
                    task={task} 
                    currentUserData={userData} 
                    onUpdate={handleTaskUpdate} 
                  />
                </div>
              ))}
          </div>
        ))}
      </div>
    </div>
  )
}