"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { CalendarEvent, TeamMember } from "@/types/calendar";

export default function TeamCalendar() {
    const [events, setEvents] = useState<CalendarEvent[]>([]);
    const [teamMembers, setTeamMembers] = useState<TeamMember[]>([]);
    const [selectedMember, setSelectedMember] = useState<string>('all');
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchTeamData();
    }, []);

    const fetchTeamData = async () => {
        try {
            const token = localStorage.getItem("token");
            const [eventsRes, teamRes] = await Promise.all([
                fetch("http://127.0.0.1:5000/api/calendar/team", {
                    headers: { Authorization: `Bearer ${token}` },
                }),
                fetch("http://127.0.0.1:5000/api/team/members", {
                    headers: { Authorization: `Bearer ${token}` },
                })
            ]);

            if (eventsRes.ok) {
                const eventsData = await eventsRes.json();
                setEvents(eventsData.events.map((event: any) => ({
                    ...event,
                    start: new Date(event.start),
                    end: new Date(event.end),
                })));
            }

            if (teamRes.ok) {
                const teamData = await teamRes.json();
                setTeamMembers(teamData.members);
            }
        } catch (error) {
            console.error("Failed to fetch team data:", error);
        } finally {
            setLoading(false);
        }
    };

    const filteredEvents = selectedMember === 'all'
        ? events
        : events.filter(event => event.assignee === selectedMember);

    const getWorkloadLevel = (count: number) => {
        if (count <= 2) return 'low';
        if (count <= 5) return 'medium';
        return 'high';
    };

    if (loading) {
        return <div>Loading team schedule...</div>;
    }

    return (
        <Card>
            <CardHeader>
                <div className="flex justify-between items-center">
                    <CardTitle>Team Schedule</CardTitle>
                    <Select value={selectedMember} onValueChange={setSelectedMember}>
                        <SelectTrigger className="w-48">
                            <SelectValue placeholder="Filter by member" />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="all">All Team Members</SelectItem>
                            {teamMembers.map(member => (
                                <SelectItem key={member.id} value={member.email}>
                                    {member.name} ({member.role})
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                </div>
            </CardHeader>

            <CardContent>
                {/* Workload Overview */}
                <div className="mb-6">
                    <h3 className="font-semibold mb-3">Workload Distribution</h3>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        {teamMembers.map(member => (
                            <div key={member.id} className="border rounded-lg p-3">
                                <div className="flex justify-between items-center">
                                    <span className="font-medium">{member.name}</span>
                                    <Badge variant={
                                        getWorkloadLevel(member.workload) === 'high' ? 'destructive' :
                                            getWorkloadLevel(member.workload) === 'medium' ? 'default' : 'secondary'
                                    }>
                                        {member.workload} tasks
                                    </Badge>
                                </div>
                                <p className="text-sm text-muted-foreground">{member.role}</p>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Team Events */}
                <div className="space-y-3">
                    <h3 className="font-semibold">Upcoming Deadlines</h3>
                    {filteredEvents.map(event => (
                        <div key={event.id} className="flex items-center justify-between p-3 border rounded-lg">
                            <div className="flex-1">
                                <div className="flex items-center gap-2">
                                    <h4 className="font-medium">{event.title}</h4>
                                    <Badge variant="outline">{event.type}</Badge>
                                    <Badge variant={
                                        event.status === 'overdue' ? 'destructive' : 'default'
                                    }>
                                        {event.status}
                                    </Badge>
                                </div>
                                <div className="flex gap-4 text-sm text-muted-foreground mt-1">
                                    <span>Due: {event.start.toLocaleDateString()}</span>
                                    <span>Assigned to: {event.assignee}</span>
                                </div>
                            </div>
                        </div>
                    ))}

                    {filteredEvents.length === 0 && (
                        <div className="text-center text-muted-foreground py-8">
                            No team deadlines found
                        </div>
                    )}
                </div>
            </CardContent>
        </Card>
    );
}