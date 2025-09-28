import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";

export default function Login() {
	const [email, setEmail] = useState("");
	const [password, setPassword] = useState("");
	const [rememberMe, setRememberMe] = useState(false);
	const [error, setError] = useState("");
	const navigate = useNavigate();

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

				alert("Login successful!");
				navigate("/HomePage");
			} else {
				setError(data.error || "Invalid email or password");
			}
		} catch (err) {
			console.error("Login error:", err);
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
					Login
				</h1>

				{error && (
					<p
						style={{
							color: "red",
							fontSize: "0.9rem",
							marginBottom: "1rem",
						}}
					>
						{error}
					</p>
				)}

				<div style={{ marginBottom: "1rem" }}>
					<label
						htmlFor="email"
						style={{ display: "block", marginBottom: "0.5rem" }}
					>
						Email
					</label>
					<input
						id="email"
						type="text"
						value={email}
						onChange={(e) => setEmail(e.target.value)}
						required
						style={{
							width: "100%",
							padding: "0.5rem",
							border: "1px solid #ccc",
							borderRadius: "4px",
						}}
					/>
				</div>

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

				<div
					style={{
						display: "flex",
						justifyContent: "space-between",
						alignItems: "center",
						marginBottom: "1rem",
					}}
				>
					<label style={{ fontSize: "0.9rem" }}>
						<input
							type="checkbox"
							checked={rememberMe}
							onChange={(e) => setRememberMe(e.target.checked)}
							style={{ marginRight: "0.5rem" }}
						/>
						Remember me
					</label>
					<Link
						to="/forgot-password"
						style={{ fontSize: "0.9rem", color: "#2563eb" }}
					>
						Forgot Password?
					</Link>
				</div>

				<button
					type="submit"
					style={{
						width: "100%",
						backgroundColor: "#2563eb",
						color: "white",
						padding: "0.75rem",
						border: "none",
						borderRadius: "4px",
						cursor: "pointer",
						fontWeight: "bold",
					}}
				>
					Login
				</button>

				<p
					style={{
						textAlign: "center",
						marginTop: "1rem",
						fontSize: "0.9rem",
					}}
				>
					Don't have an account?{" "}
					<Link to="/register" style={{ color: "#2563eb" }}>
						Register
					</Link>
				</p>
			</form>
		</div>
	);
}
