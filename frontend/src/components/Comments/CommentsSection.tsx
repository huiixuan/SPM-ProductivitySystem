import { useState, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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

export default function CommentsSection({ taskId, highlightComment }: CommentsSectionProps) {
	const [comments, setComments] = useState<Comment[]>([]);
	const [newComment, setNewComment] = useState("");
	const [loading, setLoading] = useState(false);

	const fetchComments = useCallback(async () => {
		try {
			const token = localStorage.getItem("token");
			const response = await fetch(`/api/comments/task/${taskId}`, {
				headers: { Authorization: `Bearer ${token}` },
			});
			if (response.ok) {
				const data = await response.json();
				setComments(data);
			}
		} catch (error) {
			console.error("Failed to fetch comments:", error);
		}
	}, [taskId]);

	const submitComment = async () => {
		if (!newComment.trim()) return;

		setLoading(true);
		try {
			const token = localStorage.getItem("token");
			const response = await fetch(`/api/comments/task/${taskId}`, {
				method: "POST",
				headers: {
					"Content-Type": "application/json",
					Authorization: `Bearer ${token}`,
				},
				body: JSON.stringify({ content: newComment }),
			});

			if (response.ok) {
				setNewComment("");
				fetchComments(); // Refresh comments
			} else {
				console.error("Failed to submit comment");
			}
		} catch (error) {
			console.error("Error submitting comment:", error);
		} finally {
			setLoading(false);
		}
	};

	useEffect(() => {
		fetchComments();
	}, [fetchComments]);

	useEffect(() => {
		if (highlightComment) {
			const element = document.getElementById(`comment-${highlightComment}`);
			if (element) {
				element.scrollIntoView({ behavior: "smooth", block: "center" });
				element.classList.add("bg-yellow-100", "border-l-4", "border-l-yellow-500");
				setTimeout(() => {
					element.classList.remove("bg-yellow-100", "border-l-4", "border-l-yellow-500");
				}, 3000);
			}
		}
	}, [highlightComment, comments]);

	return (
		<Card>
			<CardHeader>
				<CardTitle className="flex items-center gap-2">
					💬 Comments ({comments.length})
				</CardTitle>
			</CardHeader>
			<CardContent>
				{/* Comment Input */}
				<div className="mb-6">
					<Textarea
						placeholder="Add a comment..."
						value={newComment}
						onChange={(e) => setNewComment(e.target.value)}
						className="mb-2"
						rows={3}
					/>
					<Button
						onClick={submitComment}
						disabled={loading || !newComment.trim()}
						className="flex items-center gap-2"
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
											{new Date(comment.created_at).toLocaleString()}
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
							<p className="text-sm">Be the first to comment on this task.</p>
						</div>
					)}
				</div>
			</CardContent>
		</Card>
	);
}