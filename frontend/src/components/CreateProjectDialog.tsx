// frontend/src/components/CreateProjectDialog.tsx

import React, { useState, useEffect, useMemo } from 'react';
import { useForm, type SubmitHandler } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { format } from 'date-fns';
import { CalendarIcon, Plus } from 'lucide-react';
import axios from 'axios';

// --- Local Component Import ---
import { CollaboratorSelect } from './CollaboratorSelect';

// --- SHADCN Imports ---
import { Button } from './ui/button';
import { 
  Dialog, 
  DialogContent, 
  DialogHeader, 
  DialogTitle, 
  DialogTrigger,
  DialogDescription,
  DialogOverlay 
} from './ui/dialog';
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from './ui/form';
import { Input } from './ui/input';
import { Textarea } from './ui/textarea';
import { Popover, PopoverContent, PopoverTrigger } from './ui/popover';
import { Calendar } from './ui/calendar';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { cn } from '@/lib/utils';
import { ScrollArea } from './ui/scroll-area'; // 🛑 Corrected Import

// --- Form Schema (Validation) ---
const ProjectSchema = z.object({
  name: z.string().min(3, { message: 'Project name is required (min 3 characters).' }),
  description: z.string().optional(),
  deadline: z.date({ required_error: 'A project deadline is required.' }),
  collaborators: z.string().optional(),
  status: z.enum(['PD', '3', '1'], { required_error: 'Status is required.' }),
});

type ProjectInputs = z.infer<typeof ProjectSchema>;

interface CreateProjectDialogProps {
    onProjectCreated: () => void;
    authHeader: string; 
}

export function CreateProjectDialog({ onProjectCreated, authHeader }: CreateProjectDialogProps) {
  const [open, setOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Set today's date to the beginning of the day (00:00:00) 
  const today = new Date();
  today.setHours(0, 0, 0, 0); 
  
  const form = useForm<ProjectInputs>({
    resolver: zodResolver(ProjectSchema),
    defaultValues: {
      name: '', description: '', collaborators: '', status: 'PD',
    },
  });

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const uploadedFile = event.target.files?.[0];
    if (uploadedFile) {
      if (uploadedFile.type !== 'application/pdf') {
        alert('Only PDF files are allowed.');
        setFile(null);
        event.target.value = '';
        return;
      }
      setFile(uploadedFile);
    } else {
      setFile(null);
    }
  };

  const onSubmit: SubmitHandler<ProjectInputs> = async (data) => {
    setIsSubmitting(true);
    try {
      const formData = new FormData();
      formData.append('name', data.name);
      formData.append('description', data.description || '');
      formData.append('deadline', format(data.deadline, 'yyyy-MM-dd')); 
      formData.append('status', data.status);
      formData.append('collaborators', data.collaborators || '');

      if (file) {
        formData.append('attachment', file);
      }

      const response = await axios.post('/api/projects', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
          'Authorization': authHeader, 
        },
      });

      console.log('Project Created:', response.data);
      alert(`Project "${response.data.name}" created successfully!`);
      
      form.reset();
      setFile(null);
      setOpen(false); 
      onProjectCreated(); 

    } catch (error) {
      console.error('Error creating project:', error);
      const errorMessage = axios.isAxiosError(error) && error.response?.data?.error 
                             ? error.response.data.error 
                             : 'Failed to create project. Please check network and form data.';
      alert(errorMessage);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button className="flex items-center gap-2">
          <Plus className="h-4 w-4" /> Create Project
        </Button>
      </DialogTrigger>
      
      {/* Overlay: Removed explicit overlay, relying on the base DialogOverlay component or its fixed source file */}
      
      <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto bg-white">
        <DialogHeader>
          <DialogTitle>Create New Project</DialogTitle>
          <DialogDescription>
            Enter the details for your new project, including the deadline and initial status.
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="grid gap-4 py-4">
            
            {/* Project Name */}
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Project Name</FormLabel>
                  <FormControl><Input placeholder="e.g., Q3 Marketing Campaign" {...field} /></FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Description */}
            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Description</FormLabel>
                  <FormControl><Textarea placeholder="Briefly describe the project goals..." {...field} /></FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Deadline */}
            <FormField
              control={form.control}
              name="deadline"
              render={({ field }) => (
                <FormItem className="flex flex-col">
                  <FormLabel className="mb-1">Deadline</FormLabel>
                  <Popover>
                    <PopoverTrigger asChild>
                      <FormControl>
                        <Button
                          variant={'outline'}
                          className={cn('w-full justify-start text-left font-normal', !field.value && 'text-muted-foreground')}
                        >
                          {field.value ? (format(field.value, 'PPP')) : (<span>Pick a date</span>)}
                          <CalendarIcon className="ml-auto h-4 w-4 opacity-50" />
                        </Button>
                      </FormControl>
                    </PopoverTrigger>
                    {/* PopoverContent with opaque background */}
                    <PopoverContent className="w-auto p-0 bg-popover" align="start">
                      <Calendar 
                        mode="single" 
                        selected={field.value} 
                        onSelect={field.onChange} 
                        initialFocus 
                        // Visually disable and prevent selection of past dates
                        disabled={{ before: today }}
                        fromDate={today}
                      />
                    </PopoverContent>
                  </Popover>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Collaborators (Autocomplete/Select) */}
            <FormField
              control={form.control}
              name="collaborators"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Collaborators (Search by Email)</FormLabel>
                  <FormControl>
                    {/* 🛑 CollaboratorSelect is the single input used here */}
                    <CollaboratorSelect 
                      authHeader={authHeader}
                      onChange={field.onChange} 
                      value={field.value || ''}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Status */}
            <FormField
              control={form.control}
              name="status"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Status</FormLabel>
                  <Select onValueChange={field.onChange} defaultValue={field.value}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Select project status" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="PD">PD (Pending)</SelectItem>
                      <SelectItem value="3">3 (In Progress)</SelectItem>
                      <SelectItem value="1">1 (Completed)</SelectItem>
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Attachment */}
            <FormItem>
              <FormLabel>Attachment (PDF files only)</FormLabel>
              <FormControl>
                <Input 
                  type="file" 
                  accept="application/pdf"
                  onChange={handleFileChange}
                  className="file:text-sm file:font-medium"
                />
              </FormControl>
              {file && <p className="text-xs text-muted-foreground mt-1">Selected: {file.name}</p>}
              <FormMessage />
            </FormItem>
            
            <Button type="submit" className="mt-6" disabled={isSubmitting}>
              {isSubmitting ? 'Creating Project...' : 'Create Project'}
            </Button>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}