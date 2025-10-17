import { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogClose,
} from "@/components/ui/dialog";
import {
  Command,
  CommandEmpty,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { Check, ChevronsUpDown } from "lucide-react";

interface Task {
  id: number;
  title: string;
}

interface AddExistingTaskDialogProps {
  isOpen: boolean;
  setIsOpen: (open: boolean) => void;
  projectId: number;
  onTaskLinked: () => void;
}

export default function AddExistingTaskDialog({ isOpen, setIsOpen, projectId, onTaskLinked }: AddExistingTaskDialogProps) {
  const [popoverOpen, setPopoverOpen] = useState(false);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [selectedTaskId, setSelectedTaskId] = useState<number | null>(null);
  const token = localStorage.getItem("token");

  // Fetch unassigned tasks whenever the dialog is opened
  useEffect(() => {
    if (isOpen) {
      const fetchUnassignedTasks = async () => {
        try {
          const res = await fetch("/api/task/get-unassigned-tasks", {
            headers: { Authorization: `Bearer ${token}` },
          });
          const data = await res.json();
          setTasks(data);
        } catch (error) {
          toast.error("Failed to fetch unassigned tasks.");
        }
      };
      fetchUnassignedTasks();
    }
  }, [isOpen, token]);

  // Handle the linking process
  const handleLinkTask = async () => {
    if (!selectedTaskId) {
      toast.warning("Please select a task to link.");
      return;
    }
    try {
      const res = await fetch("/api/task/link-task", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ task_id: selectedTaskId, project_id: projectId }),
      });
      const result = await res.json();
      if (result.success) {
        toast.success("Task linked successfully!");
        onTaskLinked(); // Refresh the parent page's task list
        setIsOpen(false);
        setSelectedTaskId(null);
      } else {
        toast.error(`Error: ${result.error}`);
      }
    } catch (error) {
      toast.error("An unexpected error occurred.");
    }
  };

  const selectedTaskTitle = tasks.find(task => task.id === selectedTaskId)?.title || "Select a task...";

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add Existing Task to Project</DialogTitle>
        </DialogHeader>
        <div className="py-4">
          <Popover open={popoverOpen} onOpenChange={setPopoverOpen}>
            <PopoverTrigger asChild>
              <Button variant="outline" role="combobox" aria-expanded={popoverOpen} className="w-full justify-between">
                {selectedTaskTitle}
                <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-[450px] p-0">
              <Command>
                <CommandInput placeholder="Search task..." />
                <CommandList>
                  <CommandEmpty>No unassigned tasks found.</CommandEmpty>
                  {tasks.map((task) => (
                    <CommandItem
                      key={task.id}
                      value={task.title}
                      onSelect={() => {
                        setSelectedTaskId(task.id);
                        setPopoverOpen(false);
                      }}
                    >
                      <Check className={`mr-2 h-4 w-4 ${selectedTaskId === task.id ? "opacity-100" : "opacity-0"}`} />
                      {task.title}
                    </CommandItem>
                  ))}
                </CommandList>
              </Command>
            </PopoverContent>
          </Popover>
        </div>
        <DialogFooter>
          <DialogClose asChild><Button variant="outline">Cancel</Button></DialogClose>
          <Button onClick={handleLinkTask} disabled={!selectedTaskId}>Link Task</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}