import "@/index.css";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Toaster } from "sonner";
import HomePage from "@/pages/HomePage";
import Login from "@/pages/Login";
import Register from "@/pages/Register";
import ForgotPassword from "@/pages/ForgotPassword";
import TaskDashboard from "@/pages/TaskDashboard";

function App() {
	return (
		<>
			<Toaster position="top-center" richColors />
			<BrowserRouter>
				<Routes>
					<Route path="/" element={<Login />} />
					<Route path="/register" element={<Register />} />
					<Route path="/HomePage" element={<HomePage />} />
					{/* <Route path="/All-Tasks" element={<TaskDashboard />} /> */}
					<Route path="/schedule" element={<SchedulePage />} />
					<Route
						path="/forgot-password"
						element={<ForgotPassword />}
					/>
				</Routes>
			</BrowserRouter>
		</>
	);
}

export default App;
