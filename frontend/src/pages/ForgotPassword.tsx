import { useState } from "react";
import { Link } from "react-router-dom";

export default function ForgotPassword() {
    const [username, setUsername] = useState("");
    const [newPassword, setNewPassword] = useState("");
    const [message, setMessage] = useState("");

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!username || !newPassword) {
            setMessage("Both fields are required.");
            return;
        }

        try {
            const response = await fetch("http://127.0.0.1:5000/auth/forgot-password", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username, new_password: newPassword }),
            });

            const data = await response.json();

            if (response.ok) {
                setMessage("Password reset successful!");
                setUsername("");
                setNewPassword("");
            } else {
                setMessage(data.error || "Error resetting password");
            }
        } catch (err) {
            console.error("Password reset error:", err);
            setMessage("Server error. Please try again later.");
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
                    Reset Password
                </h1>

                {message && (
                    <p
                        style={{
                            color: message.includes("successful") ? "green" : "red",
                            fontSize: "0.9rem",
                            marginBottom: "1rem",
                            textAlign: "center",
                        }}
                    >
                        {message}
                    </p>
                )}

                <div style={{ marginBottom: "1rem" }}>
                    <label
                        htmlFor="username"
                        style={{ display: "block", marginBottom: "0.5rem", fontWeight: "500" }}
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

                <div style={{ marginBottom: "1.5rem" }}>
                    <label
                        htmlFor="newPassword"
                        style={{ display: "block", marginBottom: "0.5rem", fontWeight: "500" }}
                    >
                        New Password
                    </label>
                    <input
                        id="newPassword"
                        type="password"
                        value={newPassword}
                        onChange={(e) => setNewPassword(e.target.value)}
                        required
                        style={{
                            width: "100%",
                            padding: "0.5rem",
                            border: "1px solid #ccc",
                            borderRadius: "4px",
                        }}
                    />
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
                    Reset Password
                </button>

                <p
                    style={{
                        textAlign: "center",
                        marginTop: "1rem",
                        fontSize: "0.9rem",
                    }}
                >
                    Remember your password?{" "}
                    <Link to="/" style={{ color: "#2563eb" }}>
                        Login
                    </Link>
                </p>
            </form>
        </div>
    );
}