# Design notes

## Data structures and object-oriented design
- `CAMPUSES` is a dictionary holding campus-specific booking policies.
- Lists and tuples hold starter resource records and demo accounts.
- `Database` encapsulates SQLite operations.
- `User` is the base class; `Lecturer`, `CampusAdministrator`, and `SystemOperator` inherit from it.
- The GUI checks roles before exposing privileged actions.

## Database tables
- `users`: username, password hash, role, and home campus.
- `campuses`: campus name and policy values.
- `resources`: unique resource code, name, campus, and capacity.
- `bookings`: user, resource, campus, date, start time, duration, and status.

## Booking validation
- A booking must use a date that is not in the past.
- Duration must be positive and within the active campus's maximum.
- Booking times must fit within the campus operating hours.
- Active bookings for the same resource may not overlap.
- Only the owner can cancel their own future booking through the lecturer view.

## Suggested manual tests
1. Log in using each demo account and check that role-specific buttons differ.
2. Register a new lecturer, log out, and log in with the new account.
3. Add a resource with a new code, then try adding the same code again.
4. Create a booking inside the campus policy window.
5. Try a booking that exceeds the duration limit or operating hours.
6. Try two bookings for the same resource with overlapping times.
7. Cancel a future active booking and confirm its status changes.
8. Close and reopen the program; confirm users, resources, and bookings remain.
9. Compare reports for Johannesburg, Pretoria and Durban.
