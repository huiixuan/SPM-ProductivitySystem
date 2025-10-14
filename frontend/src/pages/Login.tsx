import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import {
	Card,
	CardHeader,
	CardTitle,
	CardContent,
	CardFooter,
} from "@/components/ui/card";
import { toast } from "sonner";

export default function Login() {
	const [email, setEmail] = useState("");
	const [password, setPassword] = useState("");
	const [rememberMe, setRememberMe] = useState(false);
	const [error, setError] = useState("");
	const navigate = useNavigate();
	const isValid = Boolean(email.trim() && password.trim()); // for button enable/disable

	// Load saved credentials when the page loads
	useEffect(() => {
		const savedEmail = localStorage.getItem("savedEmail");
		const savedPassword = localStorage.getItem("savedPassword");
		if (savedEmail && savedPassword) {
			setEmail(savedEmail);
			setPassword(savedPassword);
			setRememberMe(true);
		}
	}, []);

	const handleSubmit = async (e: React.FormEvent) => {
		e.preventDefault();

		if (!email || !password) {
			setError("Both fields are required.");
			return;
		}

		try {
			const response = await fetch("http://127.0.0.1:5000/auth/login", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ email, password }),
			});

			const data = await response.json();

			if (response.ok) {
				setError("");
				localStorage.setItem("token", data.access_token); // save JWT

				// Save or clear credentials depending on Remember Me
				if (rememberMe) {
					localStorage.setItem("savedEmail", email);
					localStorage.setItem("savedPassword", password);
				} else {
					localStorage.removeItem("savedEmail");
					localStorage.removeItem("savedPassword");
				}

				toast.success("Login successful!");
				navigate("/HomePage");
			} else {
				setError(data.error || "Invalid username or password");
			}
		} catch (err) {
			console.error("Login error:", err);
			setError("Server error. Please try again later.");
		}
	};

	return (
		<div className="fixed inset-0 grid place-items-center">
			<Card className="w-full max-w-sm mx-4">
				<CardHeader>
					<CardTitle className="text-center text-2xl">
						Login
					</CardTitle>
				</CardHeader>

				<CardContent>
					{error && (
						<p className="text-red-500 text-sm mb-4">{error}</p>
					)}

					<form onSubmit={handleSubmit} className="space-y-4">
						{/* Email */}
						<div>
							<label
								htmlFor="email"
								className="block text-sm font-medium mb-1"
							>
								Email
							</label>
							<input
								id="email"
								type="email"
								value={email}
								onChange={(e) => setEmail(e.target.value)}
								className="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring focus:ring-blue-500"
							/>
						</div>

						{/* Password */}
						<div>
							<label
								htmlFor="password"
								className="block text-sm font-medium mb-1"
							>
								Password
							</label>
							<input
								id="password"
								type="password"
								value={password}
								onChange={(e) => setPassword(e.target.value)}
								className="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring focus:ring-blue-500"
							/>
						</div>

						{/* Remember me + Forgot password */}
						<div className="flex items-center justify-between">
							<label className="flex items-center text-sm">
								<input
									type="checkbox"
									checked={rememberMe}
									onChange={(e) =>
										setRememberMe(e.target.checked)
									}
									className="mr-2"
								/>
								Remember me
							</label>
							<Link
								to="/forgot-password"
								className="text-sm text-blue-500 hover:underline"
							>
								Forgot Password?
							</Link>
						</div>

						<Button
							type="submit"
							disabled={!isValid}
							className={`w-full ${isValid ? "font-bold " : ""}`}
						>
							Login
						</Button>
					</form>
				</CardContent>

				<CardFooter className="flex justify-center">
					<p className="text-sm">
						Don’t have an account?{" "}
						<Link
							to="/register"
							className="text-blue-500 hover:underline"
						>
							Register
						</Link>
					</p>
				</CardFooter>
			</Card>
		</div>
	);
}
