import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "../components/ui/button";
import {
	Card,
	CardHeader,
	CardTitle,
	CardContent,
	CardFooter,
} from "../components/ui/card";

export default function Register() {
	const [role, setRole] = useState("");
	const [name, setName] = useState("");
	const [email, setEmail] = useState("");
	const [password, setPassword] = useState("");
	const [error, setError] = useState("");
	const navigate = useNavigate();
	const isValid = Boolean(
		name.trim() && role.trim() && email.trim() && password.trim()
	); // for button enable/disable

	const handleSubmit = async (e: React.FormEvent) => {
		e.preventDefault();

		if (!role) {
			setError("Please select a role.");
			return;
		}

		if (!name || !email || !password) {
			setError("All fields are required.");
			return;
		}

		try {
			const response = await fetch(
				"http://127.0.0.1:5000/auth/register",
				{
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({ name, role, email, password }),
				}
			);

			const data = await response.json();

			if (response.ok) {
				setError(""); // clear error if success
				localStorage.setItem("token", data.access_token);
				alert("Registration successful!");
				navigate("/HomePage"); // go back to Login
			} else {
				// Backend error (e.g. duplicate username)
				setError(
					data.error || "Registration failed. Please try again."
				);
			}
		} catch (err) {
			console.error("Error registering user:", err);
			setError("Server error. Please try again later.");
		}
	};

	return (
		<div className="fixed inset-0 grid place-items-center">
			<Card className="w-full max-w-sm mx-4">
				<CardHeader>
					<CardTitle className="text-center text-2xl">
						Register
					</CardTitle>
				</CardHeader>

				<CardContent>
					{error && (
						<p className="text-red-500 text-sm mb-4">{error}</p>
					)}

					<form onSubmit={handleSubmit} className="space-y-4">
						{/* Role Selection */}
						<div>
							<p className="mb-2 font-medium">I am a:</p>
							<div className="flex justify-between">
								{["STAFF", "MANAGER", "DIRECTOR", "HR"].map(
									(r) => (
										<Button
											key={r}
											type="button"
											onClick={() => setRole(r)}
											className={`flex-1 ${
												role === r ? "font-bold" : ""
											}`}
										>
											{r.charAt(0).toUpperCase() +
												r.slice(1)}
										</Button>
									)
								)}
							</div>
						</div>

						{/* Name */}
						<div style={{ marginBottom: "1rem" }}>
							<label
								htmlFor="name"
								style={{
									display: "block",
									marginBottom: "0.5rem",
								}}
							>
								Name
							</label>
							<input
								id="name"
								type="text"
								value={name}
								onChange={(e) => setName(e.target.value)}
								required
								style={{
									width: "100%",
									padding: "0.5rem",
									border: "1px solid #ccc",
									borderRadius: "4px",
								}}
							/>
						</div>

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

						<Button
							type="submit"
							className={`w-full ${isValid ? "font-bold " : ""}`}
						>
							Register
						</Button>
					</form>
				</CardContent>

				<CardFooter className="flex justify-center">
					<p className="text-sm">
						Already have an account?{" "}
						<Link to="/" className="text-blue-500 hover:underline">
							Login
						</Link>
					</p>
				</CardFooter>
			</Card>
		</div>
	);
}
