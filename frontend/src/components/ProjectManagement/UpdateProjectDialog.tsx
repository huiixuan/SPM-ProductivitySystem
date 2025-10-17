import { useEffect } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import DatePicker from "@/components/TaskManagement/DatePicker";
import EmailCombobox from "@/components/TaskManagement/EmailCombobox";
import UploadAttachments from "@/components/TaskManagement/UploadAttachments";
import { Form, FormControl, FormField, FormItem, FormLabel } from "@/components/ui/form";
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

// Define attachment and form schemas
const attachmentSchema = z.union([
  z.instanceof(File),
  z.object({ id: z.number(), filename: z.string() })
]);

// 1. Add 'notes' to the form schema
const formSchema = z.object({
  name: z.string().min(1, "Project name is required."),
  description: z.string().optional(),
  deadline: z.date().optional(),
  status: z.string().min(1, "Select a status."),
  owner: z.string().min(1, "Select an owner."),
  collaborators: z.array(z.string()).optional(),
  notes: z.string().optional(), // <-- ADDED THIS
  attachments: z.array(attachmentSchema).optional(),
});

// Component props interface
interface UpdateProjectDialogProps {
  isOpen: boolean;
  setIsOpen: (open: boolean) => void;
  project: Project;
  currentUserData: UserData;
  onUpdateSuccess: (updatedProject: Project) => void;
}

// 2. Add 'notes' to the Project interface
interface Project {
  id: number;
  name: string;
  description?: string;
  notes?: string; // <-- ADDED THIS
  deadline: string;
  status: string;
  owner_email: string;
  collaborators?: { id: number; email: string }[];
  attachments?: { id: number; filename: string }[];
}

interface UserData {
  role: string;
  email: string;
}

export default function UpdateProjectDialog({ isOpen, setIsOpen, project, currentUserData, onUpdateSuccess }: UpdateProjectDialogProps) {
  const token = localStorage.getItem("token");

  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
  });
  
  useEffect(() => {
    if (project) {
        form.reset({
            name: project.name,
            description: project.description,
            deadline: project.deadline ? new Date(project.deadline) : undefined,
            status: project.status,
            owner: project.owner_email,
            collaborators: project.collaborators?.map(c => c.email) || [],
            notes: project.notes || "",
            attachments: project.attachments || [],
        });
    }
  }, [project, form]);

  async function onSubmit(values: z.infer<typeof formSchema>) {
    const formData = new FormData();

    formData.append("name", values.name);
    formData.append("description", values.description || "");
    if (values.deadline) formData.append("deadline", values.deadline.toISOString());
    formData.append("status", values.status);
    formData.append("owner", values.owner);
    formData.append("notes", values.notes || ""); 
    
    values.collaborators?.forEach(c => formData.append("collaborators", c));

    const existingAttachments = values.attachments?.filter(att => !(att instanceof File)) || [];
    formData.append("existing_attachments", JSON.stringify(existingAttachments));
    
    const newAttachments = values.attachments?.filter(att => att instanceof File) || [];
    newAttachments.forEach(file => formData.append("attachments", file as File));

    try {
      const res = await fetch(`/api/project/update-project/${project.id}`, {
        method: "PUT",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });

      const result = await res.json();
      if (result.success) {
        onUpdateSuccess(result.project);
      } else {
        toast.error(`Update failed: ${result.error}`);
      }
    } catch (error) {
      toast.error("An unexpected error occurred.");
    }
  }

  const isOwner = currentUserData.email === project.owner_email;
  const isManagerOrDirector = currentUserData.role === 'manager' || currentUserData.role === 'director';
  const canEdit = isOwner || isManagerOrDirector;

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>Update Project: {project.name}</DialogTitle>
          <DialogDescription>
            Modify the project details below.
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <div className="grid gap-4 py-4 max-h-[70vh] overflow-y-auto pr-2">
              <FormField control={form.control} name="name" render={({ field }) => (
                <FormItem>
                  <FormLabel>Project Name</FormLabel>
                  <FormControl><Input {...field} disabled={!canEdit} /></FormControl>
                </FormItem>
              )} />
              
               <FormField control={form.control} name="description" render={({ field }) => (
                <FormItem>
                  <FormLabel>Description</FormLabel>
                  <FormControl><Textarea {...field} disabled={!canEdit} /></FormControl>
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
                  <Select onValueChange={field.onChange} defaultValue={field.value} disabled={!canEdit}>
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
                    <EmailCombobox value={field.value} onChange={field.onChange} currentUserData={currentUserData} />
                  </FormControl>
                </FormItem>
              )} />

              <FormField control={form.control} name="collaborators" render={({ field }) => (
                <FormItem>
                  <FormLabel>Collaborators</FormLabel>
                  <FormControl>
                    <EmailCombobox value={field.value as string[]} onChange={field.onChange} currentUserData={currentUserData} multiple />
                  </FormControl>
                </FormItem>
              )} />

              {/* 5. Add the Notes textarea field to the form */}
              <FormField control={form.control} name="notes" render={({ field }) => (
                <FormItem>
                  <FormLabel>Notes</FormLabel>
                  <FormControl>
                    <Textarea placeholder="Add any relevant notes..." {...field} disabled={!canEdit} />
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
              <Button type="submit" disabled={!form.formState.isValid || !canEdit}>Update Project</Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}