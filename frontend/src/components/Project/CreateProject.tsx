import { z } from "zod";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Select, SelectTrigger, SelectContent, SelectItem, SelectValue } from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner"; 

// validation schema
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

type Role = "staff" | "hr" | "manager" | "director";

export default function CreateProject() {
  const [role, setRole] = useState<Role | null>(null);
  const [loading, setLoading] = useState(false);

  // form state
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [deadline, setDeadline] = useState("");
  const [status, setStatus] = useState<"Not Started" | "In Progress" | "Completed">("Not Started");
  const [collaborators, setCollaborators] = useState("");
  const [attachment, setAttachment] = useState<File | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) return;

    fetch("http://127.0.0.1:5000/auth/dashboard", {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then((data) => {
        const r = (data.dashboard || "").toLowerCase() as Role;
        setRole(r);
      })
      .catch(() => setRole(null));
  }, []);

  const canCreate = role === "manager" || role === "director";

  const onSubmit = async () => {
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
      setName(""); setDescription(""); setDeadline(""); setStatus("Not Started"); setCollaborators(""); setAttachment(null);
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setLoading(false);
    }
  };

  if (role && !canCreate) {
    return (
      <Card className="mt-6">
        <CardHeader>
          <CardTitle>Create Project</CardTitle>
        </CardHeader>
        <CardContent>
          <Badge variant="destructive">Access denied</Badge>
          <p className="text-sm mt-2">Only Manager and Director can create projects.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="mt-6">
      <CardHeader>
        <CardTitle>
          Create Project {role ? <Badge className="ml-2">{role}</Badge> : null}
        </CardTitle>
      </CardHeader>
      <CardContent className="grid gap-4">
        <div>
          <Label htmlFor="name">Name *</Label>
          <Input id="name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Project Alpha" />
        </div>

        <div>
          <Label htmlFor="description">Description</Label>
          <Textarea id="description" rows={4} value={description} onChange={(e) => setDescription(e.target.value)} />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <Label htmlFor="deadline">Deadline</Label>
            <Input id="deadline" type="date" value={deadline} onChange={(e) => setDeadline(e.target.value)} />
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
            <Label htmlFor="collaborators">Collaborators (IDs, comma-separated)</Label>
            <Input
              id="collaborators"
              value={collaborators}
              onChange={(e) => setCollaborators(e.target.value)}
              placeholder="3, 8, 12"
            />
          </div>
        </div>

        <div>
          <Label htmlFor="attachment">Attachment (PDF)</Label>
          <Input
            id="attachment"
            type="file"
            accept="application/pdf"
            onChange={(e) => setAttachment(e.target.files?.[0] || null)}
          />
        </div>

        <Button onClick={onSubmit} disabled={loading || !canCreate}>
          {loading ? "Creating..." : "Create Project"}
        </Button>
      </CardContent>
    </Card>
  );
}
