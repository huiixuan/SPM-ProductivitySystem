import { useState, useEffect, useCallback, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
	Popover,
	PopoverContent,
	PopoverTrigger,
} from "@/components/ui/popover";
import { Textarea } from "@/components/ui/textarea";
import { Send, User } from "lucide-react";

interface Comment {
	id: number;
	content: string;
	user_id: number;
	user_email: string;
	created_at: string;
}

interface CommentsSectionProps {
	taskId: number;
	highlightComment?: number;
}

interface UserData {
	id: number;
	role: string;
	name: string;
	email: string;
}

export default function CommentsSection({
	taskId,
	highlightComment,
}: CommentsSectionProps) {
	const [comments, setComments] = useState<Comment[]>([]);
	const [newComment, setNewComment] = useState("");
	const [loading, setLoading] = useState(false);
	const [users, setUsers] = useState<UserData[]>([]);
	const [showDropdown, setShowDropdown] = useState(false);
	const [filteredUsers, setFilteredUsers] = useState<UserData[]>([]);
	const [cursorPosition, setCursorPosition] = useState(0);

	const textareaRef = useRef<HTMLTextAreaElement>(null);

	const token = localStorage.getItem("token");

	const fetchComments = useCallback(async () => {
		try {
			const response = await fetch(
				`/api/comments/get-comments/${taskId}`,
				{
					headers: { Authorization: `Bearer ${token}` },
				}
			);
			if (response.ok) {
				const data = await response.json();
				setComments(data);
			}
		} catch (error) {
			console.error("Failed to fetch comments:", error);
		}
	}, [taskId, token]);

	const getAllUsers = useCallback(async () => {
		try {
			const res = await fetch(
				`/api/task/get-project-users-for-task/${taskId}`,
				{
					headers: { Authorization: `Bearer ${token}` },
				}
			);

			if (!res.ok) throw new Error("Failed to fetch users.");

			const data = await res.json();
			setUsers(data);
		} catch (error) {
			console.error(error);
		}
	}, [taskId, token]);

	useEffect(() => {
		fetchComments();
		getAllUsers();
	}, [fetchComments, getAllUsers]);

	useEffect(() => {
		if (highlightComment) {
			const element = document.getElementById(
				`comment-${highlightComment}`
			);
			if (element) {
				element.scrollIntoView({ behavior: "smooth", block: "center" });
				element.classList.add(
					"bg-yellow-100",
					"border-l-4",
					"border-l-yellow-500"
				);
				setTimeout(() => {
					element.classList.remove(
						"bg-yellow-100",
						"border-l-4",
						"border-l-yellow-500"
					);
				}, 3000);
			}
		}
	}, [highlightComment, comments]);

	const handleTextareaChange = (
		e: React.ChangeEvent<HTMLTextAreaElement>
	) => {
		const val = e.target.value;
		const cursor = e.target.selectionStart;
		setNewComment(val);
		setCursorPosition(cursor);

		const textBeforeCursor = val.slice(0, cursor);
		const match = textBeforeCursor.match(/@(\w*)$/);
		if (match) {
			const q = match[1];
			const filtered = users.filter((u) =>
				u.name.toLowerCase().includes(q.toLowerCase())
			);

			setFilteredUsers(filtered);
			setShowDropdown(true);
		} else {
			setShowDropdown(false);
		}
	};

	const selectUser = (user: UserData) => {
		const textBeforeCursor = newComment.slice(0, cursorPosition);
		const textAfterCursor = newComment.slice(cursorPosition);
		const newText =
			textBeforeCursor.replace(/@(\w*)$/, `@${user.name} `) +
			textAfterCursor;
		setNewComment(newText);
		setShowDropdown(false);

		const newCursor = textBeforeCursor.replace(
			/@(\w*)$/,
			`@${user.name} `
		).length;
		setCursorPosition(newCursor);
		textareaRef.current?.focus();
		textareaRef.current?.setSelectionRange(newCursor, newCursor);
	};

	const submitComment = async () => {
		if (!newComment.trim()) return;

		setLoading(true);
		try {
			const response = await fetch(
				`/api/comments/save-comment/${taskId}`,
				{
					method: "POST",
					headers: {
						"Content-Type": "application/json",
						Authorization: `Bearer ${token}`,
					},
					body: JSON.stringify({ content: newComment }),
				}
			);
			if (response.ok) {
				setNewComment("");
				fetchComments();
			} else {
				console.error("Failed to submit comment");
			}
		} catch (error) {
			console.error("Error submitting comment:", error);
		} finally {
			setLoading(false);
		}
	};

	return (
		<Card>
			<CardHeader>
				<CardTitle className="flex items-center gap-2">
					💬 Comments ({comments.length})
				</CardTitle>
			</CardHeader>

			<CardContent>
				{/* Comment Input */}
				<div className="mb-6 w-full">
					<Popover
						open={showDropdown}
						onOpenChange={() => setShowDropdown(false)}
					>
						<PopoverTrigger asChild>
							<Textarea
								ref={textareaRef}
								placeholder="Add a comment..."
								value={newComment}
								onChange={handleTextareaChange}
								className="w-full border rounded p-2 min-h-[80px]"
							/>
						</PopoverTrigger>

						<PopoverContent
							side="bottom"
							align="start"
							className="w-full text-sm z-50 p-2 max-h-40 overflow-y-auto"
						>
							{filteredUsers.map((user, index) => (
								<div
									key={user.id}
									onClick={() => selectUser(user)}
									className={`p-1 w-full ${
										index === filteredUsers.length - 1
											? ""
											: "border-b"
									}`}
								>
									{user.name} - {user.email}
								</div>
							))}
						</PopoverContent>
					</Popover>

					<Button
						onClick={submitComment}
						disabled={loading || !newComment.trim()}
						className="flex items-center gap-2 mt-2"
					>
						<Send className="h-4 w-4" />
						{loading ? "Posting..." : "Post Comment"}
					</Button>
				</div>

				{/* Comments List */}
				<div className="space-y-4">
					{comments.map((comment) => (
						<div
							key={comment.id}
							id={`comment-${comment.id}`}
							className="p-4 border rounded-lg transition-all"
						>
							<div className="flex items-start gap-3">
								<div className="flex-shrink-0">
									<div className="w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center">
										<User className="h-4 w-4 text-gray-600" />
									</div>
								</div>

								<div className="flex-1">
									<div className="flex items-center gap-2 mb-1">
										<span className="font-medium text-sm">
											{comment.user_email}
										</span>
										<span className="text-xs text-gray-500">
											{new Date(
												comment.created_at
											).toLocaleString()}
										</span>
									</div>

									<p className="text-gray-700 whitespace-pre-wrap">
										{comment.content}
									</p>
								</div>
							</div>
						</div>
					))}

					{comments.length === 0 && (
						<div className="text-center py-8 text-gray-500">
							<p>No comments yet</p>
							<p className="text-sm">
								Be the first to comment on this task.
							</p>
						</div>
					)}
				</div>
			</CardContent>
		</Card>
	);
}
