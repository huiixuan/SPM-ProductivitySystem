import { useState } from "react";

export default function Login() {
	const [username, setUsername] = useState("");
	const [password, setPassword] = useState("");
	const [rememberMe, setRememberMe] = useState(false);

	const handleSubmit = (e: React.FormEvent) => {
		e.preventDefault();
		console.log({ username, password, rememberMe });
		// Later: call your Flask backend here
	};

	return (
		<div
			style={{
				display: "flex",
				justifyContent: "center",
				alignItems: "center",
				height: "100vh", // full viewport height
				width: "100vw", // full viewport width
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

				{/* Remember me + Forgot password */}
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
					<a
						href="#"
						style={{ fontSize: "0.9rem", color: "#2563eb" }}
					>
						Forgot Password?
					</a>
				</div>

				{/* Submit button */}
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

				{/* Register link */}
				<p
					style={{
						textAlign: "center",
						marginTop: "1rem",
						fontSize: "0.9rem",
					}}
				>
					Don’t have an account?{" "}
					<a href="#" style={{ color: "#2563eb" }}>
						Register
					</a>
				</p>
			</form>
		</div>
	);
}
