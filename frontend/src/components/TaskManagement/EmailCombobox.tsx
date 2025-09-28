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

type OwnerSelectionProps = {
  value?: string | string[],
  onChange?: (value: string | string[]) => void,
  placeholder?: string,
  multiple?: boolean
}

export default function EmailCombobox({ value, onChange, placeholder = "Select email...", multiple = false }: OwnerSelectionProps) {
  const [open, setOpen] = useState<boolean>(false)
  const [selected, setSelected] = useState<string[]>(Array.isArray(value) ? value : value ? [value] : [])
  const [users, setUsers] = useState<string[]>([]) 
  const [error, setError] = useState("")

  useEffect(() => {
    fetch("/api/user/get-all-emails")
      .then(res => {
        if (!res.ok) return res.json().then(data => {
          console.log(data.message)
          throw new Error(data.message)
        })
        return res.json()
      })
      .then((data: string[]) => setUsers(data as string[]))
      .catch(err => setError(err.message))
  }, [])

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
            
            {users.map(user => (
              <CommandItem key={user} value={user} onSelect={() => handleSelect(user)}>{user}</CommandItem>
            ))}
          </CommandList>
      </Command>
      </PopoverContent>
    </Popover>
  )
}