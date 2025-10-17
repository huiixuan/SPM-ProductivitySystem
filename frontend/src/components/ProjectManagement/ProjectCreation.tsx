import { useState } from "react"
import { zodResolver } from "@hookform/resolvers/zod"
import { useForm } from "react-hook-form"
import { z } from "zod"
import EmailCombobox from "@/components/TaskManagement/EmailCombobox" // Reusable!
import DatePicker from "@/components/TaskManagement/DatePicker" // Reusable!
import UploadAttachments from "@/components/TaskManagement/UploadAttachments" // Reusable!
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
import { FolderPlus } from "lucide-react"

interface UserData {
  role: string,
  email: string
}

type ProjectCreationProps = {
  currentUserData: UserData,
  onProjectCreated: () => void;
}

// 1. Add 'notes' to the form schema
const formSchema = z.object({
  name: z.string().min(1, "Project name is required."),
  description: z.string().optional(),
  deadline: z.date().optional(),
  status: z.string().min(1, "Select a status."),
  owner: z.string().min(1, "Select an owner."),
  collaborators: z.array(z.string()).optional(),
  notes: z.string().optional(), // 
  attachments: z.any().optional(),
});

export default function ProjectCreation({ currentUserData, onProjectCreated }: ProjectCreationProps) {
  const [open, setOpen] = useState(false);
  const token = localStorage.getItem("token");

  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: "",
      description: "",
      status: "Not Started",
      owner: currentUserData.email,
      collaborators: [],
      notes: "", 
      attachments: [],
    },
  });

  async function onSubmit(values: z.infer<typeof formSchema>) {
    const formData = new FormData();

    formData.append("name", values.name);
    formData.append("description", values.description || "");
    if (values.deadline) {
      formData.append("deadline", values.deadline.toISOString());
    }
    formData.append("status", values.status);
    formData.append("owner", values.owner);
    formData.append("notes", values.notes || ""); 

    values.collaborators?.forEach(c => formData.append("collaborators", c));

    if (values.attachments) {
      for (const file of values.attachments) {
        if (file instanceof File) {
          formData.append("attachments", file);
        }
      }
    }

    try {
      const response = await fetch("/api/project/create-project", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`
        },
        body: formData,
      });

      const result = await response.json();

      if (result.success) {
        toast.success("Project created successfully!");
        setOpen(false);
        form.reset();
        onProjectCreated();
      } else {
        toast.error(`Error: ${result.error}`);
      }
    } catch (error) {
      toast.error("An unexpected error occurred.");
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
            <FolderPlus className="mr-2 h-4 w-4" /> New Project
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>Create New Project</DialogTitle>
          <DialogDescription>
            Fill in the details below to create a new project.
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <div className="grid gap-4 py-4 max-h-[70vh] overflow-y-auto pr-2">
              <FormField control={form.control} name="name" render={({ field }) => (
                <FormItem>
                  <FormLabel>Project Name</FormLabel>
                  <FormControl><Input {...field} /></FormControl>
                </FormItem>
              )} />

              <FormField control={form.control} name="description" render={({ field }) => (
                <FormItem>
                  <FormLabel>Description</FormLabel>
                  <FormControl><Textarea {...field} /></FormControl>
                </FormItem>
              )} />
              
              <FormField control={form.control} name="deadline" render={({ field }) => (
                <FormItem>
                  <FormLabel>Deadline</FormLabel>
                  <FormControl><DatePicker date={field.value} onChange={field.onChange} /></FormControl>
                </FormItem>
              )} />

              <FormField control={form.control} name="status" render={({ field }) => (
                <FormItem>
                  <FormLabel>Status</FormLabel>
                  <Select onValueChange={field.onChange} defaultValue={field.value}>
                    <FormControl><SelectTrigger><SelectValue /></SelectTrigger></FormControl>
                    <SelectContent>
                      <SelectItem value="Not Started">Not Started</SelectItem>
                      <SelectItem value="In Progress">In Progress</SelectItem>
                      <SelectItem value="Completed">Completed</SelectItem>
                    </SelectContent>
                  </Select>
                </FormItem>
              )} />

              <FormField control={form.control} name="owner" render={({ field }) => (
                <FormItem>
                  <FormLabel>Project Owner</FormLabel>
                  <FormControl>
                    <EmailCombobox value={field.value} onChange={field.onChange} placeholder="Select Owner..." currentUserData={currentUserData} />
                  </FormControl>
                </FormItem>
              )} />

              <FormField control={form.control} name="collaborators" render={({ field }) => (
                <FormItem>
                  <FormLabel>Collaborators</FormLabel>
                  <FormControl>
                    <EmailCombobox value={field.value as string[]} onChange={field.onChange} placeholder="Select Collaborators..." currentUserData={currentUserData} multiple />
                  </FormControl>
                </FormItem>
              )} />

         
              <FormField control={form.control} name="notes" render={({ field }) => (
                <FormItem>
                  <FormLabel>Notes</FormLabel>
                  <FormControl>
                    <Textarea placeholder="Add any relevant notes..." {...field} />
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
              <DialogClose asChild><Button variant="outline">Cancel</Button></DialogClose>
              <Button type="submit" disabled={!form.formState.isValid}>Create Project</Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}