# Campus Events Portal

A simple web application to manage campus events, allowing administrators to create events and students to view and register for them.

---

## Features

- **Admin Portal**
  - Add new events with details like title, type, start/end time, location, and capacity.
  - View all created events and their popularity.
  
- **Student Portal**
  - Browse all available events in a clean, card-based layout.
  - Register for an event by entering basic information.
  - View a confirmation message once registration is successful.
  
- **Backend**
  - Built with Python Flask and SQLite.
  - Stores information about colleges, students, events, registrations, attendance, and feedback.
  - Provides APIs for event creation, student registration, and reporting.

- **Frontend**
  - Simple HTML, CSS, and JavaScript interface.
  - Responsive design for better usability.
  - Dynamic event list with interactive registration form.

---

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Flask (`pip install flask`)
- SQLite (comes with Python)

### Setup

1. Clone the repository:

   ```bash
   git clone <repository-url>
   cd campus-events
2. Install dependencies:

    pip install flask
3. Initialize the database:

    The database is automatically created when you run the app for the first time.

4. Run the application:

    python app.py


5. Open your browser:

    Admin portal: http://127.0.0.1:5000/admin

    Student portal: http://127.0.0.1:5000/student