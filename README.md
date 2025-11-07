# SPM project
A productivity system that allows users to manage tasks, projects, and collaborations.

## Setup and Installation
### Backend (Flask)
1. Navigate to backend folder:
```
cd backend
```

2. Create virtual environment:
```
python -m venv venv
source venv/bin/activate # Linux/macOs
venv\Scripts\activate    # Windows
```

3. Install dependencies:
```
pip install -r requirements.txt
```

4. Set environment variables:
The backend requires certain environment variables to run. Create a .env file in the backend/ folder with the following variables:
```
DB_NAME = spm_database
DB_PASSWORD = your_db_password
DB_USER = postgres
DB_HOST = localhost
DB_PORT = 5432

POWER_AUTOMATE_WEBHOOK_URL=https://defaultc98a79ca5a9a4791a243f06afd6746.4d.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/f4ec69193eec41e08a470e91b628a035/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=cdqL6YTsclWQeTHn2h7PL1mhA5wX5JAAeNwxL9Qmb5Q
```
Note:
* Replace your_db_password with your actual database password.
* Make sure your PostgreSQL database is running and accessible with the above credentials.

5. Run the backend server:
```
python app.py
```

### Frontend (React + Vite)
1. Navigate to frontend folder:
```
cd frontend
```

2. Install dependencies:
```
npm install
```

3. Run the frontend server:
```
npm run dev
```
* The app will usually be available at http://localhost:5173

## Testing
All tests are located in the backend/tests/ directory. To run the tests:
```
cd backend
pytest tests/
```

Link to github repo: https://github.com/huiixuan/SPM-ProductivitySystem.git