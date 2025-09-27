// frontend/src/pages/ProjectListPage.tsx (FINAL FIX: Graceful 403/Empty State)

import React, { useEffect, useState, useCallback, useLayoutEffect } from 'react';
import axios from 'axios';
import { Link, useNavigate } from "react-router-dom"; 
import { CreateProjectDialog } from '@/components/CreateProjectDialog'; 

// --- SHADCN Imports ---
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

interface Project {
  id: number;
  name: string;
  status: 'PD' | '3' | '1';
  deadline: string;
}

interface UserData {
    id: number;
    role: string;
    name: string;
    username: string;
}

const statusMap: Record<Project['status'], { label: string, color: string }> = {
  'PD': { label: 'Pending', color: 'bg-red-500' },
  '3': { label: 'In Progress', color: 'bg-blue-500' },
  '1': { label: 'Completed', color: 'bg-green-500' },
};

const AUTHORIZED_ROLES = ['Manager', 'Director'];

/**
 * Loads the current user's data (ID and Role) from localStorage.
 */
const loadCurrentUser = (): UserData | null => {
    try {
        const userString = localStorage.getItem('currentUser');
        if (userString) {
            return JSON.parse(userString);
        }
    } catch (e) {
        console.error("Failed to parse currentUser from localStorage", e);
    }
    return null;
};


export function ProjectListPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [currentUser, setCurrentUser] = useState<UserData | null>(null); 
  const navigate = useNavigate(); 
  
  // Dynamic Check: Role comes from state, set via localStorage load
  const userRole = currentUser?.role || 'Guest';
  const isAuthorizedToCreate = AUTHORIZED_ROLES.includes(userRole);
  
  // Dynamic Header: ID comes from the user state
  const authHeader = `Mock-User-ID ${currentUser?.id || 0}`;

  // Use useCallback to memoize the fetch function
  const fetchProjects = useCallback(async (currentAuthHeader: string) => {
    if (!currentAuthHeader || currentAuthHeader.endsWith('0')) return;
    
    try {
      setLoading(true);
      const response = await axios.get<Project[]>('/api/projects', {
        headers: {
            'Authorization': currentAuthHeader 
        }
      });
      setProjects(response.data);
    } catch (error) {
      console.error('Error fetching projects:', error);
      
      if (axios.isAxiosError(error)) {
          
          // 🛑 CRITICAL FIX 1: If 401 Unauthorized, we must clear data and redirect.
          if (error.response?.status === 401) {
              localStorage.removeItem('currentUser'); 
              navigate('/login');
              return; 
          }
          
          // 🛑 CRITICAL FIX 2: If 403 Forbidden, suppress the alert 
          // and treat it as an empty project list. (User is logged in but denied access)
          if (error.response?.status === 403) {
             // The user is authenticated (currentUser exists), but the backend denied access.
             // We set projects to empty so the 'No projects found' message displays.
             setProjects([]); 
          } else {
             // For all other errors (500, network issues), show a generic alert.
             alert('Could not load projects. Server or network issue.');
             setProjects([]);
          }
      }
      
    } finally {
      // 🛑 Ensure loading is false, even on error, so the UI updates immediately.
      setLoading(false); 
    }
  }, [navigate]);

  // useLayoutEffect runs synchronously to check localStorage before rendering
  useLayoutEffect(() => {
    const user = loadCurrentUser();
    if (user) {
        setCurrentUser(user);
    } else {
        // If no user is found, redirect immediately.
        navigate('/login');
    }
  }, [navigate]); 

  useEffect(() => {
    // Step B: Once the currentUser state is set, fetch the projects
    if (currentUser) {
        fetchProjects(authHeader);
    }
  }, [currentUser, fetchProjects, authHeader]); 

  // --- Loading State ---
  if (!currentUser || loading) return (
    <div className="p-8 text-center">
        <p>Loading Projects...</p>
    </div>
  );
  
  // --- Main Content Rendering (User is authenticated and projects loaded/failed) ---
  return (
    <div className="p-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">My Projects</h1>
        
        {/* CONDITIONAL RENDERING */}
        {isAuthorizedToCreate && (
            <CreateProjectDialog 
                onProjectCreated={() => fetchProjects(authHeader)}
                authHeader={authHeader}
            /> 
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* This block now displays immediately because 'loading' is false */}
        {projects.length === 0 ? (
            <p className="col-span-3 text-center text-muted-foreground">No projects found. Use the "Create Project" button to start (if authorized).</p>
        ) : (
            projects.map((project) => (
            <Card key={project.id} className="shadow-lg">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-xl font-semibold hover:text-primary transition-colors cursor-pointer">
                    {project.name}
                </CardTitle>
                <Badge className={statusMap[project.status]?.color}>
                    {statusMap[project.status]?.label}
                </Badge>
                </CardHeader>
                <CardContent>
                <p className="text-sm text-muted-foreground mb-4">
                    Deadline: {project.deadline ? new Date(project.deadline).toDateString() : 'N/A'}
                </p>
                <Button variant="default" className="w-full">
                    View Project Details
                </Button>
                </CardContent>
            </Card>
            ))
        )}
      </div>
      <footer className="mt-8 text-sm text-center text-muted-foreground">
          Currently logged in as: {currentUser.name} ({currentUser.role})
      </footer>
    </div>
  );
}