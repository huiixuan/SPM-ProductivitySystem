// frontend/src/components/CollaboratorSelect.tsx

import React, { useState, useEffect } from 'react';
import { useDebounce } from '@/hooks/useDebounce';
import { Input } from './ui/input';
import { Button } from './ui/button';
import { ScrollArea } from './ui/scroll-area';
import { Badge } from './ui/badge';
import { X } from 'lucide-react';
import axios from 'axios';

type User = { id: string; email: string };

interface CollaboratorSelectProps {
  authHeader: string;
  onChange: (collaborators: string) => void;
  value: string;
}

export const CollaboratorSelect: React.FC<CollaboratorSelectProps> = ({ authHeader, onChange, value }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [searchResults, setSearchResults] = useState<User[]>([]);
  const [loading, setLoading] = useState(false);
  
  const selectedEmails = value ? value.split(',').map(e => e.trim()).filter(e => e) : [];

  const debouncedSearchTerm = useDebounce(searchTerm, 500);

  // --- Fetch Logic ---
  useEffect(() => {
    if (debouncedSearchTerm.length > 2) {
      setLoading(true);
      
      // *** API CALL TO SEARCH USERS BY EMAIL (Check if this endpoint works) ***
      axios.get(`/api/users/search?q=${debouncedSearchTerm}`, { 
        headers: { 'Authorization': authHeader } 
      })
      .then(response => {
        const newResults = response.data.filter((user: User) => !selectedEmails.includes(user.email));
        setSearchResults(newResults);
      })
      .catch(error => {
        console.error("Error fetching users:", error);
        setSearchResults([]);
      })
      .finally(() => {
        setLoading(false);
      });
    } else {
      setSearchResults([]);
    }
  }, [debouncedSearchTerm, authHeader, value]);

  const addCollaborator = (email: string) => {
    if (!selectedEmails.includes(email)) {
      const newEmails = [...selectedEmails, email];
      onChange(newEmails.join(', '));
      setSearchTerm('');
      setSearchResults([]);
    }
  };

  const removeCollaborator = (email: string) => {
    const newEmails = selectedEmails.filter(e => e !== email);
    onChange(newEmails.join(', '));
  };

  return (
    <div className="space-y-2"> {/* Added space-y-2 for better separation */}
      {/* 1. Display Selected Collaborators (Badges) */}
      <div className="flex flex-wrap gap-2 min-h-8 border p-2 rounded-md">
        {selectedEmails.map(email => (
          <Badge key={email} variant="secondary" className="flex items-center">
            {email}
            <X 
              className="ml-1 h-3 w-3 cursor-pointer" 
              onClick={() => removeCollaborator(email)} 
            />
          </Badge>
        ))}
      </div>

      {/* 2. Search Input */}
      <Input
        placeholder="Search users by email..."
        value={searchTerm}
        onChange={(e) => setSearchTerm(e.target.value)}
      />

      {loading && <p className="text-sm text-muted-foreground mt-2">Searching...</p>}

      {/* 3. Search Results Dropdown */}
      {searchResults.length > 0 && (
        <ScrollArea className="h-32 w-full border rounded-md">
          <div className="p-2">
            {searchResults.map(user => (
              <div 
                key={user.id} 
                className="flex justify-between items-center p-2 hover:bg-muted cursor-pointer"
                onClick={() => addCollaborator(user.email)}
              >
                <span>{user.email}</span>
                <Button size="sm" variant="outline">Add</Button>
              </div>
            ))}
          </div>
        </ScrollArea>
      )}
    </div>
  );
};