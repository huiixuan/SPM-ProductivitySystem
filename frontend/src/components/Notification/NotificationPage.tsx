import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CheckCircle, Circle, Bell } from "lucide-react";

interface NotificationPayload {
	task_title: string;
	project_name?: string;
	[key: string]: unknown;
}

interface Notification {
	id: number;
	message: string;
	is_read: boolean;
	created_at: string;
	payload: NotificationPayload;
	type: string;
	task_id: number;
	comment_id?: number;
}

export default function NotificationPage() {
	const [notifications, setNotifications] = useState<Notification[]>([]);
	const [loading, setLoading] = useState(true);
	const navigate = useNavigate();

	const fetchNotifications = async () => {
		try {
			const token = localStorage.getItem("token");
			if (!token) return;

			const response = await fetch("/api/notifications", {
				headers: { Authorization: `Bearer ${token}` },
			});

			if (response.ok) {
				const data = await response.json();
				setNotifications(data);
			} else {
				console.error("Failed to fetch notifications");
			}
		} catch (err) {
			console.error("Error fetching notifications:", err);
		} finally {
			setLoading(false);
		}
	};

	const markAsRead = async (id: number) => {
		try {
			const token = localStorage.getItem("token");
			if (!token) return;

			await fetch(`/api/notifications/${id}/read`, {
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

	const markAllAsRead = async () => {
		try {
			const token = localStorage.getItem("token");
			if (!token) return;

			await fetch("/api/notifications/read-all", {
				method: "PATCH",
				headers: { Authorization: `Bearer ${token}` },
			});

			setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
		} catch (err) {
			console.error("Error marking all as read:", err);
		}
	};

	const handleNotificationClick = (notification: Notification) => {
		markAsRead(notification.id);
		navigate(`/tasks/${notification.task_id}`, {
			state: {
				highlightComment: notification.comment_id
			}
		});
	};

	const getNotificationIcon = (type: string) => {
		switch (type) {
			case 'due_date_reminder':
				return '📅';
			case 'new_comment':
				return '💬';
			case 'task_updated':
				return '✏️';
			default:
				return '🔔';
		}
	};

	const getTypeBadge = (type: string) => {
		const typeMap: { [key: string]: { label: string, variant: "default" | "secondary" | "outline" } } = {
			'due_date_reminder': { label: 'Due Date', variant: 'default' },
			'new_comment': { label: 'Comment', variant: 'secondary' },
			'task_updated': { label: 'Update', variant: 'outline' }
		};

		const config = typeMap[type] || { label: type, variant: 'outline' };
		return <Badge variant={config.variant}>{config.label}</Badge>;
	};

	useEffect(() => {
		fetchNotifications();
	}, []);

	if (loading) {
		return (
			<div className="container mx-auto p-6">
				<div className="text-center">Loading notifications...</div>
			</div>
		);
	}

	const unreadCount = notifications.filter(n => !n.is_read).length;

	return (
		<div className="container mx-auto p-6 max-w-4xl">
			<Card>
				<CardHeader>
					<div className="flex justify-between items-center">
						<CardTitle className="flex items-center gap-2">
							<Bell className="h-6 w-6" />
							Notifications
							{unreadCount > 0 && (
								<Badge variant="destructive" className="ml-2">
									{unreadCount} unread
								</Badge>
							)}
						</CardTitle>
						{unreadCount > 0 && (
							<Button
								onClick={markAllAsRead}
								variant="outline"
								size="sm"
								className="flex items-center gap-2"
							>
								<CheckCircle className="h-4 w-4" />
								Mark all as read
							</Button>
						)}
					</div>
				</CardHeader>
				<CardContent>
					<div className="space-y-4">
						{notifications.length === 0 ? (
							<div className="text-center py-8 text-gray-500">
								<Bell className="h-12 w-12 mx-auto mb-4 text-gray-300" />
								<p>No notifications yet</p>
								<p className="text-sm">You'll see notifications here when you have new comments or task updates.</p>
							</div>
						) : (
							notifications.map((notification) => (
								<div
									key={notification.id}
									onClick={() => handleNotificationClick(notification)}
									className={`p-4 border rounded-lg cursor-pointer transition-all ${notification.is_read
											? "bg-gray-50 border-gray-200 hover:bg-gray-100"
											: "bg-blue-50 border-blue-200 hover:bg-blue-100 border-l-4 border-l-blue-500"
										}`}
								>
									<div className="flex items-start justify-between">
										<div className="flex items-start gap-3 flex-1">
											<div className="text-lg mt-1">
												{getNotificationIcon(notification.type)}
											</div>
											<div className="flex-1">
												<div className="flex items-center gap-2 mb-2">
													<h3 className={`font-medium ${notification.is_read ? "text-gray-700" : "text-gray-900"
														}`}>
														{notification.payload.task_title}
													</h3>
													{getTypeBadge(notification.type)}
												</div>
												<p className="text-sm text-gray-600 mb-1">
													{notification.payload.project_name || 'Task'}
												</p>
												<p className="text-gray-700">
													{notification.message}
												</p>
												<p className="text-xs text-gray-500 mt-2">
													{new Date(notification.created_at).toLocaleString()}
												</p>
											</div>
										</div>
										<div className="flex items-center gap-2">
											{!notification.is_read && (
												<button
													onClick={(e) => {
														e.stopPropagation();
														markAsRead(notification.id);
													}}
													className="p-1 hover:bg-white rounded transition-colors"
													title="Mark as read"
												>
													<Circle className="h-4 w-4 text-blue-500" />
												</button>
											)}
											{notification.is_read && (
												<CheckCircle className="h-4 w-4 text-green-500" />
											)}
										</div>
									</div>
								</div>
							))
						)}
					</div>
				</CardContent>
			</Card>
		</div>
	);
}