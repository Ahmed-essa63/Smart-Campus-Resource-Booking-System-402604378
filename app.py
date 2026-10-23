"""
Smart Campus Resource Booking System
Programming 512 project starter implementation.
Uses Python standard-library Tkinter and SQLite.
"""

import sqlite3
import hashlib
import os
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date, timedelta

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "smart_campus.db")

CAMPUSES = {
    "Johannesburg": {
        "max_hours": 4, "start_hour": 8, "end_hour": 17,
        "policy": "Maximum 4 hours; bookings allowed 08:00–17:00"
    },
    "Pretoria": {
        "max_hours": 3, "start_hour": 9, "end_hour": 16,
        "policy": "Maximum 3 hours; bookings allowed 09:00–16:00"
    },
    "Durban": {
        "max_hours": 2, "start_hour": 8, "end_hour": 15,
        "policy": "Maximum 2 hours; bookings allowed 08:00–15:00"
    },
}

DEFAULT_RESOURCES = [
    ("JHB-LAB-01", "Computer Laboratory 1", "Johannesburg", 40),
    ("JHB-PROJ-01", "Multimedia Projector", "Johannesburg", 1),
    ("PTA-ROOM-01", "Seminar Room 1", "Pretoria", 25),
    ("PTA-PROJ-01", "Presentation Projector", "Pretoria", 1),
    ("DBN-LAB-01", "Computer Laboratory 1", "Durban", 30),
    ("DBN-ROOM-01", "Seminar Room 1", "Durban", 20),
]


def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


