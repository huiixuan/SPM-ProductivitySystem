import { useState } from "react";
import { z } from "zod";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Select, SelectTrigger, SelectContent, SelectItem, SelectValue } from "@/components/ui/select";

const schema = z.object({
  name: z.string().min(1, "Name is required"),
  description: z.string().optional(),
  deadline: z.string().optional(),
  status: z.enum(["Not Started", "In Progress", "Completed"]).default("Not Started"),
  collaborators: z.string().optional(),
  attachment: z
    .any()
    .refine((f) => !f || (f instanceof File && f.type === "application/pdf"), { message: "Only PDF allowed" })
    .optional(),
});

type Props = {
  disabled?: boolean;
  onCreated?: () => void;
};

export default function NewProjectButton({ disabled, onCreated }: Props) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [deadline, setDeadline] = useState("");
  const [status, setStatus] = useState<"Not Started" | "In Progress" | "Completed">("Not Started");
  const [collaborators, setCollaborators] = useState("");
  const [attachment, setAttachment] = useState<File | null>(null);

  const reset = () => {
    setName(""); setDescription(""); setDeadline("");
    setStatus("Not Started"); setCollaborators(""); setAttachment(null);
  };

  const submit = async () => {
    const parsed = schema.safeParse({ name, description, deadline, status, collaborators, attachment });
    if (!parsed.success) {
      toast.error(parsed.error.issues[0].message);
      return;
    }
    const token = localStorage.getItem("token");
    if (!token) {
      toast.error("Not signed in. Please log in again.");
      return;
    }

    const fd = new FormData();
    fd.append("name", name);
    if (description) fd.append("description", description);
    if (deadline) fd.append("deadline", deadline);
    fd.append("status", status);
    if (collaborators) fd.append("collaborators", collaborators);
    if (attachment) fd.append("attachment", attachment);

    try {
      setLoading(true);
      const res = await fetch("http://127.0.0.1:5000/api/project", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: fd,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to create project");

      toast.success(`Project created: #${data.project.id} ${data.project.name}`);
      reset();
      setOpen(false);
      onCreated?.();
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(v) => !disabled && setOpen(v)}>
      <DialogTrigger asChild>
        <Button variant="outline" disabled={disabled}>
          + New Project
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Add New Project</DialogTitle>
        </DialogHeader>

        <Card>
          <CardContent className="grid gap-4 pt-6">
            <div>
              <Label>Name *</Label>
              <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Project Alpha" />
            </div>

            <div>
              <Label>Description</Label>
              <Textarea rows={3} value={description} onChange={(e) => setDescription(e.target.value)} />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <Label>Deadline</Label>
                <Input type="date" value={deadline} onChange={(e) => setDeadline(e.target.value)} />
              </div>

              <div>
                <Label>Status</Label>
                <Select value={status} onValueChange={(v) => setStatus(v as any)}>
                  <SelectTrigger><SelectValue placeholder="Select status" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Not Started">Not Started</SelectItem>
                    <SelectItem value="In Progress">In Progress</SelectItem>
                    <SelectItem value="Completed">Completed</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label>Collaborators (emails, comma-separated)</Label>
                <Input
                    value={collaborators}
                    onChange={(e) => setCollaborators(e.target.value)}
                    placeholder="alice@example.com, bob@example.com"
                />
                </div>
            </div>
            <div>
              <Label>Attachment (PDF)</Label>
              <Input
                type="file"
                accept="application/pdf"
                onChange={(e) => setAttachment(e.target.files?.[0] || null)}
              />
            </div>
          </CardContent>
        </Card>

        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)} disabled={loading}>Cancel</Button>
          <Button onClick={submit} disabled={loading}>
            {loading ? "Creating..." : "Create Project"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
