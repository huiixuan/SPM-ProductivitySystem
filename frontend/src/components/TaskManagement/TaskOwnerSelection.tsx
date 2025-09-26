import { useState, useEffect } from "react"
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
  CommandShortcut,
} from "@/components/ui/command"

export function TaskOwnerSelection() {
  const [users, setUsers] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch("/api/user/get-all-emails")
      .then(res => {
        if (!res.ok) return res.json().then(data => {
          throw new Error(data.messsage)
        })
        return res.json()
      })
      .then(data => setUsers(data))
      .catch(err => setError(err.messsage))
  }, [])

  return (
    <Command>
      <CommandInput placeholder="Search by email..." />

      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>
        
        {users.map(user => (
          <CommandItem>{user}</CommandItem>
        ))}
      </CommandList>
    </Command>
  )
}