class Database:
    def __init__(self, path=DB_PATH):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.create_tables()
        self.seed_data()

    def create_tables(self):
        self.conn.executescript("""
        PRAGMA foreign_keys = ON;
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('Lecturer','Campus Administrator','System Operator')),
            campus TEXT
        );
        CREATE TABLE IF NOT EXISTS campuses (
            name TEXT PRIMARY KEY,
            max_hours INTEGER NOT NULL,
            start_hour INTEGER NOT NULL,
            end_hour INTEGER NOT NULL,
            policy TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resource_code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            campus TEXT NOT NULL REFERENCES campuses(name),
            capacity INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            resource_id INTEGER NOT NULL REFERENCES resources(id),
            campus TEXT NOT NULL REFERENCES campuses(name),
            booking_date TEXT NOT NULL,
            start_time TEXT NOT NULL,
            duration_hours REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'Active',
            created_at TEXT NOT NULL
        );
        """)
        self.conn.commit()

    def seed_data(self):
        for name, policy in CAMPUSES.items():
            self.conn.execute(
                """INSERT OR IGNORE INTO campuses
                (name,max_hours,start_hour,end_hour,policy) VALUES (?,?,?,?,?)""",
                (name, policy["max_hours"], policy["start_hour"], policy["end_hour"], policy["policy"])
            )
        # Demo accounts: change these passwords before real use.
        demos = [
            ("lecturer", "Learn123!", "Lecturer", "Johannesburg"),
            ("admin_jhb", "Admin123!", "Campus Administrator", "Johannesburg"),
            ("operator", "Operator123!", "System Operator", None),
        ]
        for username, password, role, campus in demos:
            self.conn.execute(
                "INSERT OR IGNORE INTO users(username,password_hash,role,campus) VALUES (?,?,?,?)",
                (username, hash_password(password), role, campus)
            )
        for code, name, campus, capacity in DEFAULT_RESOURCES:
            self.conn.execute(
                "INSERT OR IGNORE INTO resources(resource_code,name,campus,capacity) VALUES (?,?,?,?)",
                (code, name, campus, capacity)
            )
        self.conn.commit()

    def authenticate(self, username, password):
        return self.conn.execute(
            "SELECT * FROM users WHERE username=? AND password_hash=?",
            (username.strip(), hash_password(password))
        ).fetchone()

    def register_lecturer(self, username, password, campus):
        self.conn.execute(
            "INSERT INTO users(username,password_hash,role,campus) VALUES (?,?,?,?)",
            (username.strip(), hash_password(password), "Lecturer", campus)
        )
        self.conn.commit()

    def campuses(self):
        return self.conn.execute("SELECT * FROM campuses ORDER BY name").fetchall()

    def resources(self, campus=None):
        if campus:
            return self.conn.execute(
                "SELECT * FROM resources WHERE campus=? ORDER BY name", (campus,)
            ).fetchall()
        return self.conn.execute("SELECT * FROM resources ORDER BY campus,name").fetchall()

    def add_resource(self, code, name, campus, capacity):
        self.conn.execute(
            "INSERT INTO resources(resource_code,name,campus,capacity) VALUES (?,?,?,?)",
            (code.strip().upper(), name.strip(), campus, capacity)
        )
        self.conn.commit()

    def update_resource(self, resource_id, code, name, campus, capacity):
        self.conn.execute(
            "UPDATE resources SET resource_code=?,name=?,campus=?,capacity=? WHERE id=?",
            (code.strip().upper(), name.strip(), campus, capacity, resource_id)
        )
        self.conn.commit()

    def delete_resource(self, resource_id):
        linked = self.conn.execute(
            "SELECT COUNT(*) FROM bookings WHERE resource_id=?", (resource_id,)
        ).fetchone()[0]
        if linked:
            raise ValueError("This resource has booking records and cannot be deleted.")
        self.conn.execute("DELETE FROM resources WHERE id=?", (resource_id,))
        self.conn.commit()

    def bookings(self, campus=None, user_id=None, status=None):
        sql = """SELECT b.*, u.username, r.resource_code, r.name AS resource_name
                 FROM bookings b JOIN users u ON u.id=b.user_id
                 JOIN resources r ON r.id=b.resource_id WHERE 1=1"""
        args = []
        if campus:
            sql += " AND b.campus=?"; args.append(campus)
        if user_id is not None:
            sql += " AND b.user_id=?"; args.append(user_id)
        if status:
            sql += " AND b.status=?"; args.append(status)
        sql += " ORDER BY b.booking_date,b.start_time"
        return self.conn.execute(sql, args).fetchall()

    def is_available(self, resource_id, booking_date, start_time, duration):
        start = datetime.strptime(start_time, "%H:%M")
        end = start + timedelta(hours=duration)
        rows = self.conn.execute(
            """SELECT start_time,duration_hours FROM bookings
               WHERE resource_id=? AND booking_date=? AND status='Active'""",
            (resource_id, booking_date)
        ).fetchall()
        for row in rows:
            old_start = datetime.strptime(row["start_time"], "%H:%M")
            old_end = old_start + timedelta(hours=row["duration_hours"])
            if start < old_end and old_start < end:
                return False
        return True

    def create_booking(self, user_id, resource_id, campus, booking_date, start_time, duration):
        self.conn.execute(
            """INSERT INTO bookings
            (user_id,resource_id,campus,booking_date,start_time,duration_hours,status,created_at)
            VALUES (?,?,?,?,?,?,?,?)""",
            (user_id, resource_id, campus, booking_date, start_time, duration, "Active",
             datetime.now().isoformat(timespec="seconds"))
        )
        self.conn.commit()

    def cancel_booking(self, booking_id):
        self.conn.execute(
            "UPDATE bookings SET status='Cancelled' WHERE id=? AND status='Active'",
            (booking_id,)
        )
        self.conn.commit()

    def report_rows(self):
        return self.conn.execute("""
        SELECT c.name AS campus,
               COUNT(b.id) AS total_bookings,
               COALESCE(ROUND(AVG(CASE WHEN b.status='Active' THEN b.duration_hours END),2),0) AS avg_hours
        FROM campuses c
        LEFT JOIN bookings b ON b.campus=c.name
        GROUP BY c.name ORDER BY c.name
        """).fetchall()

    def popular_resources(self, campus=None):
        sql = """SELECT r.campus,r.resource_code,r.name,COUNT(b.id) AS uses
                 FROM resources r LEFT JOIN bookings b
                 ON b.resource_id=r.id AND b.status='Active'"""
        args = []
        if campus:
            sql += " WHERE r.campus=?"; args.append(campus)
        sql += " GROUP BY r.id ORDER BY uses DESC,r.name"
        return self.conn.execute(sql, args).fetchall()

    def close(self):
        self.conn.close()


