import { useState } from "react"
import { CalendarIcon } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Calendar } from "@/components/ui/calendar"
import { Input } from "@/components/ui/input"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"

function formatDate(date: Date | undefined) {
  if (!date) return ""

  return date.toLocaleDateString("en-US", {
    day: "2-digit",
    month: "long",
    year: "numeric",
  })
}

function isValidDate(date: Date | undefined) {
  if (!date) {
    return false
  }
  return !isNaN(date.getTime())
}

type DatePickerProps = {
  date?: Date
  onChange?: (date: Date | undefined) => void
}

export default function DatePicker({ date, onChange }: DatePickerProps) {
    const today = new Date()
    const [open, setOpen] = useState(false)
    const [month, setMonth] = useState<Date | undefined>(date)
    const [value, setValue] = useState(formatDate(date))

    return (
        <div className="flex flex-col gap-3">
            <div className="relative flex gap-2">
                <Input id="date" value={value} placeholder={formatDate(today)} className="pr-10"
                    onChange={(e) => {
                        const date = new Date(e.target.value)
                        setValue(e.target.value)
                        if (isValidDate(date)) {
                            onChange?.(date)
                            setMonth(date)
                        }
                    }}
                    onKeyDown={(e) => {
                        if (e.key === "ArrowDown") {
                        e.preventDefault()
                        setOpen(true)
                        }
                    }}
                />

                <Popover open={open} onOpenChange={setOpen}>
                    <PopoverTrigger asChild>
                        <Button
                        id="date-picker"
                        variant="ghost"
                        className="absolute top-1/2 right-2 size-6 -translate-y-1/2"
                        >
                            <CalendarIcon className="size-3.5" />
                            <span className="sr-only">Select due date</span>
                        </Button>
                    </PopoverTrigger>

                    <PopoverContent
                        className="w-auto overflow-hidden p-0 bg-white"
                        align="end"
                        alignOffset={-8}
                        sideOffset={10}
                    >
                        <Calendar
                        mode="single"
                        selected={date}
                        captionLayout="dropdown"
                        showOutsideDays={false}
                        month={month}
                        onMonthChange={setMonth}
                        onSelect={(date) => {
                            if (!date || date < today) return
                            onChange?.(date)
                            setValue(formatDate(date))
                            setOpen(false)
                        }}
                        disabled={(date) => (date.getDate() < today.getDate()) && (date.getMonth() === today.getMonth())}
                        />
                    </PopoverContent>
                </Popover>
            </div>
        </div>
    )
}
