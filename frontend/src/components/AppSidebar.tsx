import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar"
import { Calendar, Home, Inbox, Search, Settings } from "lucide-react"

const items = [
  {
    title: "Projects",
    url: "/HomePage",
    icon: Home
  },
  {
    title: "Task Overview",
    url: "",
    icon: ""
  },
  {
    title: "Notifications",
    url: "",
    icon: ""
  }
]

export function AppSidebar() {
  return (
    <Sidebar>
      <SidebarContent />

    </Sidebar>
  )
}