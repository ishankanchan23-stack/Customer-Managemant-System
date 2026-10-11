# Customer Management System

A customer management dashboard backed by a persistent SQLite database, built
around the original C++17 customer model. The web application uses plain HTML,
CSS, and JavaScript, with a small Python standard-library server for its HTTP
API and database. No package installation, frontend framework, or external
database server is required.

## Project structure

```text
.
├── Customer.h              # Original C++ Date and Customer declarations
├── Customer.cpp            # Original C++ data model implementation
├── main.cpp                # Original C++ console demonstration
├── server.py               # HTTP server, customer API, SQLite storage
├── web/
│   ├── index.html          # Dashboard and accessible dialogs
│   ├── styles.css          # Responsive light/dark dashboard styles
│   └── app.js              # Dashboard, customer management, and API client
├── tests/
│   └── test_server.py      # HTTP API and persistence integration tests
├── data/                   # Created automatically; SQLite database lives here
├── Makefile                # C++ build plus optional web/test targets
└── .gitignore
```

The repository started as a Stage 1 C++17 data-model demonstration, not as an
existing web application. Its original customer model and console demonstration
are preserved. The Python server is the web application's backend: Python's
standard library provides HTTP and SQLite support without adding a framework,
database driver, or build step. The browser UI uses no third-party packages.

## Run the web application

Requirements: Python 3.10 or newer. On Windows, install Python with the Python
Launcher (`py`) available on your PATH.

From the project directory in PowerShell:

```powershell
py -3 server.py
```

Open **http://127.0.0.1:8000** in your browser. The page and API are served
together by the same process; there is no separate frontend build or server.
Press **Ctrl+C** in the terminal to stop the server.

The SQLite database is created automatically at `data/customers.db`. Customer
records and activity history remain there after the server is restarted. To
choose a different database path:

```powershell
$env:CMS_DATABASE_PATH = "C:\data\customers.db"
py -3 server.py
```

The server binds to `127.0.0.1` by default and is intended for a single-user,
local workspace. Authentication and role management are not implemented: do
not expose this development server to a network or the public internet. The
database itself stays on the server and is not served as a static file.

## Features

- Overview dashboard with total, active, inactive, and engagement statistics.
- Six-month customer registration chart and recent customer/activity summaries.
- Customer profiles with create, read, update, and confirmed delete operations.
- Case-insensitive search by customer ID, name, email, phone, or city.
- City and status filters, sortable columns, and server-side pagination.
- Customer CSV import with row validation and all-or-nothing database changes;
  CSV export respects the current search and filters.
- Activity history for customer creation, editing, removal, and CSV imports.
- Responsive layout, accessible dialogs and forms, toast messages, and saved
  light/dark theme preference.
- Backend validation, parameterized SQL queries, unique case-insensitive email
  addresses, request-size limits, and clear API error responses.
- Useful empty states; no placeholder customer records are inserted.

Required customer fields are full name, email, phone number, and city. Address
is optional. IDs are assigned by SQLite. Status is active or inactive, and
registration date defaults to the current date.

## Tests

Run the backend integration tests from the project directory:

```powershell
py -3 -m unittest discover -s tests -v
```

The tests cover customer CRUD, validation, duplicate emails, search and filters,
sorting and pagination, statistics, city lookup, CSV import/export, rollback of
invalid imports, HTTP routes, request limits, and persistence across a server
restart. All test data is written to temporary databases.

## Original C++ demonstration

The C++17 model and console sample remain available. With a compatible g++:

```powershell
g++ -std=c++17 -Wall -Wextra Customer.cpp main.cpp -o cms.exe
.\cms.exe
```

If GNU Make is installed, the Makefile also provides `make`, `make run`,
`make web`, and `make test` targets.
