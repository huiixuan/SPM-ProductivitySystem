import { useForm } from "react-hook-form"
import { z } from "zod"
import { EmailCombobox } from "@/components/TaskManagement/EmailCombobox"
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
} from "@/components/ui/form"
import { DatePicker } from "@/components/TaskManagement/DatePicker"
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
import { Plus } from "lucide-react"

const formSchema = z.object({
  title: z.string().min(1, "Title is required."),
  description: z.string().optional(),
  duedate: z.date(),
  status: z.string().min(1, "Select a status."),
  owner: z.string().min(1, "Task owner is required."),
  collaborators: z.array(z.string()).optional,
  notes: z.string().optional(),
  attachments: z.array(z.instanceof(File)).optional().default([])
})
type TaskFormData = z.infer<typeof formSchema>

export function TaskCreation() {
  const statuses = ["Unassigned", "Ongoing", "Pending Review", "Completed"]

  const form = useForm<TaskFormData>()

  function onSubmit(values: z.infer<typeof formSchema>) {
    
  }

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="outline"><Plus /> New Task</Button>
      </DialogTrigger>

      <DialogContent className="sm:max-w-[625px]">
        <DialogHeader>
          <DialogTitle>Add New Task</DialogTitle>
          <DialogDescription>
            Fill in the details below to add a new task to your list.
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)}>
            <div className="flex flex-col gap-4">
              <FormField control={form.control} name="title" render={({ field }) => (
                <FormItem>
                  <FormLabel>Title</FormLabel>
                  <FormControl>
                    <Input {...field} />
                  </FormControl>
                </FormItem>
              )} />

              <FormField control={form.control} name="description" render={({ field }) => (
                <FormItem>
                  <FormLabel>Description</FormLabel>
                  <FormControl>
                    <Textarea defaultValue="" {...field} />
                  </FormControl>
                </FormItem>
              )} />

              <div className="flex flex-row gap-2">
                <FormField control={form.control} name="duedate" render={({ field }) => (
                  <FormItem className="w-1/2">
                    <FormLabel>Due Date</FormLabel>
                    <FormControl>
                      <DatePicker date={field.value} onChange={field.onChange} />
                    </FormControl>
                  </FormItem>
                )} />

                <FormField control={form.control} name="status" render={({ field }) => (
                  <FormItem className="w-1/2">
                    <FormLabel>Status</FormLabel>
                    <FormControl>
                      <Select onValueChange={field.onChange} value={field.value}>
                        <SelectTrigger className="w-full">
                          <SelectValue placeholder="Status" />
                        </SelectTrigger>

                        <SelectContent>
                          {statuses.map(status => (
                            <SelectItem value={status}>{status}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </FormControl>
                  </FormItem>
                )} />
              </div>

              <FormField control={form.control} name="owner" render={({ field }) => (
                <FormItem>
                  <FormLabel>Task Owner</FormLabel>
                  <FormControl>
                    <EmailCombobox value={field.value} onChange={field.onChange} placeholder="Select Task Owner..." />
                  </FormControl>
                </FormItem>
              )} />

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

                  </FormControl>
                </FormItem>
              )} />
            </div>
          </form>
        </Form>
        
        <DialogFooter>
          <DialogClose asChild>
            <Button variant="outline">Cancel</Button>
          </DialogClose>
          <Button type="submit">Save changes</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
