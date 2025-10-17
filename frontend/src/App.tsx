import "@/index.css";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Toaster } from "sonner";
import HomePage from "@/pages/HomePage";
import Login from "@/pages/Login";
import Register from "@/pages/Register";
import ForgotPassword from "@/pages/ForgotPassword";
import TaskDashboard from "@/pages/TaskDashboard";
import SchedulePage from "@/pages/SchedulePage";
import Layout from "@/layout";
import ProjectDashboard from '@/pages/ProjectDashboard'; 
import ProjectDetailPage from '@/pages/ProjectDetailPage';

function App() {
	return (
		<>
			<Toaster position="top-center" richColors />
			<BrowserRouter>
				<Routes>
					<Route path="/" element={<Login />} />
					<Route path="/register" element={<Register />} />
					<Route path="/forgot-password" element={<ForgotPassword />} />

					<Route 
						path="/HomePage" 
						element={
							<Layout>
								<HomePage />
							</Layout>
						} 
					/>

					<Route 
						path="/UserTasks" 
						element={
							<Layout>
								<TaskDashboard />
							</Layout>
						} 
					/>

					<Route 
						path="/schedule" 
						element={
							<Layout>
								<SchedulePage />
							</Layout>
						} 
					/>

					<Route path="/projects" 
					element={ 
						<Layout>
							<ProjectDashboard />
						</Layout>} /> 

        			<Route path="/projects/:projectId" 
					element={<ProjectDetailPage />} />
				</Routes>
			</BrowserRouter>
		</>
	);
}

export default App;
