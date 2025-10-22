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
} from "lucide-react";
import { NotificationBell } from "./Notification/NotificationBell";

const items = [
	{
		title: "Home",
		url: "/HomePage",
		icon: Home,
	},
	{
		title: "Projects",
		url: "/projects", // You can change this URL to your desired projects page
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
	const { userData, handleLogout } = useAuth();

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
			</SidebarContent>

			<SidebarFooter>
				<Separator />
				<div className="flex items-center justify-between p-2"></div>
				<NotificationBell />
				<SidebarMenu>
					<SidebarMenuItem key={userData.email}>
						<SidebarMenuButton
							asChild
							className="text-black transition-colors hover:bg-gray-200 hover:!text-black"
						>
							<div>
								<div className="border border-gray-300 rounded-lg w-8 h-8 flex items-center justify-center">
									{userData.email.slice(0, 1)}
								</div>
								{userData.email}
								<LogOut
									onClick={() => handleLogout()}
									size={16}
								/>
							</div>
						</SidebarMenuButton>
					</SidebarMenuItem>
				</SidebarMenu>
			</SidebarFooter>
		</Sidebar>
	);
}
