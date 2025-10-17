// pages/SchedulePage.tsx
"use client";

import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ArrowLeft, AlertTriangle } from "lucide-react";

type CalendarEvent = {
    id: number;
    title: string;
    description?: string;
    start: Date;
    end: Date;
    type: 'task' | 'project';
    status: 'completed' | 'ongoing' | 'overdue' | 'upcoming';
    assignee?: string;
    assigneeEmail?: string;
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
    const [currentUser, setCurrentUser] = useState<any>(null);
    const navigate = useNavigate();

    useEffect(() => {
        fetchCurrentUser();
        fetchCalendarData();
    }, []);

    const fetchCurrentUser = async () => {
        try {
            const token = localStorage.getItem("token");
            if (!token) {
                navigate("/");
                return;
            }

            const response = await fetch("http://127.0.0.1:5000/auth/dashboard", {
                headers: { Authorization: `Bearer ${token}` },
            });

            if (response.ok) {
                const data = await response.json();
                setCurrentUser(data);
            }
        } catch (error) {
            console.error("Failed to fetch current user:", error);
        }
    };

    const fetchCalendarData = async () => {
        try {
            const token = localStorage.getItem("token");
            if (!token) {
                navigate("/");
                return;
            }

            // Fetch all data in parallel
            const [personalRes, teamRes, workloadRes] = await Promise.all([
                fetch("http://127.0.0.1:5000/api/calendar/personal", {
                    headers: { Authorization: `Bearer ${token}` },
                }),
                fetch("http://127.0.0.1:5000/api/calendar/team", {
                    headers: { Authorization: `Bearer ${token}` },
                }),
                fetch("http://127.0.0.1:5000/api/calendar/workload", {
                    headers: { Authorization: `Bearer ${token}` },
                })
            ]);

            // Process personal events
            if (personalRes.ok) {
                const personalData = await personalRes.json();
                const events = personalData.events.map((event: any) => ({
                    ...event,
                    start: new Date(event.start),
                    end: new Date(event.end),
                }));
                setPersonalEvents(events);
            }

            // Process team events
            if (teamRes.ok) {
                const teamData = await teamRes.json();
                const events = teamData.events.map((event: any) => ({
                    ...event,
                    start: new Date(event.start),
                    end: new Date(event.end),
                }));
                setTeamEvents(events);
            }

            // Process workload data
            if (workloadRes.ok) {
                const workloadData = await workloadRes.json();
                setTeamMembers(workloadData.team_members);
            } else {
                // Fallback: get user emails
                const usersRes = await fetch("http://127.0.0.1:5000/api/user/get-all-emails", {
                    headers: { Authorization: `Bearer ${token}` },
                });
                if (usersRes.ok) {
                    const usersData = await usersRes.json();
                    const fallbackMembers = usersData.map((email: string, index: number) => ({
                        id: index + 1,
                        name: email.split('@')[0],
                        email: email,
                        role: 'User',
                        workload: 0
                    }));
                    setTeamMembers(fallbackMembers);
                }
            }

        } catch (error) {
            console.error("Failed to fetch calendar data:", error);
        } finally {
            setLoading(false);
        }
    };

    const handleBack = () => {
        navigate("/HomePage");
    };

    const filteredTeamEvents = selectedMember === 'all'
        ? teamEvents
        : teamEvents.filter(event => event.assigneeEmail === selectedMember);

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'overdue': return 'destructive'; // Red
            case 'ongoing': return 'default';     // Blue/Default
            case 'completed': return 'secondary'; // Gray
            default: return 'outline';            // Outlined
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

    // Count overdue items for summary
    const overdueCount = personalEvents.filter(event => event.status === 'overdue').length;

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

            {/* Current User Info */}
            {currentUser && (
                <Card>
                    <CardContent className="pt-6">
                        <div className="flex justify-between items-center">
                            <div>
                                <p className="font-semibold">Logged in as: {currentUser.email}</p>
                                <p className="text-sm text-muted-foreground">Role: {currentUser.role}</p>
                            </div>
                            <div className="flex items-center gap-2">
                                {overdueCount > 0 && (
                                    <Badge variant="destructive" className="flex items-center gap-1">
                                        <AlertTriangle className="h-3 w-3" />
                                        {overdueCount} overdue
                                    </Badge>
                                )}
                                <Badge variant="outline">
                                    {personalEvents.filter(event => event.status !== 'completed').length} upcoming items
                                </Badge>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            )}

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
                        <p className="text-sm text-muted-foreground">
                            Showing {personalEvents.length} tasks and projects
                            {overdueCount > 0 && (
                                <span className="text-destructive font-medium"> • {overdueCount} overdue items need attention</span>
                            )}
                        </p>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-4">
                            {personalEvents.map((event) => (
                                <div
                                    key={`${event.type}-${event.id}`}
                                    className={`flex items-center justify-between p-3 border rounded-lg ${event.status === 'overdue' ? 'bg-red-50 border-red-200' : ''
                                        }`}
                                >
                                    <div className="flex-1">
                                        <div className="flex items-center gap-2 mb-2">
                                            <h4 className={`font-medium ${event.status === 'overdue' ? 'text-red-800' : ''
                                                }`}>
                                                {event.title}
                                            </h4>
                                            <Badge variant={getStatusColor(event.status)}>
                                                {event.status === 'overdue' && <AlertTriangle className="h-3 w-3 mr-1" />}
                                                {event.status}
                                            </Badge>
                                            <Badge variant="outline">{event.type}</Badge>
                                        </div>
                                        <p className={`text-sm ${event.status === 'overdue' ? 'text-red-600 font-medium' : 'text-muted-foreground'
                                            }`}>
                                            Due: {event.start.toLocaleDateString()}
                                            {event.status === 'overdue' && (
                                                <span className="ml-2 font-semibold">• OVERDUE</span>
                                            )}
                                        </p>
                                        {event.description && (
                                            <p className="text-sm mt-1 text-muted-foreground">{event.description}</p>
                                        )}
                                    </div>
                                </div>
                            ))}

                            {personalEvents.length === 0 && (
                                <div className="text-center text-muted-foreground py-8">
                                    No upcoming deadlines. Create a project or task to see them here.
                                    <br />
                                    <Button
                                        variant="outline"
                                        className="mt-2"
                                        onClick={() => navigate("/HomePage")}
                                    >
                                        Go Create Something
                                    </Button>
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
                            {teamMembers.length > 0 ? (
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
                                            <p className="text-sm text-muted-foreground">{member.email}</p>
                                            <p className="text-xs text-muted-foreground">{member.role}</p>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <div className="text-center text-muted-foreground py-4">
                                    No team members found
                                </div>
                            )}
                        </div>

                        {/* Team Events */}
                        <div className="space-y-3">
                            <h3 className="font-semibold">Upcoming Team Deadlines</h3>
                            {filteredTeamEvents.length > 0 ? (
                                filteredTeamEvents.map(event => (
                                    <div
                                        key={`${event.type}-${event.id}`}
                                        className={`flex items-center justify-between p-3 border rounded-lg ${event.status === 'overdue' ? 'bg-red-50 border-red-200' : ''
                                            }`}
                                    >
                                        <div className="flex-1">
                                            <div className="flex items-center gap-2 mb-2">
                                                <h4 className={`font-medium ${event.status === 'overdue' ? 'text-red-800' : ''
                                                    }`}>
                                                    {event.title}
                                                </h4>
                                                <Badge variant="outline">{event.type}</Badge>
                                                <Badge variant={getStatusColor(event.status)}>
                                                    {event.status === 'overdue' && <AlertTriangle className="h-3 w-3 mr-1" />}
                                                    {event.status}
                                                </Badge>
                                            </div>
                                            <div className={`flex gap-4 text-sm ${event.status === 'overdue' ? 'text-red-600 font-medium' : 'text-muted-foreground'
                                                }`}>
                                                <span>Due: {event.start.toLocaleDateString()}</span>
                                                {event.status === 'overdue' && <span>• OVERDUE</span>}
                                                {event.assigneeEmail && (
                                                    <span>Assigned to: {event.assigneeEmail}</span>
                                                )}
                                            </div>
                                            {event.description && (
                                                <p className="text-sm mt-1 text-muted-foreground">{event.description}</p>
                                            )}
                                        </div>
                                    </div>
                                ))
                            ) : (
                                <div className="text-center text-muted-foreground py-8">
                                    No team deadlines found. Create projects with collaborators to see team schedule.
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