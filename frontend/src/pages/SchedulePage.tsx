"use client";

import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ArrowLeft, Calendar as CalendarIcon, List, Users, RefreshCw } from "lucide-react";
import MonthlyCalendarView from "@/components/Calendar/MonthlyCalendarView";
import WeeklyCalendarView from "@/components/Calendar/WeeklyCalendarView";
import DailyCalendarView from "@/components/Calendar/DailyCalendarView";
import EventDetailsModal from "@/components/Calendar/EventDetailsModal";

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
    collaborators?: string[];
};

type ApiCalendarEvent = Omit<CalendarEvent, 'start' | 'end'> & { start: string; end: string };

type TeamMember = {
    id: number;
    name: string;
    email: string;
    role: string;
    workload: number;
    task_count: number;
    project_count: number;
    overdue_count: number;
};

type DisplayMode = 'calendar' | 'list';
type CalendarViewType = 'month' | 'week' | 'day';

type UserData = {
    email: string;
    role: string;
};

type BasicTeamMember = {
    id: number;
    name: string;
    email: string;
    role: string;
};

const enhanceEventWithOverdueStatus = (event: ApiCalendarEvent): CalendarEvent => {
    const start = new Date(event.start);
    const end = new Date(event.end);

    let status = event.status;
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    if (status !== 'completed' && start < today && status !== 'overdue') {
        status = 'overdue';
    }

    return {
        ...event,
        start,
        end,
        status
    };
};

