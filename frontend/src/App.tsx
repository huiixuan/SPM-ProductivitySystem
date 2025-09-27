import "./index.css";
import HomePage from "./pages/HomePage";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import Login from "./pages/Login";
import Register from "./pages/Register";
import ForgotPassword from './pages/ForgotPassword';


function App() {
	return (
		<BrowserRouter>
			<Routes>
				<Route path="/" element={<Login />} />
				<Route path="/register" element={<Register />} />
				<Route path="/HomePage" element={<HomePage />} />
				<Route path="/forgot-password" element={<ForgotPassword />} />
			</Routes>
		</BrowserRouter>
	);
}

export default App;


