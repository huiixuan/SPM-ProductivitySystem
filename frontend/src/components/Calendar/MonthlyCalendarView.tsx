"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ChevronLeft, ChevronRight } from "lucide-react";

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

interface MonthlyCalendarViewProps {
    events: CalendarEvent[];
    currentDate: Date;
    onNavigate: (direction: 'prev' | 'next') => void;
    onSelectEvent?: (event: CalendarEvent) => void;
    onGoToToday: () => void;
}

export default function MonthlyCalendarView({
    events,
    currentDate,
    onNavigate,
    onSelectEvent,
    onGoToToday
}: MonthlyCalendarViewProps) {

    const getDaysInMonth = (date: Date) => {
        return new Date(date.getFullYear(), date.getMonth() + 1, 0).getDate();
    };

    const getFirstDayOfMonth = (date: Date) => {
        return new Date(date.getFullYear(), date.getMonth(), 1).getDay();
    };

    const getEventsForDay = (day: number) => {
        return events.filter(calEvent => {
            const eventDate = new Date(calEvent.start);
            return eventDate.getDate() === day &&
                eventDate.getMonth() === currentDate.getMonth() &&
                eventDate.getFullYear() === currentDate.getFullYear();
        });
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'overdue': return 'destructive';
            case 'ongoing': return 'default';
            case 'completed': return 'secondary';
            default: return 'outline';
        }
    };

    const getStatusBorderColor = (status: string) => {
        switch (status) {
            case 'overdue': return '#ef4444';
            case 'ongoing': return '#3b82f6';
            case 'completed': return '#6b7280';
            default: return '#10b981';
        }
    };

    const daysInMonth = getDaysInMonth(currentDate);
    const firstDay = getFirstDayOfMonth(currentDate);
    const monthName = currentDate.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });

    return (
        <Card>
            <CardHeader>
                <div className="flex items-center justify-between">
                    <CardTitle>Monthly View - {monthName}</CardTitle>
                    <div className="flex items-center gap-2">
                        <Button variant="outline" size="sm" onClick={onGoToToday}>
                            Today
                        </Button>
                        <div className="flex items-center">
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => onNavigate('prev')}
                            >
                                <ChevronLeft className="h-4 w-4" />
                            </Button>
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => onNavigate('next')}
                            >
                                <ChevronRight className="h-4 w-4" />
                            </Button>
                        </div>
                    </div>
                </div>
            </CardHeader>
            <CardContent>
                <div className="grid grid-cols-7 gap-1">
                    {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(day => (
                        <div key={day} className="text-center font-medium text-sm py-2 border-b">
                            {day}
                        </div>
                    ))}
                    {Array.from({ length: firstDay }).map((_, index) => (
                        <div key={`empty-${index}`} className="h-24 border rounded bg-gray-50"></div>
                    ))}

                    {Array.from({ length: daysInMonth }).map((_, index) => {
                        const day = index + 1;
                        const dayEvents = getEventsForDay(day);
                        const isToday = new Date().getDate() === day &&
                            new Date().getMonth() === currentDate.getMonth() &&
                            new Date().getFullYear() === currentDate.getFullYear();

                        return (
                            <div
                                key={day}
                                className={`h-24 border rounded p-1 overflow-y-auto ${isToday ? 'bg-blue-50 border-blue-200' : 'bg-white'
                                    }`}
                            >
                                <div className={`text-sm font-medium mb-1 ${isToday ? 'text-blue-600' : ''}`}>
                                    {day}
                                </div>
                                <div className="space-y-1">
                                    {dayEvents.map(calEvent => (
                                        <div
                                            key={calEvent.id}
                                            className={`text-xs p-1 rounded cursor-pointer hover:bg-gray-100 border-l-4 ${calEvent.status === 'overdue' ? 'bg-red-50 border-red-300' : ''
                                                }`}
                                            style={{
                                                borderLeftColor: getStatusBorderColor(calEvent.status)
                                            }}
                                            onClick={() => onSelectEvent?.(calEvent)}
                                            title={`${calEvent.title} - ${calEvent.status}`}
                                        >
                                            <div className={`font-medium truncate ${calEvent.status === 'overdue' ? 'text-red-800 font-bold' : ''
                                                }`}>
                                                {calEvent.type === 'task' ? '📝' : '📁'} {calEvent.title}
                                            </div>
                                            <Badge
                                                variant={getStatusColor(calEvent.status)}
                                                className={`mt-1 text-xs ${calEvent.status === 'overdue' ? 'animate-pulse' : ''
                                                    }`}
                                            >
                                                {calEvent.status === 'overdue' ? '⚠️ ' : ''}{calEvent.status}
                                            </Badge>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        );
                    })}
                </div>

                <div className="mt-4 flex flex-wrap gap-4 text-xs">
                    <div className="flex items-center gap-1">
                        <div className="h-3 w-3 bg-destructive rounded"></div>
                        <span>Overdue</span>
                    </div>
                    <div className="flex items-center gap-1">
                        <div className="h-3 w-3 bg-blue-500 rounded"></div>
                        <span>Ongoing</span>
                    </div>
                    <div className="flex items-center gap-1">
                        <div className="h-3 w-3 bg-gray-400 rounded"></div>
                        <span>Completed</span>
                    </div>
                    <div className="flex items-center gap-1">
                        <div className="h-3 w-3 bg-green-500 rounded"></div>
                        <span>Upcoming</span>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}