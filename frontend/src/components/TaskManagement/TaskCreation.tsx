import { useState } from "react"
import { zodResolver } from "@hookform/resolvers/zod"
import { useForm } from "react-hook-form"
import { z } from "zod"
import EmailCombobox from "@/components/TaskManagement/EmailCombobox"
import DatePicker from "@/components/TaskManagement/DatePicker"
import UploadAttachments from "@/components/TaskManagement/UploadAttachments"
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
} from "@/components/ui/form"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from "@/components/ui/select"
import { toast } from "sonner"
import { Plus } from "lucide-react"

const formSchema = z.object({
  title: z.string().min(1, "Title is required."),
  description: z.string().optional(),
  duedate: z.date(),
  status: z.string().min(1, "Select a status."),
  priority: z.coerce.number().min(1, "Priority is required."),
  owner: z.string().min(1, "Task owner is required."),
  collaborators: z.array(z.string()),
  notes: z.string().optional(),
  attachments: z.array(z.instanceof(File))
})
type TaskFormData = z.infer<typeof formSchema>

export default function TaskCreation() {
  const [open, setOpen] = useState<boolean>(false)
  const statuses = ["Unassigned", "Ongoing", "Pending Review", "Completed"]
  const priorities = Array.from({ length: 10 }, (_, i) => i + 1)

  const form = useForm<TaskFormData>({
    resolver: zodResolver(formSchema),
    mode: "onChange",
    defaultValues: {
      title: "",
      description: "",
      status: "",
      owner: "",
      collaborators: [],
      notes: "",
      attachments: [],
      priority: 1
    }
  })

  async function onSubmit(values: TaskFormData) {
    const formData = new FormData()

    formData.append("title", values.title)

    if (values.description) {
      formData.append("description", values.description)
    }

    formData.append("duedate", values.duedate.toISOString())
    formData.append("status", values.status)
    formData.append("priority", values.priority.toString())
    formData.append("owner", values.owner)

    if (values.notes) {
      formData.append("notes", values.notes)
    }

    values.collaborators.forEach((c) => {
      formData.append("collaborators", c)
    })

    values.attachments.forEach((file) => {
      formData.append("attachments", file)
    })

    try {
      const res = await fetch("/api/task/create-task", {
        method: "POST",
        body: formData
      })

      const data = await res.json()

      if (res.ok && data.success) {
        toast.success("Task created successfully.")
        form.reset()
        setOpen(false)
      } else {
        toast.error("Task creation failed.")
      }

    } catch (error) {
      toast.error("Task creation failed: " + error)
    }
  }

  return (
    <Dialog 
      open={open} 
      onOpenChange={(isOpen) => {
        if (!isOpen) {
          form.reset()
        }
        setOpen(isOpen)
    }}>
      <DialogTrigger asChild>
        <Button variant="outline"><Plus /> New Task</Button>
      </DialogTrigger>

      <DialogContent className="sm:max-w-[825px]">
        <DialogHeader>
          <DialogTitle>Add New Task</DialogTitle>
          <DialogDescription>
            Fill in the details below to add a new task to your list.
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)}>
            <div className="flex flex-col gap-4">
              <FormField control={form.control} name="title" render={({ field, fieldState }) => (
                <FormItem>
                  <FormLabel>Title</FormLabel>
                  <FormControl>
                    <Input {...field} />
                  </FormControl>
                  {fieldState.error && (<p className="text-red-700">{fieldState.error.message}</p>)}
                </FormItem>
              )} />

              <FormField control={form.control} name="description" render={({ field }) => (
                <FormItem>
                  <FormLabel>Description</FormLabel>
                  <FormControl>
                    <Textarea {...field} />
                  </FormControl>
                </FormItem>
              )} />

              <div className="flex flex-row gap-2">
                <FormField control={form.control} name="duedate" render={({ field, fieldState }) => (
                  <FormItem className="w-1/2">
                    <FormLabel>Due Date</FormLabel>
                    <FormControl>
                      <DatePicker date={field.value} onChange={field.onChange} />
                    </FormControl>
                    {fieldState.error && (<p className="text-red-700">{fieldState.error.message}</p>)}
                  </FormItem>
                )} />

                <FormField control={form.control} name="status" render={({ field, fieldState }) => (
                  <FormItem className="w-1/2">
                    <FormLabel>Status</FormLabel>
                    <FormControl>
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
                    </FormControl>
                    {fieldState.error && (<p className="text-red-700">{fieldState.error.message}</p>)}
                  </FormItem>
                )} />
              </div>

             
            <div className="flex flex-row gap-2">
              <FormField control={form.control} name="priority" render={({ field, fieldState }) => (
                <FormItem className="w-1/2">
                  <FormLabel>Priority</FormLabel>
                  <FormControl>
                    <Select onValueChange={(value) => field.onChange(parseInt(value, 10))} value={field.value?.toString()}>
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="Priority" />
                      </SelectTrigger>
                      <SelectContent>
                        {priorities.map(p => (
                          <SelectItem key={p} value={p.toString()}>
                            {p} {/* Changed from "Priority {p}" to just "{p}" */}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </FormControl>
                  {fieldState.error && (<p className="text-red-700">{fieldState.error.message}</p>)}
                </FormItem>
              )} />


                <FormField control={form.control} name="owner" render={({ field, fieldState }) => (
                  <FormItem className="w-1/2">
                    <FormLabel>Task Owner</FormLabel>
                    <FormControl>
                      <EmailCombobox value={field.value} onChange={field.onChange} placeholder="Select Task Owner..." />
                    </FormControl>
                    {fieldState.error && (<p className="text-red-700">{fieldState.error.message}</p>)}
                  </FormItem>
                )} />
              </div>

              <FormField control={form.control} name="collaborators" render={({ field }) => (
                <FormItem>
                  <FormLabel>Collaborators</FormLabel>
                  <FormControl>
                    <EmailCombobox value={field.value as string[]} onChange={field.onChange} placeholder="Select Collaborators..." multiple />
                  </FormControl>
                </FormItem>
              )} />

              <FormField control={form.control} name="notes" render={({ field }) => (
                <FormItem>
                  <FormLabel>Notes</FormLabel>
                  <FormControl>
                    <Textarea {...field} />
                  </FormControl>
                </FormItem>
              )} />

              <FormField control={form.control} name="attachments" render={({ field }) => (
                <FormItem>
                  <FormLabel>Attachments</FormLabel>
                  <FormControl>
                    <UploadAttachments value={field.value} onChange={field.onChange} />
                  </FormControl>
                </FormItem>
              )} />
            </div>

            <DialogFooter>
              <DialogClose asChild>
                <Button variant="outline">Cancel</Button>
              </DialogClose>
              <Button type="submit" disabled={!form.formState.isValid}>Create Task</Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}