"use client";

import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom"; 
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ArrowLeft } from "lucide-react"; 

type CalendarEvent = {
    id: number;
    title: string;
    description?: string;
    start: Date;
    end: Date;
    type: 'task' | 'project';
    status: 'completed' | 'ongoing' | 'overdue' | 'upcoming';
    assignee?: string;
};

type TeamMember = {
    id: number;
    name: string;
    email: string;
    role: string;
    workload: number;
};

export default function SchedulePage() {
    const [activeTab, setActiveTab] = useState<"personal" | "team">("personal");
    const [personalEvents, setPersonalEvents] = useState<CalendarEvent[]>([]);
    const [teamEvents, setTeamEvents] = useState<CalendarEvent[]>([]);
    const [teamMembers, setTeamMembers] = useState<TeamMember[]>([]);
    const [selectedMember, setSelectedMember] = useState<string>('all');
    const [loading, setLoading] = useState(true);
    const navigate = useNavigate();

    useEffect(() => {
        fetchCalendarData();
    }, []);

    const fetchCalendarData = async () => {
        try {
            const token = localStorage.getItem("token");

            
            await new Promise(resolve => setTimeout(resolve, 1000));

            // Mock data - replace with actual API calls
            const mockPersonalEvents: CalendarEvent[] = [
                {
                    id: 1,
                    title: "Complete Project Proposal",
                    description: "Finalize and submit the project proposal document",
                    start: new Date(Date.now() + 2 * 24 * 60 * 60 * 1000), // 2 days from now
                    end: new Date(Date.now() + 2 * 24 * 60 * 60 * 1000),
                    type: "task",
                    status: "upcoming"
                },
                {
                    id: 2,
                    title: "Team Meeting",
                    description: "Weekly team sync meeting",
                    start: new Date(Date.now() + 1 * 24 * 60 * 60 * 1000), // 1 day from now
                    end: new Date(Date.now() + 1 * 24 * 60 * 60 * 1000),
                    type: "task",
                    status: "ongoing"
                },
                {
                    id: 3,
                    title: "Project Alpha Deadline",
                    start: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000), // 1 day ago
                    end: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000),
                    type: "project",
                    status: "overdue"
                }
            ];

            const mockTeamEvents: CalendarEvent[] = [
                {
                    id: 4,
                    title: "Design Review",
                    start: new Date(Date.now() + 3 * 24 * 60 * 60 * 1000),
                    end: new Date(Date.now() + 3 * 24 * 60 * 60 * 1000),
                    type: "task",
                    status: "upcoming",
                    assignee: "alice@example.com"
                },
                {
                    id: 5,
                    title: "Client Presentation",
                    start: new Date(Date.now() + 5 * 24 * 60 * 60 * 1000),
                    end: new Date(Date.now() + 5 * 24 * 60 * 60 * 1000),
                    type: "project",
                    status: "upcoming",
                    assignee: "bob@example.com"
                }
            ];

            const mockTeamMembers: TeamMember[] = [
                { id: 1, name: "Alice Johnson", email: "alice@example.com", role: "Developer", workload: 3 },
                { id: 2, name: "Bob Smith", email: "bob@example.com", role: "Designer", workload: 2 },
                { id: 3, name: "Carol Davis", email: "carol@example.com", role: "Manager", workload: 1 }
            ];

            setPersonalEvents(mockPersonalEvents);
            setTeamEvents(mockTeamEvents);
            setTeamMembers(mockTeamMembers);

        } catch (error) {
            console.error("Failed to fetch calendar data:", error);
        } finally {
            setLoading(false);
        }
    };

    const handleBack = () => {
        navigate("/HomePage"); // Navigate back to homepage
    };

    const filteredTeamEvents = selectedMember === 'all'
        ? teamEvents
        : teamEvents.filter(event => event.assignee === selectedMember);

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'overdue': return 'destructive';
            case 'ongoing': return 'default';
            case 'completed': return 'secondary';
            default: return 'outline';
        }
    };

    const getWorkloadLevel = (count: number) => {
        if (count <= 2) return 'low';
        if (count <= 5) return 'medium';
        return 'high';
    };

    if (loading) {
        return (
            <div className="container mx-auto p-6">
                <div className="text-center">Loading schedule...</div>
            </div>
        );
    }

    return (
        <div className="container mx-auto p-6 space-y-6">
            {/* Header with Back Button */}
            <div className="flex items-center gap-4">
                <Button
                    variant="outline"
                    onClick={handleBack}
                    className="flex items-center gap-2"
                >
                    <ArrowLeft className="h-4 w-4" />
                    Back to Dashboard
                </Button>
                <h1 className="text-3xl font-bold">Schedule & Timeline</h1>
            </div>

            {/* Simple Tab Navigation */}
            <div className="flex space-x-4 border-b">
                <Button
                    variant={activeTab === "personal" ? "default" : "ghost"}
                    onClick={() => setActiveTab("personal")}
                    className="rounded-none border-b-2 border-transparent data-[active=true]:border-primary"
                >
                    My Schedule
                </Button>
                <Button
                    variant={activeTab === "team" ? "default" : "ghost"}
                    onClick={() => setActiveTab("team")}
                    className="rounded-none border-b-2 border-transparent data-[active=true]:border-primary"
                >
                    Team Schedule
                </Button>
            </div>

            {/* Personal Schedule Tab */}
            {activeTab === "personal" && (
                <Card>
                    <CardHeader>
                        <CardTitle>My Upcoming Deadlines</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-4">
                            {personalEvents.map((event) => (
                                <div key={event.id} className="flex items-center justify-between p-3 border rounded-lg">
                                    <div className="flex-1">
                                        <div className="flex items-center gap-2">
                                            <h4 className="font-medium">{event.title}</h4>
                                            <Badge variant={getStatusColor(event.status)}>
                                                {event.status}
                                            </Badge>
                                            <Badge variant="outline">{event.type}</Badge>
                                        </div>
                                        <p className="text-sm text-muted-foreground">
                                            Due: {event.start.toLocaleDateString()}
                                        </p>
                                        {event.description && (
                                            <p className="text-sm mt-1">{event.description}</p>
                                        )}
                                    </div>
                                </div>
                            ))}

                            {personalEvents.length === 0 && (
                                <div className="text-center text-muted-foreground py-8">
                                    No upcoming deadlines
                                </div>
                            )}
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Team Schedule Tab */}
            {activeTab === "team" && (
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
                            <h3 className="font-semibold">Upcoming Team Deadlines</h3>
                            {filteredTeamEvents.map(event => (
                                <div key={event.id} className="flex items-center justify-between p-3 border rounded-lg">
                                    <div className="flex-1">
                                        <div className="flex items-center gap-2">
                                            <h4 className="font-medium">{event.title}</h4>
                                            <Badge variant="outline">{event.type}</Badge>
                                            <Badge variant={getStatusColor(event.status)}>
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

                            {filteredTeamEvents.length === 0 && (
                                <div className="text-center text-muted-foreground py-8">
                                    No team deadlines found
                                </div>
                            )}
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Additional Back Button at Bottom */}
            <div className="flex justify-center mt-6">
                <Button
                    variant="outline"
                    onClick={handleBack}
                    className="flex items-center gap-2"
                >
                    <ArrowLeft className="h-4 w-4" />
                    Back to Dashboard
                </Button>
            </div>
        </div>
    );
}