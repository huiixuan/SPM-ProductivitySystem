"use client";

import * as React from "react";
import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

type Project = {
  id: number;
  name: string;
  description?: string;
  status?: string;
  deadline?: string | null;
  created_at?: string;
};

export default function ProjectList({ refreshKey }: { refreshKey: number }) {
  const [projects, setProjects] = useState<Project[] | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) return;

    fetch("http://127.0.0.1:5000/api/project", {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then((data) => setProjects(data.projects || []))
      .catch(() => setProjects([]));
  }, [refreshKey]);

  return (
    <Card className="mt-6">
      <CardHeader>
        <CardTitle>Projects</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {projects === null ? (
          <div className="text-sm text-muted-foreground">Loading…</div>
        ) : projects.length === 0 ? (
          <div className="text-sm text-muted-foreground">No current projects yet.</div>
        ) : (
          projects.map((p) => (
            <div key={p.id} className="flex items-center justify-between rounded-lg border p-3">
              <div>
                <div className="font-medium">{p.name}</div>
                {p.description ? (
                  <div className="text-sm text-muted-foreground line-clamp-1">
                    {p.description}
                  </div>
                ) : null}
              </div>
              <div className="flex items-center gap-2">
                {p.status ? <Badge>{p.status}</Badge> : null}
                {p.deadline ? (
                  <span className="text-xs text-muted-foreground">
                    {new Date(p.deadline).toLocaleDateString()}
                  </span>
                ) : null}
              </div>
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}
