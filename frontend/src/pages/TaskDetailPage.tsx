import { useEffect, useState } from "react";
import { useParams, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
    ArrowLeft,
    Calendar,
    User,
    FileText,
    AlertTriangle,
    Clock,
    FolderKanban,
    Edit,
    Paperclip
} from "lucide-react";
import UpdateTaskDialog from "@/components/TaskManagement/UpdateTaskDialog";
import CommentsSection from "@/components/Comments/CommentsSection";
import { toast } from "sonner";

interface Task {
    id: number;
    title: string;
    description?: string;
    duedate: string;
    status: string;
    priority: number;
    created_at: string;
    notes: string;
    owner_email: string;
    project: string;
    project_id?: number;
    collaborators?: {
        id: number;
        email: string;
        name?: string;
    }[];
    attachments?: {
        id: number;
        filename: string;
    }[];
}


export default function TaskDetailPage() {
    const { taskId } = useParams<{ taskId: string }>();
    const location = useLocation();
    const navigate = useNavigate();
    const [task, setTask] = useState<Task | null>(null);
    const [loading, setLoading] = useState(true);
    const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
    const { userData } = useAuth();
    const token = localStorage.getItem("token");

    const highlightComment = location.state?.highlightComment;

    useEffect(() => {
        const fetchTask = async () => {
            if (!taskId) return;

            setLoading(true);
            try {
                const res = await fetch(`/api/task/get-task/${taskId}`, {
                    headers: { Authorization: `Bearer ${token}` },
                });

                if (!res.ok) throw new Error("Failed to fetch task details.");
                const data = await res.json();
                setTask(data);
            } catch (error) {
                const message = error instanceof Error ? error.message : "Unknown error occurred";
                toast.error(message);
                console.error("Error fetching task:", error);
            } finally {
                setLoading(false);
            }
        };

        fetchTask();
    }, [taskId, token]);

    const handleUpdateSuccess = (updatedTask: Task) => {
        setTask(updatedTask);
        setIsEditDialogOpen(false);
        toast.success("Task updated successfully!");
    };

    const handleBack = () => {
        navigate(-1);
    };

    const getStatusColor = (status: string) => {
        const statusColors: { [key: string]: string } = {
            "Unassigned": "bg-gray-400",
            "Ongoing": "bg-blue-400",
            "Pending Review": "bg-amber-400",
            "Completed": "bg-emerald-400"
        };
        return statusColors[status] || "bg-gray-400";
    };

    const getPriorityColor = (priority: number) => {
        if (priority <= 3) return "bg-green-400";
        if (priority <= 6) return "bg-yellow-400";
        return "bg-red-400";
    };

    const getDaysUntilDue = (dueDate: string) => {
        const today = new Date();
        const due = new Date(dueDate);
        const diffTime = due.getTime() - today.getTime();
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
        return diffDays;
    };

    const getDueDateStatus = (dueDate: string, status: string) => {
        if (status === "Completed") return "completed";

        const daysUntilDue = getDaysUntilDue(dueDate);
        if (daysUntilDue < 0) return "overdue";
        if (daysUntilDue === 0) return "due-today";
        if (daysUntilDue <= 3) return "due-soon";
        return "upcoming";
    };

    const getDueDateMessage = (dueDate: string, status: string) => {
        if (status === "Completed") return "Completed";

        const daysUntilDue = getDaysUntilDue(dueDate);
        if (daysUntilDue < 0) return `${Math.abs(daysUntilDue)} days overdue`;
        if (daysUntilDue === 0) return "Due today";
        if (daysUntilDue === 1) return "Due tomorrow";
        return `Due in ${daysUntilDue} days`;
    };

    const downloadAttachment = async (attachmentId: number, filename: string) => {
        try {
            const token = localStorage.getItem("token");
            const response = await fetch(`/api/attachment/get-attachment/${attachmentId}`, {
                headers: { Authorization: `Bearer ${token}` },
            });

            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = url;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
            } else {
                toast.error("Failed to download attachment");
            }
        } catch (error) {
            console.error("Error downloading attachment:", error);
            toast.error("Error downloading attachment");
        }
    };

    if (loading) {
        return (
            <div className="container mx-auto p-6">
                <div className="text-center">Loading task details...</div>
            </div>
        );
    }

    if (!task) {
        return (
            <div className="container mx-auto p-6">
                <div className="text-center text-red-600">Task not found.</div>
                <Button onClick={handleBack} className="mt-4">
                    <ArrowLeft className="mr-2 h-4 w-4" /> Go Back
                </Button>
            </div>
        );
    }

    const dueDateStatus = getDueDateStatus(task.duedate, task.status);
    const isOverdue = dueDateStatus === "overdue";
    const isOwner = userData.email === task.owner_email;
    const isCollaborator = task.collaborators?.some(c => c.email === userData.email);

    return (
        <div className="container mx-auto p-4 md:p-6 max-w-6xl">
            <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-4">
                    <Button variant="ghost" onClick={handleBack} className="flex items-center gap-2">
                        <ArrowLeft className="h-4 w-4" /> Back
                    </Button>
                    <h1 className="text-3xl font-bold">Task Details</h1>
                </div>

                {(isOwner || isCollaborator) && (
                    <Button
                        onClick={() => setIsEditDialogOpen(true)}
                        className="flex items-center gap-2"
                    >
                        <Edit className="h-4 w-4" /> Edit Task
                    </Button>
                )}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

                <div className="lg:col-span-2 space-y-6">

                    <Card>
                        <CardHeader>
                            <div className="flex justify-between items-start">
                                <div>
                                    <CardTitle className="text-2xl flex items-center gap-3">
                                        {task.title}
                                        <Badge className={`${getStatusColor(task.status)} text-white text-sm`}>
                                            {task.status}
                                        </Badge>
                                        <Badge className={`${getPriorityColor(task.priority)} text-white text-sm`}>
                                            Priority {task.priority}
                                        </Badge>
                                    </CardTitle>
                                    {task.project && (
                                        <div className="flex items-center gap-2 mt-2 text-gray-600">
                                            <FolderKanban size={18} />
                                            <span className="font-medium">Project:</span>
                                            {task.project}
                                        </div>
                                    )}
                                </div>

                                {isOverdue && (
                                    <Badge variant="destructive" className="flex items-center gap-1 animate-pulse">
                                        <AlertTriangle className="h-4 w-4" />
                                        Overdue
                                    </Badge>
                                )}
                            </div>
                        </CardHeader>
                        <CardContent className="space-y-4">

                            {task.description && (
                                <div>
                                    <h3 className="font-semibold text-lg mb-2">Description</h3>
                                    <p className="text-gray-700 whitespace-pre-wrap bg-gray-50 p-3 rounded-md">
                                        {task.description}
                                    </p>
                                </div>
                            )}


                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

                                <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-md">
                                    <Calendar className={`h-5 w-5 ${isOverdue ? "text-red-500" :
                                            dueDateStatus === "due-today" ? "text-orange-500" :
                                                "text-gray-500"
                                        }`} />
                                    <div>
                                        <p className="font-medium">Due Date</p>
                                        <p className={`text-sm ${isOverdue ? "text-red-600 font-semibold" :
                                                dueDateStatus === "due-today" ? "text-orange-600" :
                                                    "text-gray-600"
                                            }`}>
                                            {new Date(task.duedate).toLocaleDateString('en-US', {
                                                weekday: 'long',
                                                year: 'numeric',
                                                month: 'long',
                                                day: 'numeric'
                                            })}
                                        </p>
                                        <p className={`text-xs ${isOverdue ? "text-red-500" :
                                                dueDateStatus === "due-today" ? "text-orange-500" :
                                                    "text-gray-500"
                                            }`}>
                                            {getDueDateMessage(task.duedate, task.status)}
                                        </p>
                                    </div>
                                </div>

                                <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-md">
                                    <User className="h-5 w-5 text-gray-500" />
                                    <div>
                                        <p className="font-medium">Task Owner</p>
                                        <p className="text-sm text-gray-600">{task.owner_email}</p>
                                        {isOwner && (
                                            <p className="text-xs text-blue-500">(You)</p>
                                        )}
                                    </div>
                                </div>


                                <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-md">
                                    <Clock className="h-5 w-5 text-gray-500" />
                                    <div>
                                        <p className="font-medium">Created</p>
                                        <p className="text-sm text-gray-600">
                                            {new Date(task.created_at).toLocaleDateString()}
                                        </p>
                                    </div>
                                </div>

                                <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-md">
                                    <FileText className="h-5 w-5 text-gray-500" />
                                    <div>
                                        <p className="font-medium">Current Status</p>
                                        <Badge className={`${getStatusColor(task.status)} text-white`}>
                                            {task.status}
                                        </Badge>
                                    </div>
                                </div>
                            </div>

                            {task.notes && (
                                <div>
                                    <h3 className="font-semibold text-lg mb-2">Notes</h3>
                                    <p className="text-gray-700 whitespace-pre-wrap bg-gray-50 p-3 rounded-md">
                                        {task.notes}
                                    </p>
                                </div>
                            )}


                            {task.attachments && task.attachments.length > 0 && (
                                <div>
                                    <h3 className="font-semibold text-lg mb-2">Attachments</h3>
                                    <div className="space-y-2">
                                        {task.attachments.map((attachment) => (
                                            <div
                                                key={attachment.id}
                                                className="flex items-center gap-3 p-3 bg-gray-50 rounded-md hover:bg-gray-100 transition-colors cursor-pointer"
                                                onClick={() => downloadAttachment(attachment.id, attachment.filename)}
                                            >
                                                <Paperclip className="h-4 w-4 text-gray-500" />
                                                <span className="text-blue-600 hover:underline flex-1">
                                                    {attachment.filename}
                                                </span>
                                                <Button variant="ghost" size="sm">
                                                    Download
                                                </Button>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </CardContent>
                    </Card>


                    <CommentsSection
                        taskId={task.id}
                        highlightComment={highlightComment}
                    />
                </div>

                <div className="space-y-6">

                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <User className="h-5 w-5" />
                                Collaborators
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            {task.collaborators && task.collaborators.length > 0 ? (
                                <div className="space-y-3">
                                    {task.collaborators.map((collaborator) => (
                                        <div
                                            key={collaborator.id}
                                            className="flex items-center gap-3 p-2 rounded-md hover:bg-gray-50"
                                        >
                                            <div className="w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center">
                                                <span className="text-sm font-medium">
                                                    {collaborator.email.charAt(0).toUpperCase()}
                                                </span>
                                            </div>
                                            <div className="flex-1">
                                                <p className="text-sm font-medium">
                                                    {collaborator.email}
                                                    {collaborator.email === userData.email && (
                                                        <span className="text-blue-500 text-xs ml-2">(You)</span>
                                                    )}
                                                </p>
                                                {collaborator.name && (
                                                    <p className="text-xs text-gray-500">{collaborator.name}</p>
                                                )}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <p className="text-gray-500 text-sm">No collaborators assigned</p>
                            )}
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader>
                            <CardTitle>Quick Actions</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-3">
                            {(isOwner || isCollaborator) && (
                                <Button
                                    onClick={() => setIsEditDialogOpen(true)}
                                    className="w-full flex items-center gap-2"
                                >
                                    <Edit className="h-4 w-4" /> Edit Task
                                </Button>
                            )}

                            {task.project_id && (
                                <Button
                                    variant="outline"
                                    className="w-full flex items-center gap-2"
                                    onClick={() => navigate(`/projects/${task.project_id}`)}
                                >
                                    <FolderKanban className="h-4 w-4" /> View Project
                                </Button>
                            )}

                            <Button
                                variant="outline"
                                className="w-full flex items-center gap-2"
                                onClick={handleBack}
                            >
                                <ArrowLeft className="h-4 w-4" /> Back to List
                            </Button>
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader>
                            <CardTitle>Task Information</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-3 text-sm">
                            <div className="flex justify-between">
                                <span className="text-gray-500">Task ID:</span>
                                <span className="font-medium">#{task.id}</span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-gray-500">Created:</span>
                                <span>{new Date(task.created_at).toLocaleDateString()}</span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-gray-500">Last Updated:</span>
                                <span>{new Date(task.created_at).toLocaleDateString()}</span>
                            </div>
                            <Separator />
                            <div className="flex justify-between">
                                <span className="text-gray-500">Priority:</span>
                                <Badge className={getPriorityColor(task.priority)}>
                                    Level {task.priority}
                                </Badge>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-gray-500">Status:</span>
                                <Badge className={getStatusColor(task.status)}>
                                    {task.status}
                                </Badge>
                            </div>
                        </CardContent>
                    </Card>
                </div>
            </div>

            {userData && task && (
                <UpdateTaskDialog
                    open={isEditDialogOpen}
                    setOpen={setIsEditDialogOpen}
                    task={task}
                    currentUserData={userData}
                    onUpdateSuccess={handleUpdateSuccess}
                />
            )}
        </div>
    );
}