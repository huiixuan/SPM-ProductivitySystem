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

interface WeeklyCalendarViewProps {
    events: CalendarEvent[];
    currentDate: Date;
    onNavigate: (direction: 'prev' | 'next') => void;
    onSelectEvent?: (event: CalendarEvent) => void;
    onGoToToday: () => void;
}

export default function WeeklyCalendarView({
    events,
    currentDate,
    onNavigate,
    onSelectEvent,
    onGoToToday
}: WeeklyCalendarViewProps) {

    const getWeekDates = (date: Date) => {
        const startOfWeek = new Date(date);
        const day = startOfWeek.getDay();
        const diff = startOfWeek.getDate() - day;
        startOfWeek.setDate(diff);

        const weekDates = [];
        for (let i = 0; i < 7; i++) {
            const weekDay = new Date(startOfWeek);
            weekDay.setDate(startOfWeek.getDate() + i);
            weekDates.push(weekDay);
        }
        return weekDates;
    };

    const getEventsForDay = (day: Date) => {
        return events.filter(calEvent => {
            const eventDate = new Date(calEvent.start);
            return eventDate.getDate() === day.getDate() &&
                eventDate.getMonth() === day.getMonth() &&
                eventDate.getFullYear() === day.getFullYear();
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

    const weekDates = getWeekDates(currentDate);
    const weekRange = `${weekDates[0].toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} - ${weekDates[6].toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}`;

    return (
        <Card>
            <CardHeader>
                <div className="flex items-center justify-between">
                    <CardTitle>Weekly View - {weekRange}</CardTitle>
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
                <div className="grid grid-cols-7 gap-2">
                    {weekDates.map((date, index) => {
                        const dayEvents = getEventsForDay(date);
                        const isToday = new Date().toDateString() === date.toDateString();

                        return (
                            <div key={index} className="min-h-32">
                                <div className={`text-center font-medium p-2 border-b ${isToday ? 'bg-blue-50 text-blue-600' : ''}`}>
                                    <div className="text-sm">{date.toLocaleDateString('en-US', { weekday: 'short' })}</div>
                                    <div className={`text-lg ${isToday ? 'font-bold' : ''}`}>
                                        {date.getDate()}
                                    </div>
                                </div>
                                <div className="p-1 space-y-1 max-h-48 overflow-y-auto">
                                    {dayEvents.map(calEvent => (
                                        <div
                                            key={calEvent.id}
                                            className="text-xs p-1 rounded cursor-pointer hover:bg-gray-100 border-l-4"
                                            style={{
                                                borderLeftColor: getStatusBorderColor(calEvent.status)
                                            }}
                                            onClick={() => onSelectEvent?.(calEvent)}
                                            title={`${calEvent.title} - ${calEvent.status}`}
                                        >
                                            <div className="font-medium truncate">
                                                {calEvent.type === 'task' ? '📝' : '📁'} {calEvent.title}
                                            </div>
                                            <Badge variant={getStatusColor(calEvent.status)} className="mt-1 text-xs">
                                                {calEvent.status}
                                            </Badge>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        );
                    })}
                </div>
            </CardContent>
        </Card>
    );
}