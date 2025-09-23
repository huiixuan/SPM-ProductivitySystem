import "./index.css";
import { useState } from "react";
import HomePage from "@/pages/HomePage";
import Login from "@/pages/Login";
import Register from "@/pages/Register";

function App() {
	const [showLogin, setShowLogin] = useState(true);

	return showLogin ? (
		<Login onSwitchToRegister={() => setShowLogin(false)} />
	) : (
		<Register onSwitchToLogin={() => setShowLogin(true)} />
	);
}

export default App;
