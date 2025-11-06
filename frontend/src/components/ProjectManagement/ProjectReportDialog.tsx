import { useState, useEffect } from "react";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogFooter,
    DialogClose,
    DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { toast } from "sonner";
import { Download, CalendarDays } from "lucide-react"; // Removed User icon
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";

interface TaskScheduleItem {
  title: string;
  duedate: string | null; 
  status: string;
}
interface ReportData {
  task_counts: { [key: string]: number };
  task_schedule: TaskScheduleItem[];
}

interface ProjectReportDialogProps {
    isOpen: boolean;
    setIsOpen: (open: boolean) => void;
    projectId: number;
    projectName: string;
    projectStatus: string;   
}

export default function ProjectReportDialog({
    isOpen,
    setIsOpen,
    projectId,
    projectName,
    projectStatus    
}: ProjectReportDialogProps) {
    const [reportData, setReportData] = useState<ReportData | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const token = localStorage.getItem("token");
    const [generationTime, setGenerationTime] = useState("");

    useEffect(() => {
        if (isOpen) {
            const fetchReportData = async () => {
                setLoading(true);
                setError(null);
                setReportData(null);
                setGenerationTime(new Date().toLocaleString());
                try {
                    const res = await fetch(
                        `/api/project/get-report-data/${projectId}`,
                        {
                            headers: { Authorization: `Bearer ${token}` },
                        }
                    );
                    if (res.status === 403)
                        throw new Error(
                            "You do not have permission to view this report."
                        );
                    if (!res.ok)
                        throw new Error("Failed to fetch report data.");

                    const data: ReportData = await res.json();
                    setReportData(data);
                } catch (err) {
                    setError(
                        err instanceof Error ? err.message : "An error occurred"
                    );
                } finally {
                    setLoading(false);
                }
            };
            fetchReportData();
        }
    }, [isOpen, projectId, token]);

    const handleExportPDF = () => {
        if (!reportData) return;
        const doc = new jsPDF();
        
        doc.text(`Project Report: ${projectName}`, 14, 20);
        doc.setFontSize(12);
        doc.text(`Generated on: ${generationTime}`, 14, 28);

        doc.text(`Overall Status: ${projectStatus}`, 14, 36);
        
        doc.setFontSize(14);
        doc.text("Task Breakdown", 14, 48); // Moved up
        const countsTableData = Object.entries(reportData.task_counts).map(([status, count]) => [
          status,
          count
        ]);
        const totalTasks = Object.values(reportData.task_counts).reduce((a, b) => a + b, 0);

        autoTable(doc, {
          startY: 52, // Moved up
          head: [["Status", "Count"]],
          body: countsTableData,
          theme: "striped",
          headStyles: { fillColor: [41, 128, 185] },
          foot: [["Total Tasks", totalTasks]],
          footStyles: { fontStyle: 'bold', fillColor: [230, 230, 230], textColor: [0, 0, 0] }
        });

        const firstTableEnd = (doc as any).lastAutoTable.finalY;
        doc.setFontSize(14);
        doc.text("Task Schedule", 14, firstTableEnd + 10);
        
        const scheduleTableData = reportData.task_schedule.map(task => [
          task.title,
          task.duedate ? new Date(task.duedate).toLocaleDateString() : 'N/A',
          task.status,
        ]);

        autoTable(doc, {
          startY: firstTableEnd + 14,
          head: [["Task", "Deadline", "Status"]], 
          body: scheduleTableData,
          theme: "striped",
          headStyles: { fillColor: [41, 128, 185] },
        });
        
        doc.save(`project_report_${projectName.replace(/\s+/g, "_")}.pdf`);
        toast.success("Report exported successfully!");
    };

    const totalTasks = reportData ? Object.values(reportData.task_counts).reduce((a, b) => a + b, 0) : 0;

    return (
        <Dialog open={isOpen} onOpenChange={setIsOpen}>
            <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>Project Report: {projectName}</DialogTitle>
                    <DialogDescription>
                        A summary of the project schedule and task breakdown.
                    </DialogDescription>
                </DialogHeader>
                
                <div>
                    <div className="flex justify-between items-center my-4">
                      <h3 className="text-lg font-semibold">Task Status</h3>
                      <div>
                        <span className="text-sm font-semibold text-gray-600 mr-2">Overall Status:</span>
                        <Badge className="w-fit">{projectStatus}</Badge>
                      </div>
                    </div>
                    <p className="text-sm text-gray-500 mb-4">
                        Report generated: {generationTime}
                    </p>
                    
                    {loading && <p>Loading task breakdown...</p>}
                    {error && <p className="text-red-600">{error}</p>}
                    
                    {reportData && (
                        <div className="space-y-6">
                            <div>
                                <ul className="grid grid-cols-2 gap-x-4 gap-y-2">
                                    {/* This will now include "Projected" in the list */}
                                    {Object.keys(reportData.task_counts).map((status) => (
                                        <li key={status} className="flex justify-between items-center text-sm">
                                            <span className="text-gray-700">{status}:</span> 
                                            <strong className="font-semibold">{reportData.task_counts[status]}</strong>
                                        </li>
                                    ))}
                                </ul>
                                <hr className="my-3" />
                                <div className="flex justify-between font-bold text-base">
                                    <span>Total Tasks:</span>
                                    <span>{totalTasks}</span>
                                </div>
                            </div>
                            
                            <Separator />

                            <div>
                                <h4 className="text-base font-semibold mb-3">Task Schedule</h4>
                                {reportData.task_schedule.length > 0 ? (
                                    <ul className="space-y-3 max-h-64 overflow-y-auto pr-2">
                                        {reportData.task_schedule.map((task, index) => (
                                            <li key={index} className="text-sm p-3 bg-gray-50 rounded-md border">
                                                <div className="flex justify-between items-center mb-1">
                                                    <span className="font-medium text-gray-900">{task.title}</span>
                                                    {/* --- THIS IS THE FIX ---
                                                        Cleaned up badge logic for "Projected" */}
                                                    <Badge 
                                                        variant={task.status === 'Completed' ? 'secondary' : (task.status === 'Projected' ? 'outline' : 'default')}
                                                        className={task.status === 'Projected' ? 'border-blue-500 text-blue-600' : ''}
                                                    >
                                                        {task.status}
                                                    </Badge>
                                                </div>
                                                <div className="flex justify-start text-gray-600">
                                                    <span className="flex items-center gap-1.5">
                                                        <CalendarDays className="h-3.5 w-3.5" />
                                                        {task.duedate ? new Date(task.duedate).toLocaleDateString() : 'No Deadline'}
                                                    </span>
                                                </div>
                                            </li>
                                        ))}
                                    </ul>
                                ) : (
                                    <p className="text-sm text-gray-500">No tasks found for this project.</p>
                                )}
                            </div>
                        </div>
                    )}
                </div>

                <DialogFooter className="mt-4">
                    <DialogClose asChild>
                        <Button variant="outline">Close</Button>
                    </DialogClose>
                    <Button
                        onClick={handleExportPDF}
                        disabled={loading || !reportData}
                    >
                        <Download className="mr-2 h-4 w-4" /> Export to PDF
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}