export default function SchedulePage() {
    const [activeTab, setActiveTab] = useState<"personal" | "team">("personal");
    const [displayMode, setDisplayMode] = useState<DisplayMode>('calendar');
    const [calendarView, setCalendarView] = useState<CalendarViewType>('month');
    const [currentDate, setCurrentDate] = useState(new Date());
    const [selectedEvent, setSelectedEvent] = useState<CalendarEvent | null>(null);
    const [isEventModalOpen, setIsEventModalOpen] = useState(false);

    const [personalEvents, setPersonalEvents] = useState<CalendarEvent[]>([]);
    const [teamEvents, setTeamEvents] = useState<CalendarEvent[]>([]);
    const [teamMembers, setTeamMembers] = useState<TeamMember[]>([]);
    const [selectedMember, setSelectedMember] = useState<string>('all');
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [currentUser, setCurrentUser] = useState<UserData | null>(null);
    const navigate = useNavigate();

    const fetchCurrentUser = useCallback(async () => {
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
    }, [navigate]);

    const fetchCalendarData = useCallback(async () => {
        try {
            const token = localStorage.getItem("token");
            if (!token) {
                navigate("/");
                return;
            }

            setRefreshing(true);

            const [personalRes, teamRes, workloadRes, teamMembersRes] = await Promise.all([
                fetch("http://127.0.0.1:5000/api/calendar/personal", {
                    headers: { Authorization: `Bearer ${token}` },
                }),
                fetch("http://127.0.0.1:5000/api/calendar/team", {
                    headers: { Authorization: `Bearer ${token}` },
                }),
                fetch("http://127.0.0.1:5000/api/calendar/workload", {
                    headers: { Authorization: `Bearer ${token}` },
                }),
                fetch("http://127.0.0.1:5000/api/team/members", {
                    headers: { Authorization: `Bearer ${token}` },
                })
            ]);

            if (personalRes.ok) {
                const personalData = await personalRes.json();
                const events = personalData.events.map((event: ApiCalendarEvent) =>
                    enhanceEventWithOverdueStatus(event)
                );
                setPersonalEvents(events);
            }

            if (teamRes.ok) {
                const teamData = await teamRes.json();
                const events = teamData.events.map((event: ApiCalendarEvent) =>
                    enhanceEventWithOverdueStatus(event)
                );
                setTeamEvents(events);
            }

            if (workloadRes.ok) {
                const workloadData = await workloadRes.json();
                setTeamMembers(workloadData.team_members);
            }

            if (teamMembersRes.ok && teamMembers.length === 0) {
                const teamMembersData = await teamMembersRes.json();
                const fallbackMembers = teamMembersData.members.map((member: BasicTeamMember) => ({
                    ...member,
                    workload: 0,
                    task_count: 0,
                    project_count: 0,
                    overdue_count: 0
                }));
                setTeamMembers(fallbackMembers);
            }

        } catch (error) {
            console.error("Failed to fetch calendar data:", error);
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    }, [navigate, teamMembers.length]);

    useEffect(() => {
        fetchCurrentUser();
        fetchCalendarData();
    }, [fetchCurrentUser, fetchCalendarData]);

    useEffect(() => {
        const interval = setInterval(() => {
            fetchCalendarData();
        }, 30000);

        return () => clearInterval(interval);
    }, [fetchCalendarData]);

    const handleBack = () => {
        navigate("/HomePage");
    };

    const handleEventSelect = (event: CalendarEvent) => {
        setSelectedEvent(event);
        setIsEventModalOpen(true);
    };

    const handleNavigate = (direction: 'prev' | 'next') => {
        const newDate = new Date(currentDate);

        if (calendarView === 'month') {
            newDate.setMonth(newDate.getMonth() + (direction === 'next' ? 1 : -1));
        } else if (calendarView === 'week') {
            newDate.setDate(newDate.getDate() + (direction === 'next' ? 7 : -7));
        } else {
            newDate.setDate(newDate.getDate() + (direction === 'next' ? 1 : -1));
        }
        setCurrentDate(newDate);
    };

    const handleGoToToday = () => {
        setCurrentDate(new Date());
    };

    const filteredTeamEvents = selectedMember === 'all'
        ? teamEvents
        : teamEvents.filter(event => {
            const isAssignee = event.assigneeEmail === selectedMember;

            const isCollaborator = event.collaborators?.includes(selectedMember) || false;

            return isAssignee || isCollaborator;
        });

    const currentEvents = activeTab === 'personal' ? personalEvents : filteredTeamEvents;

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'overdue': return 'destructive';
            case 'ongoing': return 'default';
            case 'completed': return 'secondary';
            default: return 'outline';
        }
    };

    const getWorkloadLevel = (workload: number) => {
        if (workload <= 2) return 'low';
        if (workload <= 5) return 'medium';
        return 'high';
    };

    const getWorkloadVariant = (level: string) => {
        switch (level) {
            case 'high': return 'destructive';
            case 'medium': return 'default';
            default: return 'secondary';
        }
    };

    const getWorkloadDisplay = (member: TeamMember) => {
        const totalItems = member.workload;
        const breakdown = [];

        if (member.task_count > 0) {
            breakdown.push(`${member.task_count} task${member.task_count !== 1 ? 's' : ''}`);
        }
        if (member.project_count > 0) {
            breakdown.push(`${member.project_count} project${member.project_count !== 1 ? 's' : ''}`);
        }
        if (member.overdue_count > 0) {
            breakdown.push(`${member.overdue_count} overdue`);
        }

        return {
            total: totalItems,
            breakdown: breakdown.length > 0 ? breakdown.join(', ') : 'No items'
        };
    };

    const overdueCount = personalEvents.filter(event => event.status === 'overdue').length;
    const upcomingCount = personalEvents.filter(event => event.status === 'upcoming').length;
    const ongoingCount = personalEvents.filter(event => event.status === 'ongoing').length;


    useEffect(() => {
        if (activeTab === 'team') {
            console.log('Team Events:', teamEvents.length);
            console.log('Selected Member:', selectedMember);
            console.log('Filtered Team Events:', filteredTeamEvents.length);
            console.log('Current Events:', currentEvents.length);
        }
    }, [activeTab, selectedMember, teamEvents, filteredTeamEvents, currentEvents]);

    if (loading) {
        return (
            <div className="container mx-auto p-6">
                <div className="text-center">Loading schedule...</div>
            </div>
        );
    }

    return (
        <div className="container mx-auto p-6 space-y-6">

            <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <Button variant="outline" onClick={handleBack} className="flex items-center gap-2">
                        <ArrowLeft className="h-4 w-4" />
                        Back to Dashboard
                    </Button>
                    <h1 className="text-3xl font-bold">Schedule & Timeline</h1>
                </div>

                <div className="flex items-center gap-2">
                    <Button
                        variant={displayMode === 'list' ? 'default' : 'outline'}
                        onClick={() => setDisplayMode('list')}
                        className="flex items-center gap-2"
                    >
                        <List className="h-4 w-4" /> List
                    </Button>
                    <Button
                        variant={displayMode === 'calendar' ? 'default' : 'outline'}
                        onClick={() => setDisplayMode('calendar')}
                        className="flex items-center gap-2"
                    >
                        <CalendarIcon className="h-4 w-4" /> Calendar
                    </Button>
                </div>
            </div>

            {currentUser && (
                <Card>
                    <CardContent className="pt-6">
                        <div className="flex justify-between items-center">
                            <div>
                                <p className="font-semibold">Logged in as: {currentUser.email}</p>
                                <p className="text-sm text-muted-foreground">Role: {currentUser.role}</p>
                            </div>
                            <div className="flex items-center gap-4">
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={fetchCalendarData}
                                    disabled={refreshing}
                                    className="flex items-center gap-2"
                                >
                                    <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
                                    Refresh
                                </Button>
                                {overdueCount > 0 && <Badge variant="destructive">{overdueCount} overdue</Badge>}
                                {ongoingCount > 0 && <Badge variant="default">{ongoingCount} ongoing</Badge>}
                                {upcomingCount > 0 && <Badge variant="outline">{upcomingCount} upcoming</Badge>}
                            </div>
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Tabs */}
            <div className="flex space-x-4 border-b">
                <Button
                    variant={activeTab === "personal" ? "default" : "ghost"}
                    onClick={() => setActiveTab("personal")}
                >
                    <CalendarIcon className="h-4 w-4 mr-2" /> My Schedule
                </Button>
                <Button
                    variant={activeTab === "team" ? "default" : "ghost"}
                    onClick={() => setActiveTab("team")}
                >
                    <Users className="h-4 w-4 mr-2" /> Team Schedule
                </Button>
            </div>

            {displayMode === 'calendar' && (
                <Card>
                    <CardContent className="pt-6">
                        <div className="flex items-center justify-between">
                            <div className="flex gap-2">
                                <Button
                                    variant={calendarView === 'day' ? 'default' : 'outline'}
                                    size="sm"
                                    onClick={() => setCalendarView('day')}
                                >
                                    Day
                                </Button>
                                <Button
                                    variant={calendarView === 'week' ? 'default' : 'outline'}
                                    size="sm"
                                    onClick={() => setCalendarView('week')}
                                >
                                    Week
                                </Button>
                                <Button
                                    variant={calendarView === 'month' ? 'default' : 'outline'}
                                    size="sm"
                                    onClick={() => setCalendarView('month')}
                                >
                                    Month
                                </Button>
                            </div>
                            <div className="text-sm text-muted-foreground">
                                {refreshing ? 'Refreshing...' : 'Auto-refreshes every 30 seconds'}
                            </div>
                        </div>
                    </CardContent>
                </Card>
            )}

            {activeTab === 'team' && (
                <Card>
                    <CardHeader>
                        <div className="flex items-center justify-between">
                            <CardTitle>Team Overview</CardTitle>
                            <div className="flex items-center gap-4">
                                <div className="text-sm text-muted-foreground">
                                    Showing {filteredTeamEvents.length} events for{' '}
                                    {selectedMember === 'all' ? 'all team members' : selectedMember}
                                </div>
                                <Select value={selectedMember} onValueChange={setSelectedMember}>
                                    <SelectTrigger className="w-64">
                                        <SelectValue placeholder="Filter by team member" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="all">All Team Members</SelectItem>
                                        {teamMembers.map(member => {
                                            const workloadDisplay = getWorkloadDisplay(member);
                                            return (
                                                <SelectItem key={member.id} value={member.email}>
                                                    {member.name} - {workloadDisplay.total} items
                                                </SelectItem>
                                            );
                                        })}
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>
                    </CardHeader>
                    <CardContent>
                        <div className="mb-6">
                            <h3 className="font-semibold mb-3">Workload Distribution</h3>
                            {teamMembers.length > 0 ? (
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                    {teamMembers.map(member => {
                                        const workloadLevel = getWorkloadLevel(member.workload);
                                        const workloadDisplay = getWorkloadDisplay(member);
                                        const isSelected = selectedMember === member.email;

                                        return (
                                            <div
                                                key={member.id}
                                                className={`border rounded-lg p-4 cursor-pointer transition-all ${isSelected ? 'ring-2 ring-blue-500 bg-blue-50' : 'hover:bg-gray-50'
                                                    }`}
                                                onClick={() => setSelectedMember(isSelected ? 'all' : member.email)}
                                            >
                                                <div className="flex justify-between items-center mb-2">
                                                    <span className={`font-medium ${isSelected ? 'text-blue-700' : ''}`}>
                                                        {member.name}
                                                    </span>
                                                    <Badge variant={getWorkloadVariant(workloadLevel)}>
                                                        {workloadDisplay.total} items
                                                    </Badge>
                                                </div>
                                                <p className="text-sm text-muted-foreground">{member.email}</p>
                                                <p className="text-xs text-muted-foreground capitalize">{member.role}</p>

                                                <div className="mt-2 text-xs text-muted-foreground">
                                                    {workloadDisplay.breakdown}
                                                </div>

                                                <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
                                                    <div
                                                        className={`h-2 rounded-full ${workloadLevel === 'high' ? 'bg-red-500' :
                                                                workloadLevel === 'medium' ? 'bg-yellow-500' : 'bg-green-500'
                                                            }`}
                                                        style={{
                                                            width: `${Math.min(member.workload * 10, 100)}%`
                                                        }}
                                                    ></div>
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            ) : (
                                <div className="text-center text-muted-foreground py-4">
                                    No team members found
                                </div>
                            )}
                        </div>
                    </CardContent>
                </Card>
            )}

            {displayMode === 'calendar' ? (
                <>
                    {calendarView === 'month' && (
                        <MonthlyCalendarView
                            events={currentEvents}
                            currentDate={currentDate}
                            onNavigate={handleNavigate}
                            onSelectEvent={handleEventSelect}
                            onGoToToday={handleGoToToday}
                        />
                    )}
                    {calendarView === 'week' && (
                        <WeeklyCalendarView
                            events={currentEvents}
                            currentDate={currentDate}
                            onNavigate={handleNavigate}
                            onSelectEvent={handleEventSelect}
                            onGoToToday={handleGoToToday}
                        />
                    )}
                    {calendarView === 'day' && (
                        <DailyCalendarView
                            events={currentEvents}
                            currentDate={currentDate}
                            onNavigate={handleNavigate}
                            onSelectEvent={handleEventSelect}
                            onGoToToday={handleGoToToday}
                        />
                    )}
                </>
            ) : (
                <Card>
                    <CardHeader>
                        <CardTitle>
                            {activeTab === 'personal' ? 'My Deadlines' : 'Team Deadlines'}
                            <span className="text-sm font-normal text-muted-foreground ml-2">
                                • {currentEvents.length} items
                                {activeTab === 'team' && selectedMember !== 'all' && (
                                    <> for {selectedMember}</>
                                )}
                            </span>
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-3">
                            {currentEvents.map((event) => (
                                <div
                                    key={`${event.type}-${event.id}`}
                                    className={`flex items-center justify-between p-4 border rounded-lg transition-all duration-200 ${event.status === 'overdue'
                                            ? 'bg-red-50 border-red-300 shadow-sm hover:bg-red-100'
                                            : 'hover:bg-gray-50'
                                        }`}
                                    onClick={() => handleEventSelect(event)}
                                >
                                    <div className="flex-1">
                                        <div className="flex items-center gap-2 mb-2">
                                            <h4 className={`font-medium ${event.status === 'overdue' ? 'text-red-800 text-lg' : ''
                                                }`}>
                                                {event.type === 'task' ? '📝' : '📁'} {event.title}
                                            </h4>
                                            <Badge variant={getStatusColor(event.status)} className={
                                                event.status === 'overdue' ? 'animate-pulse' : ''
                                            }>
                                                {event.status === 'overdue' ? '⚠️ ' : ''}{event.status}
                                            </Badge>
                                            <Badge variant="outline">{event.type}</Badge>
                                        </div>
                                        <p className={`text-sm ${event.status === 'overdue' ? 'text-red-600 font-medium' : 'text-muted-foreground'
                                            }`}>
                                            Due: {event.start.toLocaleDateString('en-US', {
                                                weekday: 'long',
                                                year: 'numeric',
                                                month: 'long',
                                                day: 'numeric'
                                            })}
                                        </p>
                                        {event.description && (
                                            <p className="text-sm mt-1 text-muted-foreground">{event.description}</p>
                                        )}
                                        {event.assigneeEmail && activeTab === 'team' && (
                                            <p className="text-sm mt-1 text-muted-foreground">
                                                Assigned to: {event.assigneeEmail}
                                                {event.collaborators && event.collaborators.length > 0 && (
                                                    <span> (with {event.collaborators.length} collaborator{event.collaborators.length !== 1 ? 's' : ''})</span>
                                                )}
                                            </p>
                                        )}

                                        {event.status === 'overdue' && (
                                            <div className="flex items-center gap-1 mt-2 text-red-600 text-sm">
                                                <span>⚠️ This item is overdue</span>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            ))}
                            {currentEvents.length === 0 && (
                                <div className="text-center text-muted-foreground py-8">
                                    {activeTab === 'personal' ? (
                                        'No deadlines found. Create tasks or projects to see them here.'
                                    ) : selectedMember === 'all' ? (
                                        'No team deadlines found. Team deadlines will appear when projects have collaborators.'
                                    ) : (
                                        `No deadlines found for ${selectedMember}. This user might not have any assigned tasks or projects with due dates.`
                                    )}
                                </div>
                            )}
                        </div>
                    </CardContent>
                </Card>
            )}

            <EventDetailsModal
                event={selectedEvent}
                isOpen={isEventModalOpen}
                onClose={() => setIsEventModalOpen(false)}
            />

            <div className="flex justify-center">
                <Button variant="outline" onClick={handleBack} className="flex items-center gap-2">
                    <ArrowLeft className="h-4 w-4" />
                    Back to Dashboard
                </Button>
            </div>
        </div>
    );
}