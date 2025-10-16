import { useEffect } from "react"
import TaskCreation from "@/components/TaskManagement/TaskCreation"
import DatePicker from "@/components/TaskManagement/DatePicker"
import EmailCombobox from "@/components/TaskManagement/EmailCombobox"
import UploadAttachments from "@/components/TaskManagement/UploadAttachments"
import { zodResolver } from "@hookform/resolvers/zod"
import { useForm } from "react-hook-form"
import { z } from "zod"
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
} from "@/components/ui/form"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from "@/components/ui/select"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { toast } from "sonner"

interface AttachmentType {
  id: number;
  filename: string;
}

const attachmentSchema = z.union([
  z.instanceof(File),
  z.object({
    id: z.number(),
    filename: z.string()
  })
])

const formSchema = z.object({
  title: z.string().min(1, "Title is required."),
  description: z.string().optional(),
  duedate: z.date(),
  status: z.string().min(1, "Select a status."),
  priority: z.number().min(1, "Priority is required."),
  owner: z.string().min(1, "Task owner is required."),
  collaborators: z.array(z.string()).optional(),
  notes: z.string().optional(),
  attachments: z.array(attachmentSchema)
})
type TaskFormData = z.infer<typeof formSchema>

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

interface UserData {
  role: string,
  email: string
}

type UpdateTaskDialogProps = {
  open: boolean,
  setOpen: (open: boolean) => void,
  task: Task,
  currentUserData: UserData,
  onUpdateSuccess: () => void
}

