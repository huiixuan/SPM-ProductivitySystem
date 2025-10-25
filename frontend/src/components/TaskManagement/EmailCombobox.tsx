import { useState, useEffect } from "react"
import {
  Command,
  CommandEmpty,
  CommandInput,
  CommandItem,
  CommandList
} from "@/components/ui/command"
import {
  Popover,
  PopoverContent,
  PopoverTrigger
} from "@/components/ui/popover"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ChevronDown, X } from "lucide-react"

interface UserData {
  role: string,
  email: string
}

type OwnerSelectionProps = {
  value?: string | string[],
  onChange?: (value: string | string[]) => void,
  placeholder?: string,
  currentUserData: UserData,
  multiple?: boolean
}

type UserOption = {
  id: number,
  role: string,
  name: string,
  email: string
}

export default function EmailCombobox({ 
  value, 
  onChange, 
  placeholder = "Select email...", 
  currentUserData,
  multiple = false
}: OwnerSelectionProps) {
  const [open, setOpen] = useState<boolean>(false)
  const [selected, setSelected] = useState<string[]>(Array.isArray(value) ? value : value ? [value] : [])
  const [users, setUsers] = useState<UserOption[]>([]) 
  const [error, setError] = useState("")

  const token = localStorage.getItem("token")

  const ROLE_HIERARCHY: Record<string, number> = {
    "staff": 1,
    "manager": 2,
    "director": 3
  }

  useEffect(() => {
    if (Array.isArray(value)) {
      setSelected(value)
    } else if (value) {
      setSelected([value])
    } else {
      setSelected([])
    }
  }, [value])

  useEffect(() => {
    fetch("/api/user/get-all-users", {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`
      }
    })
      .then(res => {
        if (!res.ok) throw new Error("Failed to fetch users.")
        return res.json()
      })
      .then((data: UserOption[]) => setUsers(data))
      .catch(err => setError(err.message))
  }, [])

  const validUsers = users.filter(user => {
    if (user.email === currentUserData.email) {
      return true
    }

    if (!multiple) {
      return ROLE_HIERARCHY[user.role.toLowerCase()] < ROLE_HIERARCHY[currentUserData.role]
    }

    return true
  })

  const handleSelect = (email: string) => {
    let updated: string[]

    if (multiple) {
      if (selected.includes(email)) {
        updated = selected.filter(e => e !== email)
      } else {
        updated = [...selected, email]
      }

      setSelected(updated)
      if (onChange) onChange(updated)

    } else {
      updated = [email]
      setSelected(updated)
      if (onChange) onChange(email)
      setOpen(false)
    }
  }

  const handleCancelEmail = (email: string, event?: React.MouseEvent) => {
    if (event) {
      event.preventDefault()
      event.stopPropagation()
    }

    const updated = selected.filter(e => e !== email)
    setSelected(updated)
    if (onChange) onChange(updated)
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="outline" role="combobox" aria-expanded={open} className="w-full flex items-center justify-between bg-white">
          {multiple ? ( 
            selected.length > 0 ? ( 
              <div className="flex flex-row gap-2">
                {selected.map(email => (
                  <Badge key={email} variant="outline" className="py-1 px-2">
                    {email}
                    <span role="button" tabIndex={0} onClick={(e) => {handleCancelEmail(email, e)}} className="cursor-pointer">
                      <X />
                    </span>
                    
                  </Badge>
                ))}
              </div>
            ) : (
              <span className="text-gray-400">{placeholder}</span>
            )
          ) : (
            selected.length === 1 ? (
              <span>{selected[0]}</span>
            ) : (
              <span className="text-gray-400">{placeholder}</span>
            )
          )}

          <ChevronDown className="opacity-50" />
        </Button>
      </PopoverTrigger>
      
      <PopoverContent className="w-full">
        {error && (<div className="text-red-700">{error}</div>)}

        <Command>
          <CommandInput placeholder="Search by email..." />

          <CommandList>
            <CommandEmpty>No results found.</CommandEmpty>
            
            {!multiple ? (
              validUsers.map(user => (
                <CommandItem key={user.email} value={user.email} onSelect={() => handleSelect(user.email)}>{user.email}</CommandItem>
              ))
            ): (
              users.map(user => (
                <CommandItem key={user.email} value={user.email} onSelect={() => handleSelect(user.email)}>{user.email}</CommandItem>
              ))
            )}
          </CommandList>
      </Command>
      </PopoverContent>
    </Popover>
  )
}