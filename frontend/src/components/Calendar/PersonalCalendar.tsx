"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Calendar, CalendarEvent, CalendarView } from "@/types/calendar";

export default function PersonalCalendar() {
    const [view, setView] = useState<CalendarView>('month');
    const [currentDate, setCurrentDate] = useState(new Date());
    const [events, setEvents] = useState<CalendarEvent[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchPersonalEvents();
    }, [currentDate]);

    const fetchPersonalEvents = async () => {
        try {
            const token = localStorage.getItem("token");
            const response = await fetch("http://127.0.0.1:5000/api/calendar/personal", {
                headers: { Authorization: `Bearer ${token}` },
            });

            if (response.ok) {
                const data = await response.json();
                setEvents(data.events.map((event: any) => ({
                    ...event,
                    start: new Date(event.start),
                    end: new Date(event.end),
                })));
            }
        } catch (error) {
            console.error("Failed to fetch events:", error);
        } finally {
            setLoading(false);
        }
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'overdue': return 'destructive';
            case 'ongoing': return 'default';
            case 'completed': return 'secondary';
            default: return 'outline';
        }
    };

    const navigateDate = (direction: 'prev' | 'next') => {
        const newDate = new Date(currentDate);
        if (view === 'month') {
            newDate.setMonth(newDate.getMonth() + (direction === 'next' ? 1 : -1));
        } else if (view === 'week') {
            newDate.setDate(newDate.getDate() + (direction === 'next' ? 7 : -7));
        } else {
            newDate.setDate(newDate.getDate() + (direction === 'next' ? 1 : -1));
        }
        setCurrentDate(newDate);
    };

    if (loading) {
        return <div>Loading calendar...</div>;
    }

    return (
        <Card>
            <CardHeader>
                <div className="flex justify-between items-center">
                    <CardTitle>My Schedule</CardTitle>
                    <div className="flex gap-2">
                        <Button
                            variant={view === 'day' ? 'default' : 'outline'}
                            size="sm"
                            onClick={() => setView('day')}
                        >
                            Day
                        </Button>
                        <Button
                            variant={view === 'week' ? 'default' : 'outline'}
                            size="sm"
                            onClick={() => setView('week')}
                        >
                            Week
                        </Button>
                        <Button
                            variant={view === 'month' ? 'default' : 'outline'}
                            size="sm"
                            onClick={() => setView('month')}
                        >
                            Month
                        </Button>
                    </div>
                </div>

                <div className="flex justify-between items-center">
                    <Button variant="outline" onClick={() => navigateDate('prev')}>
                        Previous
                    </Button>
                    <span className="font-semibold">
                        {currentDate.toLocaleDateString('en-US', {
                            month: 'long',
                            year: 'numeric',
                            ...(view === 'week' && { week: 'numeric' })
                        })}
                    </span>
                    <Button variant="outline" onClick={() => navigateDate('next')}>
                        Next
                    </Button>
                </div>
            </CardHeader>

            <CardContent>
                <div className="space-y-4">
                    {events.map((event) => (
                        <div key={event.id} className="flex items-center justify-between p-3 border rounded-lg">
                            <div className="flex-1">
                                <div className="flex items-center gap-2">
                                    <h4 className="font-medium">{event.title}</h4>
                                    <Badge variant={getStatusColor(event.status)}>
                                        {event.status}
                                    </Badge>
                                </div>
                                <p className="text-sm text-muted-foreground">
                                    {event.start.toLocaleDateString()} • {event.type}
                                </p>
                                {event.description && (
                                    <p className="text-sm mt-1">{event.description}</p>
                                )}
                            </div>
                        </div>
                    ))}

                    {events.length === 0 && (
                        <div className="text-center text-muted-foreground py-8">
                            No upcoming deadlines
                        </div>
                    )}
                </div>
            </CardContent>
        </Card>
    );
}