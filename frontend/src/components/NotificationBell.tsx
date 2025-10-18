import { useState, useEffect } from "react";
import { Bell } from "lucide-react";

interface Notification {
	id: number;
	message: string;
	is_read: boolean;
	created_at: string;
	payload: { project_name: string; task_title: string; duedate: string };
}

export const NotificationBell = () => {
	const [notifications, setNotifications] = useState<Notification[]>([]);
	const [open, setOpen] = useState(false);

	const fetchNotifications = async () => {
		try {
			const token = localStorage.getItem("token");
			if (!token) return;

			const response = await fetch(
				"http://127.0.0.1:5000/api/notifications",
				{
					headers: { Authorization: `Bearer ${token}` },
				}
			);

			if (response.ok) {
				const data = await response.json();
				setNotifications(data);
			} else {
				console.error("Failed to fetch notifications");
			}
		} catch (err) {
			console.error("Error fetching notifications:", err);
		}
	};

	const markAsRead = async (id: number) => {
		try {
			const token = localStorage.getItem("token");
			if (!token) return;

			await fetch(`http://127.0.0.1:5000/api/notifications/${id}/read`, {
				method: "PATCH",
				headers: { Authorization: `Bearer ${token}` },
			});

			setNotifications((prev) =>
				prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
			);
		} catch (err) {
			console.error("Error marking notification as read:", err);
		}
	};

	useEffect(() => {
		fetchNotifications();
	}, []);

	const unreadCount = notifications.filter((n) => !n.is_read).length;

	return (
		<div className="relative">
			<button
				onClick={() => setOpen(!open)}
				className="relative p-2 text-gray-800 hover:text-gray-600"
			>
				<Bell className="w-5 h-5" />
				{unreadCount > 0 && (
					<span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full px-1">
						{unreadCount}
					</span>
				)}
			</button>

			{open && (
				<div className="absolute bottom-10 left-10 w-80 bg-white shadow-lg rounded-lg border border-gray-200 z-50">
					<div className="p-2 text-gray-700 font-semibold border-b">
						Notifications
					</div>
					<div className="max-h-64 overflow-y-auto">
						{notifications.length === 0 ? (
							<div className="p-3 text-sm text-gray-400">
								No notifications
							</div>
						) : (
							notifications.map((n) => (
								<div
									key={n.id}
									onClick={() => markAsRead(n.id)}
									className={`p-2 border-b text-sm cursor-pointer ${
										n.is_read ? "bg-gray-100" : "bg-blue-50"
									} hover:bg-gray-200`}
								>
									<p className="font-medium">
										{n.payload.project_name}
									</p>
									<p>{n.payload.task_title}</p>
									<p className="text-xs text-gray-500">
										Due {n.payload.duedate}
									</p>
								</div>
							))
						)}
					</div>
				</div>
			)}
		</div>
	);
};
