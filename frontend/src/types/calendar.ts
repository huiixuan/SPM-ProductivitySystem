export type CalendarView = 'day' | 'week' | 'month';

export interface CalendarEvent {
    id: number;
    title: string;
    description?: string;
    start: Date;
    end: Date;
    type: 'task' | 'project';
    status: 'completed' | 'ongoing' | 'overdue' | 'upcoming';
    assignee?: string;
    projectId?: number;
    taskId?: number;
}

export interface TeamMember {
    id: number;
    name: string;
    email: string;
    role: string;
    workload: number;
}