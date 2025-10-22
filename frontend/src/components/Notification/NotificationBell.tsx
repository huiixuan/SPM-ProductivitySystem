import { useState, useEffect } from "react";
import { Bell } from "lucide-react";
import { useNavigate } from "react-router-dom";

interface NotificationPayload {
    project_name?: string;
    task_title?: string;
    comment_author?: string;
    comment_excerpt?: string;
    updated_fields?: Array<{
        field: string;
        old_value: string;
        new_value: string;
    }>;
    updated_by?: string;
    [key: string]: string | number | boolean | null | undefined | unknown[];
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

export const NotificationBell = () => {
    const [notifications, setNotifications] = useState<Notification[]>([]);
    const [open, setOpen] = useState(false);
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();

    const fetchNotifications = async () => {
        try {
            setLoading(true);
            const token = localStorage.getItem("token");
            if (!token) return;

            const response = await fetch("http://127.0.0.1:5000/api/notifications", {
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

    const handleNotificationClick = (notification: Notification) => {
        markAsRead(notification.id);

        // Navigate to task detail page
        navigate(`/tasks/${notification.task_id}`, {
            state: {
                highlightComment: notification.comment_id
            }
        });
        setOpen(false);
    };

    // Refresh notifications every 30 seconds
    useEffect(() => {
        fetchNotifications();

        const interval = setInterval(() => {
            fetchNotifications();
        }, 30000);

        return () => clearInterval(interval);
    }, []);

    const unreadCount = notifications.filter((n) => !n.is_read).length;

    return (
        <div className="relative">
            <button
                onClick={() => {
                    setOpen(!open);
                    fetchNotifications(); // Refresh when opening
                }}
                className="relative p-2 text-gray-800 hover:text-gray-600"
                disabled={loading}
            >
                <Bell className="w-5 h-5" />
                {unreadCount > 0 && (
                    <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full px-1 min-w-4 h-4 flex items-center justify-center">
                        {unreadCount}
                    </span>
                )}
            </button>

            {open && (
                <div className="absolute bottom-10 left-10 w-80 bg-white shadow-lg rounded-lg border border-gray-200 z-50">
                    <div className="p-2 text-gray-700 font-semibold border-b flex justify-between items-center">
                        <span>Notifications</span>
                        <button
                            onClick={() => navigate("/notifications")}
                            className="text-xs text-blue-500 hover:underline"
                        >
                            View All
                        </button>
                    </div>
                    <div className="max-h-64 overflow-y-auto">
                        {loading ? (
                            <div className="p-3 text-sm text-gray-400">Loading...</div>
                        ) : notifications.length === 0 ? (
                            <div className="p-3 text-sm text-gray-400">
                                No notifications
                            </div>
                        ) : (
                            notifications.slice(0, 5).map((n) => (
                                <div
                                    key={n.id}
                                    onClick={() => handleNotificationClick(n)}
                                    className={`p-3 border-b text-sm cursor-pointer ${n.is_read ? "bg-gray-50" : "bg-blue-50 border-l-4 border-l-blue-500"
                                        } hover:bg-gray-100 transition-colors`}
                                >
                                    <div className="flex justify-between items-start mb-1">
                                        <span className={`font-medium ${n.is_read ? "text-gray-600" : "text-gray-900"}`}>
                                            {n.payload.task_title || 'Task Update'}
                                        </span>
                                        <span className="text-xs text-gray-500">
                                            {new Date(n.created_at).toLocaleDateString()}
                                        </span>
                                    </div>
                                    <p className={`${n.is_read ? "text-gray-600" : "text-gray-800"} mb-1`}>
                                        {n.message}
                                    </p>
                                    {!n.is_read && (
                                        <div className="mt-1">
                                            <span className="inline-block w-2 h-2 bg-blue-500 rounded-full"></span>
                                        </div>
                                    )}
                                </div>
                            ))
                        )}
                    </div>
                </div>
            )}
        </div>
    );
};