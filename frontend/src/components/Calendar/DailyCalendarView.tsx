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

interface DailyCalendarViewProps {
    events: CalendarEvent[];
    currentDate: Date;
    onNavigate: (direction: 'prev' | 'next') => void;
    onSelectEvent?: (event: CalendarEvent) => void;
    onGoToToday: () => void;
}

export default function DailyCalendarView({
    events,
    currentDate,
    onNavigate,
    onSelectEvent,
    onGoToToday
}: DailyCalendarViewProps) {

    const getEventsForDay = (date: Date) => {
        return events.filter(calEvent => {
            const eventDate = new Date(calEvent.start);
            return eventDate.getDate() === date.getDate() &&
                eventDate.getMonth() === date.getMonth() &&
                eventDate.getFullYear() === date.getFullYear();
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

    const dayEvents = getEventsForDay(currentDate);

    return (
        <Card>
            <CardHeader>
                <div className="flex items-center justify-between">
                    <CardTitle>
                        Daily View - {currentDate.toLocaleDateString('en-US', {
                            weekday: 'long',
                            year: 'numeric',
                            month: 'long',
                            day: 'numeric'
                        })}
                    </CardTitle>
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
                <div className="space-y-4">
                    {dayEvents.length === 0 ? (
                        <div className="text-center text-muted-foreground py-8">
                            No events scheduled for today.
                        </div>
                    ) : (
                        dayEvents.map(calEvent => (
                            <div
                                key={calEvent.id}
                                className={`p-4 border rounded-lg hover:bg-gray-50 cursor-pointer ${calEvent.status === 'overdue'
                                        ? 'bg-red-50 border-red-300 hover:bg-red-100'
                                        : ''
                                    }`}
                                onClick={() => onSelectEvent?.(calEvent)}
                            >
                                <div className="flex items-start justify-between">
                                    <div className="flex-1">
                                        <div className="flex items-center gap-2 mb-2">
                                            <h3 className={`font-semibold text-lg ${calEvent.status === 'overdue' ? 'text-red-800' : ''
                                                }`}>
                                                {calEvent.type === 'task' ? '📝' : '📁'} {calEvent.title}
                                            </h3>
                                            <Badge
                                                variant={getStatusColor(calEvent.status)}
                                                className={calEvent.status === 'overdue' ? 'animate-pulse' : ''}
                                            >
                                                {calEvent.status === 'overdue' ? '⚠️ ' : ''}{calEvent.status}
                                            </Badge>
                                            <Badge variant="outline">{calEvent.type}</Badge>
                                        </div>

                                        {calEvent.description && (
                                            <p className="text-muted-foreground mb-3">{calEvent.description}</p>
                                        )}

                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                                            <div>
                                                <span className="font-medium">Due:</span>{' '}
                                                {calEvent.start.toLocaleDateString('en-US', {
                                                    weekday: 'long',
                                                    month: 'long',
                                                    day: 'numeric',
                                                    year: 'numeric'
                                                })}
                                            </div>

                                            {calEvent.assigneeEmail && (
                                                <div>
                                                    <span className="font-medium">Assigned to:</span>{' '}
                                                    {calEvent.assigneeEmail}
                                                </div>
                                            )}
                                        </div>

                                        {calEvent.status === 'overdue' && (
                                            <div className="flex items-center gap-1 mt-3 text-red-600 text-sm">
                                                <span>⚠️ This item is overdue</span>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </CardContent>
        </Card>
    );
}