import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

export default function Register() {
	const [role, setRole] = useState("");
	const [name, setName] = useState("");
	const [username, setUsername] = useState("");
	const [password, setPassword] = useState("");
	const [error, setError] = useState("");
	const navigate = useNavigate();

	const handleSubmit = async (e: React.FormEvent) => {
		e.preventDefault();

		if (!role) {
			setError("Please select a role.");
			return;
		}

		if (!name || !username || !password) {
			setError("All fields are required.");
			return;
		}

		try {
			const response = await fetch(
				"http://127.0.0.1:5000/auth/register",
				{
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({ role, name, username, password }),
				}
			);

			const data = await response.json();

			if (response.ok) {
				setError(""); // clear error if success
				alert("Registration successful!");
				navigate("/"); // go back to Login
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
		<div
			style={{
				display: "flex",
				justifyContent: "center",
				alignItems: "center",
				height: "100vh",
				width: "100vw",
				backgroundColor: "#f3f4f6",
			}}
		>
			<form
				onSubmit={handleSubmit}
				style={{
					background: "white",
					padding: "2rem",
					borderRadius: "8px",
					boxShadow: "0 4px 6px rgba(0,0,0,0.1)",
					width: "100%",
					maxWidth: "400px",
				}}
			>
				<h1
					style={{
						textAlign: "center",
						fontSize: "2rem",
						fontWeight: "bold",
						marginBottom: "1.5rem",
					}}
				>
					Register
				</h1>

				{/* Role */}
				<div style={{ marginBottom: "1.5rem" }}>
					<p style={{ marginBottom: "0.5rem", fontWeight: "500" }}>
						I am a:
					</p>
					<div
						style={{
							display: "flex",
							justifyContent: "space-between",
						}}
					>
						{["Staff", "Manager", "Director", "HR"].map((r) => (
							<button
								type="button"
								key={r}
								onClick={() => setRole(r)}
								style={{
									flex: 1,
									margin: "0 0.25rem",
									padding: "0.5rem",
									borderRadius: "4px",
									border:
										role === r
											? "2px solid #2563eb"
											: "1px solid #ccc",
									backgroundColor:
										role === r ? "#2563eb" : "white",
									color: role === r ? "white" : "black",
									cursor: "pointer",
									fontWeight: role === r ? "bold" : "normal",
								}}
							>
								{r}
							</button>
						))}
					</div>
				</div>

				{/* Name */}
				<div style={{ marginBottom: "1rem" }}>
					<label
						htmlFor="name"
						style={{ display: "block", marginBottom: "0.5rem" }}
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

				{/* Username */}
				<div style={{ marginBottom: "1rem" }}>
					<label
						htmlFor="username"
						style={{ display: "block", marginBottom: "0.5rem" }}
					>
						Username
					</label>
					<input
						id="username"
						type="text"
						value={username}
						onChange={(e) => setUsername(e.target.value)}
						required
						style={{
							width: "100%",
							padding: "0.5rem",
							border: "1px solid #ccc",
							borderRadius: "4px",
						}}
					/>
				</div>

				{/* Password */}
				<div style={{ marginBottom: "1rem" }}>
					<label
						htmlFor="password"
						style={{ display: "block", marginBottom: "0.5rem" }}
					>
						Password
					</label>
					<input
						id="password"
						type="password"
						value={password}
						onChange={(e) => setPassword(e.target.value)}
						required
						style={{
							width: "100%",
							padding: "0.5rem",
							border: "1px solid #ccc",
							borderRadius: "4px",
						}}
					/>
				</div>

				{/* Error message */}
				{error && (
					<p
						style={{
							color: "red",
							fontSize: "0.85rem",
							marginBottom: "1rem",
						}}
					>
						{error}
					</p>
				)}

				{/* Submit */}
				<button
					type="submit"
					style={{
						width: "100%",
						backgroundColor: "#16a34a",
						color: "white",
						padding: "0.75rem",
						border: "none",
						borderRadius: "4px",
						cursor: "pointer",
						fontWeight: "bold",
					}}
				>
					Register
				</button>

				{/* Back to Login */}
				<p
					style={{
						textAlign: "center",
						marginTop: "1rem",
						fontSize: "0.9rem",
					}}
				>
					Already have an account?{" "}
					<Link to="/" style={{ color: "#2563eb" }}>
						Login
					</Link>
				</p>
			</form>
		</div>
	);
}
