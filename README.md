# Customer Management System (C++)

A console-based Customer Management System written in modern C++, built as a
learning project to practice OOP fundamentals, file handling, and clean
project structure. It's being developed in stages, with each stage adding a
working, compilable piece of the system rather than one large dump of code.

This README reflects the current stage of development and will be updated
as new features are added.

## Current Status: Stage 1 — Data Model

Right now the project implements the core data model and proves it works.
The menu-driven interface, file storage, and CRUD operations described in
the project plan are not built yet — see [Future Improvements](#future-improvements)
for what's coming next.

## Features (implemented so far)

- `Date` struct representing a calendar date (day, month, year)
- Automatic capture of the current system date via `Date::today()`
- `Customer` class storing ID, name, phone, email, address, and registration date
- Two ways to build a customer: a parameterised constructor, or the default
  constructor followed by setters
- Encapsulated fields — all data members are private, accessed only through
  getters and setters
- No `setId()` by design — a customer's ID is fixed at creation and cannot
  be changed afterwards
- `toDisplayString()` — formats a customer's details as readable text
- A `main.cpp` driver that creates sample customers, prints them, and shows
  a setter updating a field

## Technologies Used

- **Language:** C++ (C++17)
- **Compiler:** g++
- **Build tool:** GNU Make
- **Standard library only** — no external/third-party libraries

## C++ Concepts Demonstrated

- Classes vs. structs, and choosing deliberately between them (`Customer`
  needs encapsulation and validation later; `Date` is plain data with
  nothing to protect)
- Encapsulation — private data members with public getters/setters
- Constructors — both default and parameterised, plus constructor
  initializer lists
- `const` member functions to guarantee getters can't modify state
- `std::string` handling
- String formatting with `<sstream>` and `<iomanip>`
- Working with system time via `<ctime>`
- Passing objects by `const reference` to avoid unnecessary copying

## Project Structure

```
customer-management-system/
├── include/
│   └── Customer.h        # Date struct + Customer class declarations
├── src/
│   ├── Customer.cpp      # Date + Customer implementation
│   └── main.cpp          # Stage 1 driver / demonstration
├── data/                 # Reserved for customer data file (not used yet)
├── Makefile
├── .gitignore
└── README.md
```

## How to Compile and Run

This project uses a Makefile, so building it is a single command.

```bash
# Build the project
make

# Run it
./cms

# Or build and run in one step
make run

# Remove build artifacts
make clean
```

If `make` isn't available on your system, you can compile directly:

```bash
g++ -std=c++17 -Iinclude src/*.cpp -o cms
./cms
```

## Example Output

The current `main.cpp` is a demonstration, not an interactive menu. Running
it produces output like this:

```
=== Customer Management System - Stage 1 ===

Customer ID   : 1001
Name          : Ishan Kanchan
Phone         : 9876543210
Email         : ishan@example.com
Address       : Alandi, Pune
Registered On : 15-09-2026

Customer ID   : 0
Name          : Rahul Deshmukh
Phone         : 9123456780
Email         : rahul@example.com
Address       : Kothrud, Pune
Registered On : 01-01-2000

After updating the address of customer 1001:
Chakan, Pune
```

The second customer shows placeholder values (`ID 0`, `01-01-2000`) because
it's built with the default constructor with no ID assigned yet. Automatic,
non-repeating ID generation is handled by the manager class in a later stage.

## Data Storage

Not implemented yet. The plan is a plain text file (`data/customers.txt`)
with one pipe-delimited (`|`) record per line, read and written through a
dedicated `FileHandler` class using `ifstream`/`ofstream`. The `data/`
folder already exists in the repo in preparation for this.

## Future Improvements

Planned for upcoming stages, in rough order:

- `CustomerManager` class to hold customers in a `std::vector` and generate
  unique, non-reused customer IDs
- Menu-driven console interface (`ConsoleUI`)
- File persistence, so records survive after the program closes
- Search by ID, name, and phone
- Update and delete operations, with confirmation before deleting
- Input validation (`Validator` class) with meaningful error messages
- Sorting customers by ID, name, or registration date
- Basic exception handling for invalid input and corrupt data files
- A simple record-count / summary view

## Author

**Ishan Sandeep Kanchan**
S.Y. B.Tech. Software Engineering, MIT Academy of Engineering, Alandi, Pune
