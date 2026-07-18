# Pick-to-Light Warehouse Locator

Pick-to-Light is a warehouse part-number location system. A user searches for a part number and receives its physical location: rack, column, level, position, and location ID.

The current project is the backend foundation. The final production frontend will be developed separately and connect to the API described in [API_CONTRACT.md](API_CONTRACT.md).

## Current Features

- FastAPI backend for exact part-number lookup.
- SQLite inventory database.
- Excel `.xlsx` layout import that replaces current inventory.
- Temporary local webpage for testing the backend on a phone or laptop.
- Temporary shared-admin protection for Excel inventory uploads.
- Automated tests that do not modify real inventory data.

## Project Files

| File or folder | Purpose |
| --- | --- |
| `main.py` | FastAPI application startup and route registration |
| `database.py` | SQLite connection and inventory search functions |
| `routers/` | FastAPI route modules for inventory search and Excel import |
| `setup_db.py` | Creates empty SQLite tables when a database is missing |
| `almacen_ptl.db` | Local inventory database; ignored by Git |
| `PartNumbers Layout.xlsx` | Local inventory source layout; ignored by Git |
| `static/` | Temporary test webpage; not the final frontend |
| `tests/` | Automated backend tests |
| `API_CONTRACT.md` | Backend/frontend agreement and AI handoff document |
| `requirements.txt` | Required Python packages and known-working versions |

## Requirements

- Python 3.11 or newer is recommended.
- Git is recommended for collaboration.

## First-Time Setup

Run these commands from the `Pick-to-light` project folder.

### 1. Create and activate a virtual environment

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, run this once in that terminal and then activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### 2. Install the project packages

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 3. Create the empty local database if needed

```powershell
python setup_db.py
```

Only run this when `almacen_ptl.db` does not exist or when you intentionally want a new empty database. It does not import Excel inventory data.

### 4. Load inventory data

Start the application:

```powershell
python main.py
```

Open `http://127.0.0.1:8000` if the browser does not open automatically. Use the **Update layout** section to upload the approved `.xlsx` file.

Important: uploading a layout replaces all previous inventory records.

## Daily Development

Activate the virtual environment, then start the backend:

```powershell
.\venv\Scripts\Activate.ps1
python main.py
```

Useful local URLs:

| URL | Use |
| --- | --- |
| `http://127.0.0.1:8000/` | Temporary local test webpage |
| `http://127.0.0.1:8000/docs` | FastAPI interactive API documentation |
| `http://127.0.0.1:8000/inventario/DZ133127` | Example direct inventory API request |

## Run Automated Tests

```powershell
python -m unittest discover -s tests -v
```

The tests create a temporary database. They do not modify `almacen_ptl.db` or `PartNumbers Layout.xlsx`.

## Configure Temporary Upload Access

The Excel upload route replaces all inventory, so it requires a shared temporary admin username and password. Choose a private username and password with your teammate. Do not add them to Python files, Git, `README.md`, or `API_CONTRACT.md`.

Before starting the backend, set both values in the same PowerShell terminal:

```powershell
$env:PICK_TO_LIGHT_ADMIN_USERNAME = "choose-a-private-username"
$env:PICK_TO_LIGHT_ADMIN_PASSWORD = "choose-a-private-password"
python main.py
```

The values last only for the current terminal window. The temporary local webpage asks for them only when uploading an Excel layout.

For public deployment, use HTTPS. HTTP Basic credentials must never be sent over an unencrypted public connection.

## Frontend Integration

The frontend should use the API contract in [API_CONTRACT.md](API_CONTRACT.md). The two current backend endpoints are:

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/inventario/{part_number}` | Look up one part number and its location |
| `POST` | `/importar-layout` | Replace inventory using an uploaded Excel file |

Do not change endpoint names, request field names, or response field names without updating `API_CONTRACT.md` and coordinating with both backend and frontend owners.

## Important Data and Security Notes

- The database and Excel layout are intentionally ignored by Git. Each collaborator needs an approved copy locally.
- The Excel upload endpoint uses one shared temporary admin account for the current two-person team.
- The final version needs individual warehouse-supervisor accounts and a proper authorization design.
- The final frontend host and backend host have not been selected. CORS configuration should be added only after those URLs are known.
- SQLite is suitable for local development and mostly fixed inventory. A production deployment needs persistent storage for the database file or a future cloud database decision.

## Instructions for AI Coding Assistants

1. Read `API_CONTRACT.md` before modifying the backend or building the final frontend.
2. Inspect existing code before changing it.
3. Do not invent requirements for hardware, authentication, deployment, database migration, or frontend technology.
4. Preserve API behavior unless a project owner explicitly requests a contract change.
5. Add concise comments to new non-obvious code.
6. Run focused tests after backend changes.
7. Do not commit, deploy, or overwrite real inventory data without explicit approval.
