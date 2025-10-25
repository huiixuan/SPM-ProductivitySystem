import { Link } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import {
	Sidebar,
	SidebarContent,
	SidebarFooter,
	SidebarGroup,
	SidebarGroupContent,
	SidebarGroupLabel,
	SidebarMenu,
	SidebarMenuButton,
	SidebarMenuItem,
} from "@/components/ui/sidebar";
import { Separator } from "@/components/ui/separator";
import {
	Home,
	LayoutList,
	CalendarCheck2,
	LogOut,
	FolderKanban,
	Bell
} from "lucide-react";
import { NotificationBell } from "@/components/Notification/NotificationBell";

const items = [
	{
		title: "Home",
		url: "/HomePage",
		icon: Home,
	},
	{
		title: "Projects",
		url: "/projects",
		icon: FolderKanban,
	},
	{
		title: "Task Overview",
		url: "/UserTasks",
		icon: LayoutList,
	},
	{
		title: "Schedule",
		url: "/schedule",
		icon: CalendarCheck2,
	},
];

export function AppSidebar() {
	const { userData } = useAuth();

	return (
		<Sidebar className="p-3">
			<SidebarContent>
				<SidebarGroup>
					<SidebarGroupLabel>Application</SidebarGroupLabel>

					<SidebarGroupContent>
						<SidebarMenu>
							{items.map((item) => (
								<SidebarMenuItem key={item.title}>
									<SidebarMenuButton
										asChild
										className="text-black transition-colors hover:bg-gray-200 hover:!text-black"
									>
										<Link to={item.url}>
											<item.icon />
											{item.title}
										</Link>
									</SidebarMenuButton>
								</SidebarMenuItem>
							))}
						</SidebarMenu>
					</SidebarGroupContent>
				</SidebarGroup>

				<SidebarGroup>
					<SidebarGroupLabel>Account</SidebarGroupLabel>

					<SidebarGroupContent>
						<SidebarMenu>
							<NotificationBell />
							
							<SidebarMenuItem key="logout">
								<SidebarMenuButton
									asChild
									className="text-black transition-colors hover:bg-gray-200 hover:!text-black"
								>	
									<Link to="/">
										<LogOut />
										Log Out
									</Link>
								</SidebarMenuButton>
							</SidebarMenuItem>
						</SidebarMenu>
					</SidebarGroupContent>
				</SidebarGroup>
			</SidebarContent>

			<SidebarFooter>
				<Separator />
				<div className="flex flex-row gap-2 justify-center items-center">
						<div className="border border-gray-300 rounded-lg w-8 h-8 flex items-center justify-center">
							{userData.email.slice(0, 1)}
						</div>
						
						{userData.email}
				</div>
			</SidebarFooter>
		</Sidebar>
	);
}