export default function UpdateTaskDialog({ 
  open,
  setOpen,
  task,
  currentUserData,
  onUpdateSuccess
}: UpdateTaskDialogProps) {
  const statuses = ["Unassigned", "Ongoing", "Pending Review", "Completed"]
  const priorities = Array.from({ length: 10 }, (_, i) => i + 1)

  const form = useForm<TaskFormData>({
    resolver: zodResolver(formSchema),
    mode: "onChange",
    defaultValues: {
      title: task.title,
      description: task.description || "",
      status: task.status,
      duedate: new Date(task.duedate),
      priority: task.priority || 1,
      owner: task.owner_email,
      collaborators: task.collaborators?.map(c => c.email) || [],
      notes: task.notes || "",
      attachments: task.attachments || []
    }
  })

  useEffect(() => {
    form.reset({
      title: task.title,
      description: task.description || "",
      duedate: new Date(task.duedate),
      status: task.status,
      priority: task.priority || 1,
      owner: task.owner_email,
      collaborators: task.collaborators?.map(c => c.email) || [],
      notes: task.notes || "",
      attachments: task.attachments || []
    })
  }, [task, form])

  const isOwner = currentUserData.email === task.owner_email
  const isCollaborator = task.collaborators?.some((c) => c.email === currentUserData.email)

  async function onSubmit(values: TaskFormData) {
    try {
      const formData = new FormData()

      formData.append("title", values.title)
      formData.append("description", values.description || "")
      formData.append("duedate", values.duedate.toISOString())
      formData.append("status", values.status)
      formData.append("priority", values.priority.toString())
      formData.append("owner", values.owner)
      formData.append("notes", values.notes || "")

      formData.append("collaborators", JSON.stringify(values.collaborators || []))

      const existingAttachments = values.attachments
        .filter((att): att is AttachmentType => !(att instanceof File))
        .map(att => ({ id: att.id }))
      formData.append("existing_attachments", JSON.stringify(existingAttachments))

      const newFiles = values.attachments.filter((att): att is File => att instanceof File)
      newFiles.forEach(file => {
        formData.append("attachments", file)
      })

      console.log("Submitting form data:", Object.fromEntries(formData))

      const res = await fetch(`/api/task/update-task/${task.id}`, {
        method: "PUT",
        body: formData,
      })

      if (!res.ok) {
        const errorData = await res.json()
        toast.error(errorData.message || "Failed to update task")
        return
      }

      onUpdateSuccess()
      setOpen(false)

    } catch (error) {
      toast.error("Task creation failed: " + error)
    }
  }

  const badgeColor: Record<string, string> = {
    "Unassigned": "bg-gray-400",
    "Ongoing": "bg-blue-400",
    "Pending Review": "bg-amber-400",
    "Completed": "bg-emerald-400"
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="sm:max-w-[825px]">
        <DialogHeader className="flex flex-row items-center justify-between">
          <div className="flex flex-col gap-1">
            <DialogTitle>Update Task</DialogTitle>
            <DialogDescription>Modify the details of this task below.</DialogDescription>
          </div>

          <div className="pr-8">
            <TaskCreation buttonName="Subtask" currentUserData={currentUserData} />
          </div>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)}>
            <div className="flex flex-col gap-4">
              <FormField control={form.control} name="title" render={({ field, fieldState }) => (
                <FormItem>
                  <FormLabel>Title</FormLabel>
                  <FormControl>
                    {isOwner ? (
                      <Input {...field} />
                    ) : (
                      <div>
                        {task.title}
                      </div>
                    )}
                  </FormControl>

                  {fieldState.error && (
                    <p className="text-red-700">{fieldState.error.message}</p>
                  )}
                </FormItem>
              )} />
                
              <FormField control={form.control} name="description" render={({ field }) => (
                <FormItem>
                  <FormLabel>Description</FormLabel>
                  <FormControl>
                    {(isOwner || isCollaborator) ? (
                      <Textarea {...field} />
                    ) : (
                      <div>
                        {task.description}
                      </div>
                    )}
                  </FormControl>
                </FormItem>
              )} />

              <div className="flex flex-row gap-2">
                <FormField control={form.control} name="duedate" render={({ field }) => (
                  <FormItem className="w-1/2">
                    <FormLabel>Due Date</FormLabel>
                    <FormControl>
                      {isOwner ? (
                        <DatePicker date={field.value} onChange={field.onChange} />
                      ) : (
                        <div>
                          {task.duedate}
                        </div>
                        
                      )}
                    </FormControl>
                  </FormItem>
                )} />

                <FormField control={form.control} name="status" render={({ field, fieldState }) => (
                  <FormItem className="w-1/2">
                    <FormLabel>Status</FormLabel>
                    <FormControl>
                      {(isOwner || isCollaborator) ? (
                        <Select onValueChange={field.onChange} value={field.value}>
                          <SelectTrigger className="w-full">
                            <SelectValue placeholder="Status" />
                          </SelectTrigger>

                          <SelectContent>
                            {statuses.map(status => (
                              <SelectItem key={status} value={status}>{status}</SelectItem>
                            ))}
                          </SelectContent>
                      </Select>
                      ) : (
                        <Badge className={`${badgeColor[task.status]} text-white px-3`}>{task.status}</Badge>
                      )}
                    </FormControl>

                    {fieldState.error && (
                      <p className="text-red-700">{fieldState.error.message}</p>
                    )}
                  </FormItem>
                )} />
              </div>
              
              <div className="flex flex-row gap-2">
                <FormField control={form.control} name="priority" render={({ field, fieldState }) => (
                  <FormItem className="w-1/2">
                    <FormLabel>Priority</FormLabel>
                    <FormControl>
                      {isOwner? (
                        <Select onValueChange={(v) => field.onChange(parseInt(v))} value={field.value.toString()}>
                          <SelectTrigger className="w-full">
                            <SelectValue placeholder="Priority" />
                          </SelectTrigger>

                          <SelectContent>
                            {priorities.map(p => (
                              <SelectItem key={p} value={p.toString()}>{p}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      ) : (
                        <div>{task.priority}</div>
                      )}
                    </FormControl>

                    {fieldState.error && (
                      <p className="text-red-700">{fieldState.error.message}</p>
                    )}
                  </FormItem>
                )} />

                <FormField control={form.control} name="owner" render={({ field, fieldState }) => (
                  <FormItem className="w-1/2">
                    <FormLabel>Task Owner</FormLabel>
                    <FormControl>
                      {isOwner ? (
                          <EmailCombobox value={field.value} onChange={field.onChange} placeholder="Select Task Owner..." currentUserData={currentUserData} />
                        ) : (
                          <div>
                            {task.owner_email}
                          </div>
                        )} 
                    </FormControl>

                    {fieldState.error && (
                      <p className="text-red-700">{fieldState.error.message}</p>
                    )}
                  </FormItem>
                )} />
              </div>

              <FormField control={form.control} name="collaborators" render={({ field }) => (
                <FormItem>
                  <FormLabel>Collaborators</FormLabel>
                  <FormControl>
                    {isOwner ? (
                      <EmailCombobox value={field.value as string[]} onChange={field.onChange} placeholder="Select Collaborators..." currentUserData={currentUserData} multiple />
                    ) : (
                      <div>
                        {task.collaborators?.length ? (
                          task.collaborators.map((c) => (
                            <span key={c.id}>{c.email}</span>
                          ))
                        ) : (
                          <span className="text-gray-500 italic">No collaborators</span>
                        )}
                      </div>
                    )}
                  </FormControl>
                </FormItem>
              )} />

              <FormField control={form.control} name="notes" render={({ field }) => (
                <FormItem>
                  <FormLabel>Notes</FormLabel>
                  <FormControl>
                    {(isOwner || isCollaborator) ? (
                      <Textarea {...field} />
                    ) : (
                      <div>
                        {task.notes}
                      </div>
                    )}
                    
                  </FormControl>
                </FormItem>
              )} />

              <FormField control={form.control} name="attachments" render={({ field }) => (
                <FormItem>
                  <FormLabel>Attachments</FormLabel>
                  <FormControl>
                    {(isOwner || isCollaborator) ? (
                      <div>
                        {task.attachments?.length ? (
                          <UploadAttachments value={field.value} onChange={field.onChange} />
                        ) : (
                          <span className="text-gray-500 italic">No attachments</span>
                        )}
                      </div>
                    ) : (
                      <div>
                        {task.attachments?.length ? (
                          task.attachments.map(att => (
                            <a key={att.id} href={`/api/attachment/get-attachment/${att.id}`} target="_blank" rel="noopener noreferrer">{att.filename}</a>
                          ))
                        ) : (
                          <span className="text-gray-500 italic">No attachments</span>
                        )}
                      </div>
                    )}
                    
                  </FormControl>
                </FormItem>
              )} />
            </div>

            <DialogFooter>
              <DialogClose asChild>
                <Button variant="outline">Cancel</Button>
              </DialogClose>

              <Button type="submit" disabled={!form.formState.isValid || !isOwner || !isCollaborator}>Update Task</Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}