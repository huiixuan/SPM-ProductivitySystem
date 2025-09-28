import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

export default function HomePage() {
	const [dashboard, setDashboard] = useState("");
	const navigate = useNavigate();

	useEffect(() => {
		const token = localStorage.getItem("token");
		const rememberMe = localStorage.getItem("rememberMe");

		// If no token and not remembered, redirect to login
		if (!token) {
			// Check if user was previously remembered but token expired
			if (rememberMe === "true") {
				// User expected to stay logged in but token is missing/expired
				alert("Your session has expired. Please login again.");
				localStorage.removeItem("rememberMe");
				localStorage.removeItem("rememberedEmail");
			}
			navigate("/");
			return;
		}

		fetch("http://127.0.0.1:5000/auth/dashboard", {
			headers: { Authorization: `Bearer ${token}` },
		})
			.then(async (res) => {
				const data = await res.json().catch(() => ({}));
				if (!res.ok) {
					// Token might be expired
					if (res.status === 401 || res.status === 422) {
						localStorage.removeItem("token");
						if (localStorage.getItem("rememberMe") === "true") {
							alert(
								"Your session has expired. Please login again."
							);
						}
						navigate("/");
						return;
					}
					throw new Error(data.error || "Unauthorized");
				}
				return data;
			})
			.then((data) => {
				if (!data) return; // Already handled redirect

				const role = (data.dashboard || "").toLowerCase();

				if (role === "staff")
					setDashboard("This is the Staff Dashboard");
				else if (role === "hr")
					setDashboard("This is the HR Dashboard");
				else if (role === "manager")
					setDashboard("This is the Manager Dashboard");
				else if (role === "director")
					setDashboard("This is the Director Dashboard");
				else setDashboard("Unauthorized access");
			})
			.catch((err) => {
				console.error("Dashboard error:", err);
				setDashboard(err.message);
			});
	}, [navigate]);

	const handleLogout = () => {
		// Clear all authentication data
		localStorage.removeItem("token");
		localStorage.removeItem("rememberMe");
		localStorage.removeItem("rememberedEmail");
		alert("Logged out successfully!");
		navigate("/");
	};

	return (
		<div style={{ padding: "2rem" }}>
			<h1>Dashboard</h1>
			<p>{dashboard}</p>

			{/* Show remember me status */}
			{localStorage.getItem("rememberMe") === "true" && (
				<p style={{ color: "green", fontStyle: "italic" }}>
					✓ You are staying logged in (1 week session)
				</p>
			)}

			<button
				onClick={handleLogout}
				style={{
					marginTop: "1rem",
					backgroundColor: "red",
					color: "white",
					padding: "0.5rem 1rem",
					border: "none",
					borderRadius: "4px",
					cursor: "pointer",
				}}
			>
				Logout
			</button>
		</div>
	);
}
