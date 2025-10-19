"use client";

import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Calendar, Clock, User, FileText, AlertTriangle } from "lucide-react";

type CalendarEvent = {
    id: number;
    title: string;
    start: Date;
    end: Date;
    type: 'task' | 'project';
    status: 'completed' | 'ongoing' | 'overdue' | 'upcoming';
    assignee?: string;
    assigneeEmail?: string;
    description?: string;
};

interface EventDetailsModalProps {
    event: CalendarEvent | null;
    isOpen: boolean;
    onClose: () => void;
}

export default function EventDetailsModal({ event, isOpen, onClose }: EventDetailsModalProps) {
    if (!event) return null;

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'overdue': return 'destructive';
            case 'ongoing': return 'default';
            case 'completed': return 'secondary';
            default: return 'outline';
        }
    };

    const getStatusIcon = (status: string) => {
        if (status === 'overdue') return <AlertTriangle className="h-4 w-4 mr-1" />;
        return null;
    };

    return (
        <Dialog open={isOpen} onOpenChange={onClose}>
            <DialogContent className="sm:max-w-md">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        {event.type === 'task' ? '📝' : '📁'} {event.title}
                    </DialogTitle>
                </DialogHeader>

                <div className="space-y-4">
                    <div className="flex items-center gap-2">
                        <Badge variant={getStatusColor(event.status)}>
                            {getStatusIcon(event.status)}
                            {event.status}
                        </Badge>
                        <Badge variant="outline">
                            {event.type}
                        </Badge>
                    </div>

                    <div className="flex items-center gap-2 text-sm">
                        <Calendar className="h-4 w-4 text-muted-foreground" />
                        <span className="font-medium">Due Date:</span>
                        <span>{event.start.toLocaleDateString('en-US', {
                            weekday: 'long',
                            year: 'numeric',
                            month: 'long',
                            day: 'numeric'
                        })}</span>
                    </div>

                    {event.assigneeEmail && (
                        <div className="flex items-center gap-2 text-sm">
                            <User className="h-4 w-4 text-muted-foreground" />
                            <span className="font-medium">Assigned to:</span>
                            <span>{event.assigneeEmail}</span>
                        </div>
                    )}

                    {event.description && (
                        <div className="flex items-start gap-2 text-sm">
                            <FileText className="h-4 w-4 text-muted-foreground mt-0.5" />
                            <div>
                                <span className="font-medium">Description:</span>
                                <p className="mt-1 text-muted-foreground">{event.description}</p>
                            </div>
                        </div>
                    )}

                    <div className="flex items-center gap-2 text-sm">
                        <Clock className="h-4 w-4 text-muted-foreground" />
                        <span className="font-medium">
                            {event.status === 'overdue' ? 'Overdue by:' : 'Due in:'}
                        </span>
                        <span className={event.status === 'overdue' ? 'text-destructive font-semibold' : ''}>
                            {Math.ceil((event.start.getTime() - new Date().getTime()) / (1000 * 60 * 60 * 24))} days
                        </span>
                    </div>
                </div>

                <div className="flex justify-end gap-2 mt-6">
                    <Button variant="outline" onClick={onClose}>
                        Close
                    </Button>
                </div>
            </DialogContent>
        </Dialog>
    );
}