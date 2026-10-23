# Smart Campus Resource Booking System

A Python desktop application for the Programming 512 case study. It uses Tkinter for the GUI and SQLite for persistent storage. It requires Python 3.10+ and no third-party packages.

## Run the project
1. Extract the ZIP file to a normal folder.
2. Install Python 3.10 or later from https://www.python.org/downloads/ if it is not installed. On Windows, tick **Add Python to PATH**.
3. Open the extracted folder in PyCharm.
4. Open `app.py` and run it, or open a terminal in the folder and run:
   `python app.py`
5. The SQLite database `smart_campus.db` is created automatically beside `app.py`.

## Demo accounts
- Lecturer: `lecturer` / `Learn123!`
- Campus administrator: `admin_jhb` / `Admin123!`
- System operator: `operator` / `Operator123!`

These accounts are for demonstration only. Do not use these credentials for a real system.

## Included functionality
- Lecturer registration and login
- Role-based screens for lecturers, campus administrators and system operators
- Three campuses with different booking duration and operating-hour policies
- Resource registration, updates and removal, with unique resource codes
- Booking creation with date/time validation and overlap checks
- Lecturer booking history and cancellation of future bookings
- SQLite persistence
- Campus reports: booking totals, average active booking duration and resource usage counts
- Cross-campus resource and booking comparison for the system operator

## Project files
- `app.py` — application, GUI, data model, database logic and validation
- `README.md` — setup and usage notes
- `requirements.txt` — no external dependencies required
- `design_notes.md` — brief design explanation and testing checklist

## Important academic note
Review the code, test it on your own computer, and customise it in ways you understand before submitting. The case study states that copied solutions are prohibited, so make sure your final submission reflects your own understanding and follows your lecturer's rules. The demo accounts and policy values are sample choices and may be changed to match your class requirements.
