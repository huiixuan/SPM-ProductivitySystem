"use client";

import { useState } from "react";
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

interface SimpleCalendarGridProps {
    events: CalendarEvent[];
    onSelectEvent?: (event: CalendarEvent) => void;
}

export default function SimpleCalendarGrid({ events, onSelectEvent }: SimpleCalendarGridProps) {
    const [currentDate, setCurrentDate] = useState(new Date());

    const getDaysInMonth = (date: Date) => {
        return new Date(date.getFullYear(), date.getMonth() + 1, 0).getDate();
    };

    const getFirstDayOfMonth = (date: Date) => {
        return new Date(date.getFullYear(), date.getMonth(), 1).getDay();
    };

    const navigateMonth = (direction: 'prev' | 'next') => {
        const newDate = new Date(currentDate);
        newDate.setMonth(currentDate.getMonth() + (direction === 'next' ? 1 : -1));
        setCurrentDate(newDate);
    };

    const goToToday = () => {
        setCurrentDate(new Date());
    };

    const daysInMonth = getDaysInMonth(currentDate);
    const firstDay = getFirstDayOfMonth(currentDate);
    const monthName = currentDate.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });

    const getEventsForDay = (day: number) => {
        return events.filter(event => {
            const eventDate = new Date(event.start);
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

    return (
        <Card>
            <CardHeader>
                <div className="flex items-center justify-between">
                    <CardTitle>Calendar View</CardTitle>
                    <div className="flex items-center gap-2">
                        <Button variant="outline" size="sm" onClick={goToToday}>
                            Today
                        </Button>
                        <div className="flex items-center">
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => navigateMonth('prev')}
                            >
                                <ChevronLeft className="h-4 w-4" />
                            </Button>
                            <span className="mx-4 font-semibold min-w-[140px] text-center">
                                {monthName}
                            </span>
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => navigateMonth('next')}
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
                                <div className={`text-sm font-medium mb-1 ${isToday ? 'text-blue-600' : ''
                                    }`}>
                                    {day}
                                </div>
                                <div className="space-y-1">
                                    {dayEvents.map(event => (
                                        <div
                                            key={event.id}
                                            className="text-xs p-1 rounded cursor-pointer hover:bg-gray-100"
                                            onClick={() => onSelectEvent?.(event)}
                                            title={`${event.title} - ${event.status}`}
                                        >
                                            <Badge
                                                variant={getStatusColor(event.status)}
                                                className="w-full justify-start truncate"
                                            >
                                                <span className="mr-1">
                                                    {event.type === 'task' ? '📝' : '📁'}
                                                </span>
                                                {event.title}
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
                        <Badge variant="destructive" className="h-3 w-3 p-0" />
                        <span>Overdue</span>
                    </div>
                    <div className="flex items-center gap-1">
                        <Badge variant="default" className="h-3 w-3 p-0" />
                        <span>Ongoing</span>
                    </div>
                    <div className="flex items-center gap-1">
                        <Badge variant="secondary" className="h-3 w-3 p-0" />
                        <span>Completed</span>
                    </div>
                    <div className="flex items-center gap-1">
                        <Badge variant="outline" className="h-3 w-3 p-0" />
                        <span>Upcoming</span>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}