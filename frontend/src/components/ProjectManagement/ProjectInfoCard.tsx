import { useNavigate } from "react-router-dom";
import {
	Card,
	CardContent,
	CardDescription,
	CardFooter,
	CardHeader,
	CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

// Define the shape of the project data this card expects
interface Project {
	id: number;
	name: string;
	deadline: string;
	status: string;
	owner_email: string;
}

interface UserData {
	role: string;
	email: string;
}

interface ProjectInfoCardProps {
	project: Project;
	currentUserData?: UserData; // Optional for backward compatibility
	onUpdate?: (project: Project) => void; // Optional callback for updates
}

export default function ProjectInfoCard({ project }: ProjectInfoCardProps) {
	const navigate = useNavigate(); // Hook for navigation

	// When the card is clicked, go to the project's detail page
	const handleCardClick = () => {
		navigate(`/projects/${project.id}`);
	};

	const badgeColor: Record<string, string> = {
		"Not Started": "bg-gray-400",
		"In Progress": "bg-blue-400",
		Completed: "bg-emerald-400",
	};

	if (!project) return null;

	return (
		// We removed the UpdateProjectDialog from here entirely
		<Card
			className="cursor-pointer hover:shadow-lg transition-shadow"
			onClick={handleCardClick}
		>
			<CardHeader>
				<CardTitle>{project.name}</CardTitle>
				<CardDescription>Owner: {project.owner_email}</CardDescription>
			</CardHeader>
			<CardContent>
				{project.deadline && (
					<p className="text-sm text-gray-600">
						Deadline:{" "}
						{new Date(project.deadline).toLocaleDateString()}
					</p>
				)}
			</CardContent>
			<CardFooter>
				<Badge className={`${badgeColor[project.status]} text-white`}>
					{project.status}
				</Badge>
			</CardFooter>
		</Card>
	);
}
