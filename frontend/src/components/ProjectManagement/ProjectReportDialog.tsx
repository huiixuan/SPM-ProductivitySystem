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
import { toast } from "sonner";
import { Download } from "lucide-react";
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";

interface ReportData {
  [key: string]: number; // e.g., "Ongoing": 1
}

interface ProjectReportDialogProps {
  isOpen: boolean;
  setIsOpen: (open: boolean) => void;
  projectId: number;
  projectName: string;
}

export default function ProjectReportDialog({ isOpen, setIsOpen, projectId, projectName }: ProjectReportDialogProps) {
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
          const res = await fetch(`/api/project/get-report-data/${projectId}`, {
            headers: { Authorization: `Bearer ${token}` },
          });
          if (res.status === 403) throw new Error("You do not have permission to view this report.");
          if (!res.ok) throw new Error("Failed to fetch report data.");
          
          const data: ReportData = await res.json();
          setReportData(data);
        } catch (err: any) {
          setError(err.message);
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

    const totalTasks = Object.values(reportData).reduce((a, b) => a + b, 0);

    const tableData = Object.entries(reportData).map(([status, count]) => [
      status,
      count
    ]);

    autoTable(doc, {
      startY: 35,
      head: [["Status Category", "Number of Tasks"]],
      body: tableData,
      theme: "striped",
      headStyles: { fillColor: [41, 128, 185] },
      foot: [["Total Tasks", totalTasks]],
      footStyles: { fontStyle: 'bold', fillColor: [230, 230, 230], textColor: [0, 0, 0] }
    });
    
    doc.save(`project_report_${projectName.replace(/\s+/g, '_')}.pdf`);
    toast.success("Report exported successfully!");
  };

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Project Report: {projectName}</DialogTitle>
          <DialogDescription>
            A summary of all tasks in this project by their current status.
          </DialogDescription>
        </DialogHeader>
        <div className="py-4">
          {loading && <p>Loading report...</p>}
          {error && <p className="text-red-600">{error}</p>}
          
          {/* This is the block that renders the main content */}
          {reportData && (
            <div>
              <p className="text-sm text-gray-500 mb-4">
                Report generated: {generationTime}
              </p>
              
              {/* --- THIS IS THE LIST THAT ISN'T SHOWING --- */}
              <ul className="space-y-2">
                {Object.entries(reportData).map(([status, count]) => (
                  <li key={status} className="flex justify-between">
                    <span>{status}:</span> 
                    <strong>{count}</strong>
                  </li>
                ))}
              </ul>
              {/* --- END OF LIST --- */}
              
              <hr className="my-4" />
              
              {/* This line is working, which proves reportData is valid */}
              <div className="flex justify-between font-bold text-lg">
                <span>Total Tasks:</span>
                <span>{Object.values(reportData).reduce((a, b) => a + b, 0)}</span>
              </div>
            </div>
          )}
          {/* --- END OF CONTENT BLOCK --- */}

        </div>
        <DialogFooter>
          <DialogClose asChild><Button variant="outline">Close</Button></DialogClose>
          <Button onClick={handleExportPDF} disabled={loading || !reportData}>
            <Download className="mr-2 h-4 w-4" /> Export to PDF
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}