# Student Internship Opportunity Tracker

A full-stack, responsive web application for students to organize internship opportunities, manage application stages, track deadlines, and maintain a preparation checklist.

## Features
- Student registration and login with hashed passwords
- Personal dashboard with application statistics and upcoming deadlines
- Add, edit, delete, search and filter internship opportunities
- Track statuses: Interested, Applied, Assessment, Interview, Offer, Rejected, Withdrawn
- Priority, work mode, stipend, skills, source link, notes and deadline fields
- Preparation checklist for documents, profile and interview readiness
- Reports page with status breakdown and offer conversion rate
- Profile editing
- SQLite database created automatically
- Responsive layout for desktop, tablet and mobile
- User data is scoped to the signed-in account

## Requirements
- Python 3.10 or newer
- Internet connection only if pip needs to download Flask

## Run on Windows (VS Code or Command Prompt)
1. Extract the ZIP file.
2. Open the extracted `student_internship_tracker` folder in VS Code using **File → Open Folder**.
3. Open Terminal → New Terminal.
4. Create a virtual environment:
   ```bat
   py -m venv .venv
   ```
5. Activate it:
   ```bat
   .venv\Scripts\activate
   ```
6. Install dependencies:
   ```bat
   pip install -r requirements.txt
   ```
7. Start the app:
   ```bat
   python app.py
   ```
8. Open **http://127.0.0.1:5000** in your browser.
9. Select **Create free account** and register.

## Run on macOS / Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

## Database
The app creates `tracker.db` in the project folder on first run. Back it up before moving or deleting it. To reset the local demo database, stop the server and delete `tracker.db`; it will be recreated on the next run.

## Project structure
```text
student_internship_tracker/
├── app.py
├── requirements.txt
├── README.md
├── templates/
│   ├── base.html
│   ├── landing.html
│   ├── auth.html
│   ├── dashboard.html
│   ├── opportunities.html
│   ├── opportunity_form.html
│   ├── checklist.html
│   ├── reports.html
│   ├── profile.html
│   └── 404.html
└── static/
    ├── css/style.css
    └── js/app.js
```

## Important production notes
This is a runnable academic project starter. Before public deployment, set a strong `SECRET_KEY`, use HTTPS, add CSRF protection and rate limiting, configure secure cookies, and run behind a production WSGI server. Never use Flask debug mode on a public server.
