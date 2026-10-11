#!/usr/bin/env python3
"""Small, dependency-free HTTP API and web server for the customer dashboard."""

from __future__ import annotations

import csv
import io
import json
import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import date
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Iterator
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
WEB_ROOT = ROOT / "web"
DATA_ROOT = ROOT / "data"
DEFAULT_DATABASE = DATA_ROOT / "customers.db"
MAX_REQUEST_BYTES = 1_100_000
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_PATTERN = re.compile(r"^[+()\d][+()\d .-]{5,24}$")
SORT_COLUMNS = {
    "id": "id",
    "name": "name COLLATE NOCASE",
    "email": "email COLLATE NOCASE",
    "city": "city COLLATE NOCASE",
    "status": "status",
    "registrationDate": "registration_date",
}


@contextmanager
def connect(database_path: Path) -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(database_path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database(database_path: Path) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    with connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT NOT NULL,
                city TEXT NOT NULL,
                address TEXT NOT NULL DEFAULT '',
                registration_date TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('active', 'inactive'))
            )
            """
        )
        connection.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS customers_email_unique "
            "ON customers(email COLLATE NOCASE)"
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER,
                customer_name TEXT NOT NULL,
                action TEXT NOT NULL,
                occurred_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS activity_occurred_at ON activity(occurred_at DESC)"
        )


def customer_dict(row: sqlite3.Row) -> dict[str, object]:
    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "phone": row["phone"],
        "city": row["city"],
        "address": row["address"],
        "registrationDate": row["registration_date"],
        "status": row["status"],
    }


class ValidationError(ValueError):
    def __init__(self, fields: dict[str, str]):
        self.fields = fields
        super().__init__("Please correct the highlighted customer details.")


def normalize_customer(payload: object) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise ValueError("Provide customer details as a JSON object.")

    fields = {
        "name": ("Full name", 120),
        "email": ("Email address", 254),
        "phone": ("Phone number", 30),
        "city": ("City", 100),
        "address": ("Address", 300),
    }
    result: dict[str, object] = {}
    errors: dict[str, str] = {}
    for key, (label, max_length) in fields.items():
        value = payload.get(key, "")
        if not isinstance(value, str):
            errors[key] = f"{label} must be text."
            continue
        value = value.strip()
        if key != "address" and not value:
            errors[key] = f"{label} is required."
        elif len(value) > max_length:
            errors[key] = f"{label} must be {max_length} characters or fewer."
        result[key] = value

    email = result.get("email")
    if isinstance(email, str) and email and not EMAIL_PATTERN.fullmatch(email):
        errors["email"] = "Enter a valid email address."

    phone = result.get("phone")
    if isinstance(phone, str) and phone and (
        not PHONE_PATTERN.fullmatch(phone) or sum(character.isdigit() for character in phone) < 7
    ):
        errors["phone"] = "Enter a valid phone number with at least 7 digits."

    status = payload.get("status", "active")
    if status not in ("active", "inactive"):
        errors["status"] = "Status must be active or inactive."
    result["status"] = status

    registration_date = payload.get("registrationDate") or date.today().isoformat()
    if not isinstance(registration_date, str):
        errors["registrationDate"] = "Registration date must be a valid YYYY-MM-DD date."
    else:
        try:
            parsed_date = date.fromisoformat(registration_date)
            if parsed_date.isoformat() != registration_date:
                raise ValueError
            result["registrationDate"] = registration_date
        except ValueError:
            errors["registrationDate"] = "Registration date must be a valid YYYY-MM-DD date."

    if errors:
        raise ValidationError(errors)
    return result


def customer_filters(query: dict[str, list[str]]) -> tuple[str, list[str]]:
    clauses: list[str] = []
    values: list[str] = []
    search = query.get("search", [""])[0].strip()
    if search:
        escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        clauses.append(
            "(CAST(id AS TEXT) LIKE ? ESCAPE '\\' COLLATE NOCASE "
            "OR name LIKE ? ESCAPE '\\' COLLATE NOCASE "
            "OR email LIKE ? ESCAPE '\\' COLLATE NOCASE "
            "OR phone LIKE ? ESCAPE '\\' COLLATE NOCASE "
            "OR city LIKE ? ESCAPE '\\' COLLATE NOCASE)"
        )
        values.extend([pattern] * 5)
    city = query.get("city", [""])[0].strip()
    if city:
        clauses.append("city = ? COLLATE NOCASE")
        values.append(city)
    status = query.get("status", [""])[0].strip().lower()
    if status:
        if status not in ("active", "inactive"):
            raise ValidationError({"status": "Status must be active or inactive."})
        clauses.append("status = ?")
        values.append(status)
    return (" WHERE " + " AND ".join(clauses) if clauses else ""), values


class CustomerRequestHandler(BaseHTTPRequestHandler):
    database_path = DEFAULT_DATABASE
    server_version = "CustomerManagement/1.0"

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.address_string()} - {format % args}")

    def _security_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'; "
            "img-src 'self' data:; base-uri 'none'; frame-ancestors 'none'",
        )

    def _send_json(self, status: HTTPStatus, value: object) -> None:
        body = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self._security_headers()
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, status: HTTPStatus, message: str, **details: object) -> None:
        self._send_json(status, {"error": message, **details})

    def _read_body(self) -> bytes:
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError as error:
            raise ValueError("Content-Length must be a whole number.") from error
        if content_length <= 0:
            raise ValueError("A request body is required.")
        if content_length > MAX_REQUEST_BYTES:
            raise OverflowError("Request body exceeds the 1 MB limit.")
        return self.rfile.read(content_length)

    def _read_json(self) -> object:
        try:
            return json.loads(self._read_body())
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise ValueError("Request body must contain valid JSON.") from error

    @staticmethod
    def _record_activity(
        connection: sqlite3.Connection, customer_id: int | None, name: str, action: str
    ) -> None:
        connection.execute(
            "INSERT INTO activity (customer_id, customer_name, action) VALUES (?, ?, ?)",
            (customer_id, name, action),
        )

    def _respond_database_error(self, error: sqlite3.IntegrityError) -> None:
        message = str(error)
        if "customers.email" in message:
            self._send_error(
                HTTPStatus.CONFLICT,
                "A customer with this email address already exists.",
                fields={"email": "This email address is already in use."},
            )
        elif "customers.id" in message:
            self._send_error(HTTPStatus.CONFLICT, "This customer ID already exists.")
        else:
            self._send_error(HTTPStatus.CONFLICT, "The record conflicts with existing customer data.")

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        if parsed.path == "/api/customers":
            self._list_customers(query)
        elif parsed.path == "/api/cities":
            self._get_cities()
        elif parsed.path == "/api/stats":
            self._get_stats()
        elif parsed.path == "/api/activity":
            self._get_activity(query)
        elif parsed.path == "/api/export.csv":
            self._export_customers(query)
        elif parsed.path.startswith("/api/customers/"):
            self._get_customer(parsed.path.removeprefix("/api/customers/"))
        elif parsed.path.startswith("/api/"):
            self._send_error(HTTPStatus.NOT_FOUND, "API endpoint not found.")
        else:
            self._serve_static(parsed.path)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/customers":
            self._create_customer()
        elif parsed.path == "/api/import":
            self._import_customers()
        else:
            self._send_error(HTTPStatus.NOT_FOUND, "API endpoint not found.")

    def do_PUT(self) -> None:
        path = urlparse(self.path).path
        if path.startswith("/api/customers/"):
            self._update_customer(path.removeprefix("/api/customers/"))
        else:
            self._send_error(HTTPStatus.NOT_FOUND, "API endpoint not found.")

    def do_DELETE(self) -> None:
        path = urlparse(self.path).path
        if path.startswith("/api/customers/"):
            self._delete_customer(path.removeprefix("/api/customers/"))
        else:
            self._send_error(HTTPStatus.NOT_FOUND, "API endpoint not found.")

    def _serve_static(self, path: str) -> None:
        if path not in ("/", "/index.html", "/styles.css", "/app.js"):
            self._send_error(HTTPStatus.NOT_FOUND, "Page not found.")
            return
        file_path = WEB_ROOT / ("index.html" if path == "/" else path.lstrip("/"))
        if not file_path.is_file():
            self._send_error(HTTPStatus.INTERNAL_SERVER_ERROR, "Web application files are missing.")
            return
        content_type = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "text/javascript; charset=utf-8",
        }[file_path.suffix]
        body = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self._security_headers()
        self.end_headers()
        self.wfile.write(body)

    def _list_customers(self, query: dict[str, list[str]]) -> None:
        try:
            where, values = customer_filters(query)
            page = max(1, int(query.get("page", ["1"])[0]))
            page_size = min(100, max(1, int(query.get("pageSize", ["10"])[0])))
            sort = query.get("sort", ["id"])[0]
            order = query.get("order", ["desc"])[0].lower()
            if sort not in SORT_COLUMNS or order not in ("asc", "desc"):
                raise ValidationError({"sort": "Choose a supported sort column and direction."})
        except (ValueError, ValidationError) as error:
            self._send_error(HTTPStatus.BAD_REQUEST, str(error), fields=getattr(error, "fields", None))
            return
        with connect(self.database_path) as connection:
            total = connection.execute(f"SELECT COUNT(*) FROM customers{where}", values).fetchone()[0]
            rows = connection.execute(
                f"SELECT * FROM customers{where} ORDER BY {SORT_COLUMNS[sort]} {order}, id DESC "
                "LIMIT ? OFFSET ?",
                [*values, page_size, (page - 1) * page_size],
            ).fetchall()
        self._send_json(
            HTTPStatus.OK,
            {
                "customers": [customer_dict(row) for row in rows],
                "total": total,
                "page": page,
                "pageSize": page_size,
                "totalPages": max(1, (total + page_size - 1) // page_size),
            },
        )

    def _get_customer(self, raw_id: str) -> None:
        try:
            customer_id = int(raw_id)
            if customer_id < 1:
                raise ValueError
        except ValueError:
            self._send_error(HTTPStatus.BAD_REQUEST, "Customer ID must be a positive integer.")
            return
        with connect(self.database_path) as connection:
            row = connection.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()
        if row is None:
            self._send_error(HTTPStatus.NOT_FOUND, "Customer not found.")
            return
        self._send_json(HTTPStatus.OK, {"customer": customer_dict(row)})

    def _get_stats(self) -> None:
        with connect(self.database_path) as connection:
            total, active, inactive = connection.execute(
                """
                SELECT COUNT(*),
                       COALESCE(SUM(status = 'active'), 0),
                       COALESCE(SUM(status = 'inactive'), 0)
                FROM customers
                """
            ).fetchone()
            counts = {
                row["month"]: row["count"]
                for row in connection.execute(
                    """
                    SELECT substr(registration_date, 1, 7) AS month, COUNT(*) AS count
                    FROM customers
                    WHERE registration_date >= date('now', 'start of month', '-5 months')
                    GROUP BY month
                    ORDER BY month
                    """
                ).fetchall()
            }
            activities = connection.execute(
                "SELECT * FROM activity ORDER BY id DESC LIMIT 5"
            ).fetchall()
        from datetime import datetime

        today = date.today().replace(day=1)
        months: list[dict[str, object]] = []
        for offset in range(5, -1, -1):
            month_number = today.month - 1 - offset
            year = today.year + month_number // 12
            month = month_number % 12 + 1
            key = f"{year:04d}-{month:02d}"
            months.append(
                {
                    "month": key,
                    "label": datetime(year, month, 1).strftime("%b"),
                    "count": counts.get(key, 0),
                }
            )
        self._send_json(
            HTTPStatus.OK,
            {
                "total": total,
                "active": active,
                "inactive": inactive,
                "growth": months,
                "recentActivity": [dict(row) for row in activities],
            },
        )

    def _get_cities(self) -> None:
        with connect(self.database_path) as connection:
            rows = connection.execute(
                "SELECT DISTINCT city FROM customers ORDER BY city COLLATE NOCASE"
            ).fetchall()
        self._send_json(HTTPStatus.OK, {"cities": [row["city"] for row in rows]})

    def _get_activity(self, query: dict[str, list[str]]) -> None:
        try:
            page = max(1, int(query.get("page", ["1"])[0]))
            page_size = min(50, max(1, int(query.get("pageSize", ["15"])[0])))
        except ValueError:
            self._send_error(HTTPStatus.BAD_REQUEST, "Page and page size must be whole numbers.")
            return
        with connect(self.database_path) as connection:
            total = connection.execute("SELECT COUNT(*) FROM activity").fetchone()[0]
            rows = connection.execute(
                "SELECT * FROM activity ORDER BY id DESC LIMIT ? OFFSET ?",
                (page_size, (page - 1) * page_size),
            ).fetchall()
        self._send_json(
            HTTPStatus.OK,
            {
                "activities": [dict(row) for row in rows],
                "total": total,
                "page": page,
                "pageSize": page_size,
                "totalPages": max(1, (total + page_size - 1) // page_size),
            },
        )

    def _export_customers(self, query: dict[str, list[str]]) -> None:
        try:
            where, values = customer_filters(query)
        except ValidationError as error:
            self._send_error(HTTPStatus.BAD_REQUEST, str(error), fields=error.fields)
            return
        with connect(self.database_path) as connection:
            rows = connection.execute(
                f"SELECT * FROM customers{where} ORDER BY id ASC", values
            ).fetchall()
        output = io.StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow(
            [
                "Customer ID",
                "Full Name",
                "Email",
                "Phone Number",
                "City",
                "Address",
                "Registration Date",
                "Status",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    row["id"],
                    row["name"],
                    row["email"],
                    row["phone"],
                    row["city"],
                    row["address"],
                    row["registration_date"],
                    row["status"],
                ]
            )
        body = ("\ufeff" + output.getvalue()).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Content-Disposition", 'attachment; filename="customers.csv"')
        self.send_header("Content-Length", str(len(body)))
        self._security_headers()
        self.end_headers()
        self.wfile.write(body)

    def _create_customer(self) -> None:
        try:
            customer = normalize_customer(self._read_json())
        except OverflowError as error:
            self._send_error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, str(error))
            return
        except ValueError as error:
            self._send_error(
                HTTPStatus.BAD_REQUEST, str(error), fields=getattr(error, "fields", None)
            )
            return
        with connect(self.database_path) as connection:
            try:
                cursor = connection.execute(
                    """
                    INSERT INTO customers
                        (name, email, phone, city, address, registration_date, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        customer["name"],
                        customer["email"],
                        customer["phone"],
                        customer["city"],
                        customer["address"],
                        customer["registrationDate"],
                        customer["status"],
                    ),
                )
                customer_id = cursor.lastrowid
                self._record_activity(connection, customer_id, str(customer["name"]), "created")
                row = connection.execute(
                    "SELECT * FROM customers WHERE id = ?", (customer_id,)
                ).fetchone()
            except sqlite3.IntegrityError as error:
                self._respond_database_error(error)
                return
        self._send_json(HTTPStatus.CREATED, {"customer": customer_dict(row)})

    def _update_customer(self, raw_id: str) -> None:
        try:
            customer_id = int(raw_id)
            if customer_id < 1:
                raise ValueError
            customer = normalize_customer(self._read_json())
        except OverflowError as error:
            self._send_error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, str(error))
            return
        except ValueError as error:
            message = (
                "Customer ID must be a positive integer."
                if not isinstance(error, ValidationError)
                else str(error)
            )
            self._send_error(HTTPStatus.BAD_REQUEST, message, fields=getattr(error, "fields", None))
            return
        with connect(self.database_path) as connection:
            existing = connection.execute(
                "SELECT id FROM customers WHERE id = ?", (customer_id,)
            ).fetchone()
            if existing is None:
                self._send_error(HTTPStatus.NOT_FOUND, "Customer not found.")
                return
            try:
                connection.execute(
                    """
                    UPDATE customers
                    SET name = ?, email = ?, phone = ?, city = ?, address = ?,
                        registration_date = ?, status = ?
                    WHERE id = ?
                    """,
                    (
                        customer["name"],
                        customer["email"],
                        customer["phone"],
                        customer["city"],
                        customer["address"],
                        customer["registrationDate"],
                        customer["status"],
                        customer_id,
                    ),
                )
                self._record_activity(connection, customer_id, str(customer["name"]), "updated")
                row = connection.execute(
                    "SELECT * FROM customers WHERE id = ?", (customer_id,)
                ).fetchone()
            except sqlite3.IntegrityError as error:
                self._respond_database_error(error)
                return
        self._send_json(HTTPStatus.OK, {"customer": customer_dict(row)})

    def _delete_customer(self, raw_id: str) -> None:
        try:
            customer_id = int(raw_id)
            if customer_id < 1:
                raise ValueError
        except ValueError:
            self._send_error(HTTPStatus.BAD_REQUEST, "Customer ID must be a positive integer.")
            return
        with connect(self.database_path) as connection:
            row = connection.execute(
                "SELECT name FROM customers WHERE id = ?", (customer_id,)
            ).fetchone()
            if row is None:
                self._send_error(HTTPStatus.NOT_FOUND, "Customer not found.")
                return
            connection.execute("DELETE FROM customers WHERE id = ?", (customer_id,))
            self._record_activity(connection, customer_id, row["name"], "deleted")
        self._send_json(HTTPStatus.OK, {"message": "Customer deleted successfully."})

    def _import_customers(self) -> None:
        try:
            content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
            if content_type == "text/csv":
                csv_text = self._read_body().decode("utf-8-sig")
            else:
                payload = self._read_json()
                if not isinstance(payload, dict) or not isinstance(payload.get("csv"), str):
                    raise ValueError("Provide CSV text in the 'csv' field.")
                csv_text = payload["csv"].lstrip("\ufeff")
            reader = csv.DictReader(io.StringIO(csv_text))
            if not reader.fieldnames:
                raise ValueError("The CSV file must include a header row.")
            aliases = {
                "customer id": "id",
                "id": "id",
                "full name": "name",
                "name": "name",
                "email address": "email",
                "email": "email",
                "phone number": "phone",
                "phone": "phone",
                "city": "city",
                "address": "address",
                "registration date": "registrationDate",
                "registrationdate": "registrationDate",
                "status": "status",
            }
            normalized_headers = {
                header.strip().lower(): aliases.get(header.strip().lower())
                for header in reader.fieldnames
                if header
            }
            required_headers = {"name", "email", "phone", "city"}
            available = {header for header in normalized_headers.values() if header}
            if not required_headers.issubset(available):
                raise ValueError("CSV needs Full Name, Email, Phone Number, and City columns.")
            entries: list[tuple[dict[str, object], int | None]] = []
            row_errors: list[str] = []
            ids: set[int] = set()
            emails: set[str] = set()
            for line_number, raw_row in enumerate(reader, start=2):
                if not any(
                    isinstance(value, str) and value.strip()
                    for value in raw_row.values()
                ):
                    continue
                if raw_row.get(None):
                    row_errors.append(f"Row {line_number}: The row has more columns than the header.")
                    continue
                mapped = {
                    normalized_headers[header.strip().lower()]: value
                    for header, value in raw_row.items()
                    if header and normalized_headers.get(header.strip().lower())
                }
                try:
                    customer = normalize_customer(mapped)
                    raw_id = mapped.get("id", "")
                    customer_id: int | None = None
                    if raw_id:
                        customer_id = int(str(raw_id).strip())
                        if customer_id < 1 or customer_id in ids:
                            raise ValueError("Customer ID is invalid or duplicated in this file.")
                        ids.add(customer_id)
                    email = str(customer["email"]).casefold()
                    if email in emails:
                        raise ValueError("Email address is duplicated in this file.")
                    emails.add(email)
                    entries.append((customer, customer_id))
                except (ValueError, TypeError) as error:
                    detail = str(error)
                    if isinstance(error, ValidationError):
                        detail = "; ".join(error.fields.values())
                    row_errors.append(f"Row {line_number}: {detail}")
            if row_errors:
                self._send_error(
                    HTTPStatus.BAD_REQUEST,
                    "CSV validation failed. No customers were imported.",
                    details=row_errors[:20],
                    totalErrors=len(row_errors),
                )
                return
            if not entries:
                self._send_error(HTTPStatus.BAD_REQUEST, "The CSV file contains no customer rows.")
                return
        except OverflowError as error:
            self._send_error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, str(error))
            return
        except ValueError as error:
            self._send_error(HTTPStatus.BAD_REQUEST, str(error))
            return

        with connect(self.database_path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                for customer, customer_id in entries:
                    if customer_id is not None and connection.execute(
                        "SELECT 1 FROM customers WHERE id = ?", (customer_id,)
                    ).fetchone():
                        self._send_error(HTTPStatus.CONFLICT, f"Customer ID {customer_id} already exists.")
                        return
                    if connection.execute(
                        "SELECT 1 FROM customers WHERE email = ? COLLATE NOCASE",
                        (customer["email"],),
                    ).fetchone():
                        self._send_error(
                            HTTPStatus.CONFLICT,
                            f"Email address {customer['email']} already exists.",
                            fields={"email": "This email address is already in use."},
                        )
                        return
                for customer, customer_id in entries:
                    values = (
                        customer["name"],
                        customer["email"],
                        customer["phone"],
                        customer["city"],
                        customer["address"],
                        customer["registrationDate"],
                        customer["status"],
                    )
                    if customer_id is None:
                        connection.execute(
                            "INSERT INTO customers "
                            "(name, email, phone, city, address, registration_date, status) "
                            "VALUES (?, ?, ?, ?, ?, ?, ?)",
                            values,
                        )
                    else:
                        connection.execute(
                            "INSERT INTO customers "
                            "(id, name, email, phone, city, address, registration_date, status) "
                            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                            (customer_id, *values),
                        )
                self._record_activity(connection, None, f"{len(entries)} customers", "imported")
            except sqlite3.IntegrityError as error:
                connection.rollback()
                self._respond_database_error(error)
                return
        self._send_json(
            HTTPStatus.CREATED,
            {"imported": len(entries), "message": f"Imported {len(entries)} customers."},
        )


def create_server(
    host: str = "127.0.0.1", port: int = 8000, database_path: Path = DEFAULT_DATABASE
) -> ThreadingHTTPServer:
    initialize_database(database_path)
    handler = type(
        "ConfiguredCustomerRequestHandler",
        (CustomerRequestHandler,),
        {"database_path": database_path},
    )
    return ThreadingHTTPServer((host, port), handler)


def main() -> None:
    host = os.environ.get("CMS_HOST", "127.0.0.1")
    port = int(os.environ.get("CMS_PORT", "8000"))
    database_path = Path(os.environ.get("CMS_DATABASE_PATH", str(DEFAULT_DATABASE))).expanduser()
    server = create_server(host, port, database_path)
    print(f"Customer Management System running at http://{host}:{server.server_port}")
    print(f"SQLite database: {database_path.resolve()}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