class User:
    def __init__(self, row):
        self.id = row["id"]
        self.username = row["username"]
        self.role = row["role"]
        self.campus = row["campus"]


class Lecturer(User):
    pass


class CampusAdministrator(User):
    pass


class SystemOperator(User):
    pass


class SmartCampusApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Smart Campus Resource Booking System")
        self.root.geometry("1050x700")
        self.root.minsize(900, 600)
        self.db = Database()
        self.user = None
        self.active_campus = None
        self.main = ttk.Frame(root, padding=16)
        self.main.pack(fill="both", expand=True)
        self.show_login()
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def clear(self):
        for child in self.main.winfo_children():
            child.destroy()

    def heading(self, title, subtitle=None):
        ttk.Label(self.main, text=title, font=("Segoe UI", 20, "bold")).pack(anchor="w", pady=(0, 4))
        if subtitle:
            ttk.Label(self.main, text=subtitle, wraplength=950).pack(anchor="w", pady=(0, 12))

    def show_login(self):
        self.clear()
        self.heading("Smart Campus Resource Booking System", "Log in, or register a lecturer account.")
        panel = ttk.Frame(self.main, padding=20)
        panel.pack(anchor="nw")
        ttk.Label(panel, text="Username").grid(row=0, column=0, sticky="w", pady=6)
        username = ttk.Entry(panel, width=32)
        username.grid(row=0, column=1, pady=6, padx=8)
        ttk.Label(panel, text="Password").grid(row=1, column=0, sticky="w", pady=6)
        password = ttk.Entry(panel, width=32, show="*")
        password.grid(row=1, column=1, pady=6, padx=8)

        def login():
            row = self.db.authenticate(username.get(), password.get())
            if not row:
                messagebox.showerror("Login failed", "Incorrect username or password.")
                return
            if row["role"] == "Lecturer":
                self.user = Lecturer(row)
            elif row["role"] == "Campus Administrator":
                self.user = CampusAdministrator(row)
            else:
                self.user = SystemOperator(row)
            self.show_campus_selection()

        ttk.Button(panel, text="Log in", command=login).grid(row=2, column=1, sticky="ew", pady=8)
        ttk.Button(panel, text="Register as lecturer", command=self.show_register).grid(row=3, column=1, sticky="ew")
        ttk.Label(self.main, text=(
            "Demo accounts (change before real use):  lecturer / Learn123!    |    "
            "admin_jhb / Admin123!    |    operator / Operator123!"
        ), wraplength=950).pack(anchor="w", pady=18)

    def show_register(self):
        self.clear()
        self.heading("Lecturer Registration", "Create a new lecturer account.")
        form = ttk.Frame(self.main, padding=12)
        form.pack(anchor="nw")
        ttk.Label(form, text="Username").grid(row=0, column=0, sticky="w", pady=5)
        username = ttk.Entry(form, width=30); username.grid(row=0, column=1, padx=8, pady=5)
        ttk.Label(form, text="Password (minimum 6 characters)").grid(row=1, column=0, sticky="w", pady=5)
        password = ttk.Entry(form, width=30, show="*"); password.grid(row=1, column=1, padx=8, pady=5)
        ttk.Label(form, text="Home campus").grid(row=2, column=0, sticky="w", pady=5)
        campus = ttk.Combobox(form, values=list(CAMPUSES), state="readonly", width=27)
        campus.grid(row=2, column=1, padx=8, pady=5); campus.current(0)

        def register():
            if not username.get().strip() or len(password.get()) < 6:
                messagebox.showerror("Invalid input", "Enter a username and a password of at least 6 characters.")
                return
            try:
                self.db.register_lecturer(username.get(), password.get(), campus.get())
                messagebox.showinfo("Registered", "Account created. You can now log in.")
                self.show_login()
            except sqlite3.IntegrityError:
                messagebox.showerror("Registration failed", "That username already exists.")

        ttk.Button(form, text="Create account", command=register).grid(row=3, column=1, sticky="ew", pady=10)
        ttk.Button(form, text="Back to login", command=self.show_login).grid(row=4, column=1, sticky="ew")

    def show_campus_selection(self):
        self.clear()
        self.heading("Select Active Campus", f"Signed in as {self.user.username} ({self.user.role}).")
        rows = self.db.campuses()
        options = [r["name"] for r in rows]
        if self.user.role == "Campus Administrator":
            options = [self.user.campus] if self.user.campus else options
        if self.user.role == "Lecturer" and self.user.campus in options:
            default = options.index(self.user.campus)
        else:
            default = 0
        ttk.Label(self.main, text="Campus").pack(anchor="w")
        campus = ttk.Combobox(self.main, values=options, state="readonly", width=35)
        campus.pack(anchor="w", pady=6)
        if options: campus.current(default)

        policy_label = ttk.Label(self.main, text="", wraplength=900)
        policy_label.pack(anchor="w", pady=8)

        def update_policy(_=None):
            if campus.get():
                policy = next(r["policy"] for r in rows if r["name"] == campus.get())
                policy_label.config(text=f"Policy in effect for {campus.get()}: {policy}")
        campus.bind("<<ComboboxSelected>>", update_policy)
        update_policy()

        def enter():
            if not campus.get():
                messagebox.showerror("Choose campus", "Please select a campus.")
                return
            self.active_campus = campus.get()
            self.show_dashboard()

        ttk.Button(self.main, text="Continue", command=enter).pack(anchor="w", pady=8)
        ttk.Button(self.main, text="Log out", command=self.show_login).pack(anchor="w")

    def show_dashboard(self):
        self.clear()
        self.heading("Campus Dashboard", f"User: {self.user.username} | Role: {self.user.role} | Active campus: {self.active_campus}")
        policy = next(r["policy"] for r in self.db.campuses() if r["name"] == self.active_campus)
        ttk.Label(self.main, text=f"Current booking policy: {policy}", wraplength=950).pack(anchor="w", pady=(0, 12))

        bar = ttk.Frame(self.main); bar.pack(fill="x", anchor="w", pady=(0, 12))
        ttk.Button(bar, text="View Resources", command=self.show_resources).pack(side="left", padx=(0, 6))
        ttk.Button(bar, text="Book Resource", command=self.show_booking_form).pack(side="left", padx=6)
        ttk.Button(bar, text="My Bookings", command=self.show_my_bookings).pack(side="left", padx=6)
        if self.user.role in ("Campus Administrator", "System Operator"):
            ttk.Button(bar, text="Manage Resources", command=self.show_manage_resources).pack(side="left", padx=6)
            ttk.Button(bar, text="Campus Bookings", command=self.show_all_bookings).pack(side="left", padx=6)
            ttk.Button(bar, text="Reports", command=self.show_reports).pack(side="left", padx=6)
        if self.user.role == "System Operator":
            ttk.Button(bar, text="All-Campus View", command=self.show_all_campus_data).pack(side="left", padx=6)
        ttk.Button(bar, text="Change Campus", command=self.show_campus_selection).pack(side="right")
        ttk.Button(bar, text="Log out", command=self.show_login).pack(side="right", padx=6)

        self.content = ttk.Frame(self.main)
        self.content.pack(fill="both", expand=True)
        self.show_resources()

    def make_tree(self, parent, columns, headings, height=14):
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True, pady=8)
        tree = ttk.Treeview(frame, columns=columns, show="headings", height=height)
        for col, title in zip(columns, headings):
            tree.heading(col, text=title)
            tree.column(col, width=130, anchor="w")
        ybar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=ybar.set)
        tree.pack(side="left", fill="both", expand=True)
        ybar.pack(side="right", fill="y")
        return tree

    def clear_content(self):
        for child in self.content.winfo_children():
            child.destroy()

    def show_resources(self):
        self.clear_content()
        ttk.Label(self.content, text=f"Resources at {self.active_campus}", font=("Segoe UI", 13, "bold")).pack(anchor="w")
        tree = self.make_tree(self.content, ("id","code","name","campus","capacity"), ("ID","Code","Resource","Campus","Capacity"))
        for r in self.db.resources(self.active_campus):
            tree.insert("", "end", values=(r["id"],r["resource_code"],r["name"],r["campus"],r["capacity"]))

    def show_booking_form(self):
        self.clear_content()
        self.show_resources()
        # Place booking form below the resource list.
        form = ttk.LabelFrame(self.content, text="Create a booking", padding=10)
        form.pack(fill="x", pady=8)
        resources = self.db.resources(self.active_campus)
        if not resources:
            ttk.Label(form, text="No resources are registered at this campus.").pack(anchor="w")
            return
        ttk.Label(form, text="Resource").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        resource_map = {f'{r["resource_code"]} - {r["name"]}': r for r in resources}
        resource = ttk.Combobox(form, values=list(resource_map), state="readonly", width=32)
        resource.grid(row=0, column=1, padx=4, pady=4); resource.current(0)
        ttk.Label(form, text="Date (YYYY-MM-DD)").grid(row=0, column=2, sticky="w", padx=4, pady=4)
        date_entry = ttk.Entry(form, width=14); date_entry.grid(row=0, column=3, padx=4, pady=4)
        date_entry.insert(0, date.today().isoformat())
        ttk.Label(form, text="Start time (HH:MM)").grid(row=1, column=0, sticky="w", padx=4, pady=4)
        time_entry = ttk.Entry(form, width=14); time_entry.grid(row=1, column=1, padx=4, pady=4); time_entry.insert(0, "10:00")
        ttk.Label(form, text="Duration in hours").grid(row=1, column=2, sticky="w", padx=4, pady=4)
        duration_entry = ttk.Entry(form, width=14); duration_entry.grid(row=1, column=3, padx=4, pady=4); duration_entry.insert(0, "1")

        def book():
            try:
                if self.user.role != "Lecturer":
                    messagebox.showerror("Not allowed", "Only lecturers can create bookings.")
                    return
                chosen = resource_map.get(resource.get())
                if not chosen: raise ValueError("Select a resource.")
                booking_date = date_entry.get().strip()
                parsed_date = datetime.strptime(booking_date, "%Y-%m-%d").date()
                if parsed_date < date.today(): raise ValueError("Booking date cannot be in the past.")
                start = datetime.strptime(time_entry.get().strip(), "%H:%M")
                duration = float(duration_entry.get())
                policy = next(r for r in self.db.campuses() if r["name"] == self.active_campus)
                if duration <= 0 or duration > policy["max_hours"]:
                    raise ValueError(f"Duration must be greater than 0 and no more than {policy['max_hours']} hours.")
                end = start + timedelta(hours=duration)
                if start.hour < policy["start_hour"] or end.hour + (1 if end.minute else 0) > policy["end_hour"] or (end.hour == policy["end_hour"] and end.minute > 0):
                    raise ValueError(f"Booking must fit within {policy['start_hour']:02d}:00–{policy['end_hour']:02d}:00.")
                if not self.db.is_available(chosen["id"], booking_date, time_entry.get().strip(), duration):
                    raise ValueError("That resource already has an overlapping active booking.")
                self.db.create_booking(self.user.id, chosen["id"], self.active_campus, booking_date, time_entry.get().strip(), duration)
                messagebox.showinfo("Booking created", "Your booking has been saved.")
                self.show_my_bookings()
            except ValueError as exc:
                messagebox.showerror("Cannot create booking", str(exc))
            except Exception as exc:
                messagebox.showerror("Error", f"Please check your entries. Details: {exc}")

        ttk.Button(form, text="Confirm Booking", command=book).grid(row=2, column=3, sticky="e", padx=4, pady=8)

    def show_my_bookings(self):
        self.clear_content()
        ttk.Label(self.content, text="My booking history", font=("Segoe UI", 13, "bold")).pack(anchor="w")
        tree = self.make_tree(self.content, ("id","date","start","duration","resource","campus","status"),
                              ("Booking ID","Date","Start","Hours","Resource","Campus","Status"))
        for b in self.db.bookings(user_id=self.user.id):
            tree.insert("", "end", values=(b["id"],b["booking_date"],b["start_time"],b["duration_hours"],b["resource_name"],b["campus"],b["status"]))
        def cancel():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("Select booking", "Select a booking first."); return
            values = tree.item(selected[0], "values")
            booking = next((b for b in self.db.bookings(user_id=self.user.id) if b["id"] == int(values[0])), None)
            if not booking or booking["status"] != "Active":
                messagebox.showerror("Cannot cancel", "Only active bookings can be cancelled."); return
            start_dt = datetime.strptime(booking["booking_date"] + " " + booking["start_time"], "%Y-%m-%d %H:%M")
            if start_dt <= datetime.now():
                messagebox.showerror("Cannot cancel", "Only future bookings can be cancelled."); return
            if messagebox.askyesno("Confirm cancellation", "Cancel the selected booking?"):
                self.db.cancel_booking(booking["id"]); self.show_my_bookings()
        ttk.Button(self.content, text="Cancel selected future booking", command=cancel).pack(anchor="w", pady=5)

    def show_manage_resources(self):
        if self.user.role not in ("Campus Administrator", "System Operator"):
            messagebox.showerror("Access denied", "You do not have permission to manage resources."); return
        self.clear_content()
        ttk.Label(self.content, text="Manage resources", font=("Segoe UI", 13, "bold")).pack(anchor="w")
        tree = self.make_tree(self.content, ("id","code","name","campus","capacity"), ("ID","Code","Resource","Campus","Capacity"))
        resources = self.db.resources(self.active_campus if self.user.role == "Campus Administrator" else None)
        for r in resources:
            tree.insert("", "end", values=(r["id"],r["resource_code"],r["name"],r["campus"],r["capacity"]))
        form = ttk.LabelFrame(self.content, text="Add or update selected resource", padding=8)
        form.pack(fill="x", pady=6)
        entries = {}
        labels = ["Resource code","Resource name","Capacity"]
        for i, label in enumerate(labels):
            ttk.Label(form, text=label).grid(row=0, column=i, sticky="w", padx=4)
            ent = ttk.Entry(form, width=22); ent.grid(row=1, column=i, padx=4, pady=4); entries[label] = ent
        ttk.Label(form, text="Campus").grid(row=0, column=3, sticky="w", padx=4)
        campus = ttk.Combobox(form, values=[self.user.campus] if self.user.role == "Campus Administrator" else list(CAMPUSES), state="readonly", width=18)
        campus.grid(row=1, column=3, padx=4, pady=4)
        campus.set(self.active_campus if self.active_campus in (list(CAMPUSES) if self.user.role == "System Operator" else [self.user.campus]) else (self.user.campus or self.active_campus))
        selected_id = {"value": None}
        def select_row(_=None):
            chosen = tree.selection()
            if not chosen: return
            vals = tree.item(chosen[0], "values")
            selected_id["value"] = int(vals[0])
            entries["Resource code"].delete(0,"end"); entries["Resource code"].insert(0,vals[1])
            entries["Resource name"].delete(0,"end"); entries["Resource name"].insert(0,vals[2])
            campus.set(vals[3])
            entries["Capacity"].delete(0,"end"); entries["Capacity"].insert(0,vals[4])
        tree.bind("<<TreeviewSelect>>", select_row)
        def save():
            try:
                code, name = entries["Resource code"].get().strip(), entries["Resource name"].get().strip()
                capacity = int(entries["Capacity"].get())
                if not code or not name or capacity < 1: raise ValueError("Enter code, name, and capacity of at least 1.")
                if self.user.role == "Campus Administrator" and campus.get() != self.user.campus:
                    raise ValueError("Campus administrators may only manage their own campus.")
                if selected_id["value"]:
                    self.db.update_resource(selected_id["value"],code,name,campus.get(),capacity)
                else:
                    self.db.add_resource(code,name,campus.get(),capacity)
                self.show_manage_resources()
            except sqlite3.IntegrityError:
                messagebox.showerror("Duplicate code", "Resource codes must be unique.")
            except (ValueError, TypeError) as exc:
                messagebox.showerror("Invalid resource", str(exc))
        def delete():
            if not selected_id["value"]:
                messagebox.showwarning("Select resource","Select a resource first."); return
            try:
                self.db.delete_resource(selected_id["value"]); self.show_manage_resources()
            except ValueError as exc:
                messagebox.showerror("Cannot remove", str(exc))
        buttons = ttk.Frame(form); buttons.grid(row=2,column=0,columnspan=4,sticky="w",pady=5)
        ttk.Button(buttons,text="Add / Save changes",command=save).pack(side="left",padx=4)
        ttk.Button(buttons,text="Remove selected",command=delete).pack(side="left",padx=4)
        ttk.Button(buttons,text="Clear form",command=lambda: (selected_id.update(value=None), [e.delete(0,"end") for e in entries.values()])).pack(side="left",padx=4)

    def show_all_bookings(self):
        self.clear_content()
        campus_filter = self.active_campus if self.user.role == "Campus Administrator" else None
        ttk.Label(self.content, text="Bookings" + (f" — {campus_filter}" if campus_filter else " — all campuses"),
                  font=("Segoe UI", 13, "bold")).pack(anchor="w")
        tree = self.make_tree(self.content, ("id","user","campus","resource","date","start","hours","status"),
                              ("ID","Lecturer","Campus","Resource","Date","Start","Hours","Status"))
        for b in self.db.bookings(campus=campus_filter):
            tree.insert("", "end", values=(b["id"],b["username"],b["campus"],b["resource_name"],b["booking_date"],b["start_time"],b["duration_hours"],b["status"]))

    def show_reports(self):
        self.clear_content()
        ttk.Label(self.content, text="Campus usage reports", font=("Segoe UI", 13, "bold")).pack(anchor="w")
        tree = self.make_tree(self.content, ("campus","total","average"), ("Campus","Total bookings","Average active duration (hours)"))
        rows = self.db.report_rows()
        if self.user.role == "Campus Administrator":
            rows = [r for r in rows if r["campus"] == self.user.campus]
        for r in rows:
            tree.insert("", "end", values=(r["campus"],r["total_bookings"],r["avg_hours"]))
        ttk.Label(self.content, text="Resource usage (active bookings):", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(8,0))
        popular = self.make_tree(self.content, ("campus","code","name","uses"), ("Campus","Code","Resource","Bookings"), height=6)
        for r in self.db.popular_resources(self.user.campus if self.user.role == "Campus Administrator" else None):
            popular.insert("", "end", values=(r["campus"],r["resource_code"],r["name"],r["uses"]))

    def show_all_campus_data(self):
        if self.user.role != "System Operator":
            messagebox.showerror("Access denied", "Only system operators can view all-campus data."); return
        self.clear_content()
        ttk.Label(self.content, text="Institution-wide resources and bookings", font=("Segoe UI", 13, "bold")).pack(anchor="w")
        tree = self.make_tree(self.content, ("campus","code","resource","capacity"), ("Campus","Code","Resource","Capacity"))
        for r in self.db.resources():
            tree.insert("", "end", values=(r["campus"],r["resource_code"],r["name"],r["capacity"]))
        ttk.Label(self.content, text="Cross-campus booking totals:", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        totals = self.make_tree(self.content, ("campus","total","average"), ("Campus","Bookings","Average hours"), height=5)
        for r in self.db.report_rows():
            totals.insert("", "end", values=(r["campus"],r["total_bookings"],r["avg_hours"]))

    def close(self):
        self.db.close()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    try:
        app = SmartCampusApp(root)
        root.mainloop()
    except Exception as error:
        messagebox.showerror("Application error", str(error))
        raise
