# Pick-to-Light: Backend Contract and Frontend Handoff

## Purpose of This Document

This is the source of truth for the current backend/frontend connection. It is written so a developer or AI coding assistant can understand the project without first reading every Python file.

When implementing frontend work, treat the sections marked **Current fact** as fixed. Do not invent features, rename API fields, or change backend routes unless the project owners explicitly agree.

## Project Goal

Pick-to-Light is a warehouse location system.

1. A warehouse user enters a part number in a website on a phone or laptop.
2. The website asks the backend for the location of that part.
3. The backend returns rack, column, level, position, and location ID.
4. The website displays that location clearly.
5. In a later phase, hardware will illuminate lights at the matching physical location.

## Current Scope

### Current fact

- The backend is Python + FastAPI.
- The local database is SQLite: `almacen_ptl.db`.
- Inventory source data is an Excel `.xlsx` layout file.
- The backend supports exact part-number lookup.
- The backend supports replacing all inventory from an Excel upload.
- A temporary local test website exists in `static/`.
- The final frontend will be developed separately and may replace the temporary website.

### Explicit non-goals for the current phase

- No WhatsApp integration.
- No user login or role management yet.
- No real Pick-to-Light hardware control yet.
- No cloud deployment host selected yet.
- No decision has been made to move from SQLite to PostgreSQL or another database.

## Repository Map

| Path | Purpose | Ownership / Notes |
| --- | --- | --- |
| `main.py` | FastAPI application startup, static files, and route registration | Backend |
| `database.py` | SQLite connection and inventory search functions | Backend |
| `routers/inventory.py` | Part-number search endpoint | Backend |
| `routers/layout.py` | Excel-import endpoint | Backend |
| `almacen_ptl.db` | Local SQLite inventory database | Backend data; currently ignored by Git |
| `PartNumbers Layout.xlsx` | Local Excel layout used for inventory data | Source data; currently ignored by Git |
| `setup_db.py` | Creates the initial SQLite tables | Backend utility |
| `static/` | Temporary local test website | Can be replaced by final frontend |
| `API_CONTRACT.md` | This integration contract | Keep updated when API changes |

## Running the Backend Locally

From the project folder:

```powershell
python main.py
```

The backend starts at:

```text
http://127.0.0.1:8000
```

The current temporary test webpage opens at the root URL:

```text
http://127.0.0.1:8000/
```

FastAPI's interactive development documentation is available at:

```text
http://127.0.0.1:8000/docs
```

## API Contract

### Endpoint: Search for a part number

**Current fact:** This endpoint searches using an exact part-number match after removing leading and trailing spaces.

```http
GET /inventario/{part_number}
```

Example request:

```text
GET http://127.0.0.1:8000/inventario/DZ133127
```

Successful response: `200 OK`

```json
{
  "part_number": "DZ133127",
  "rack": 106,
  "columna": 1,
  "nivel": "A",
  "posicion": "L",
  "id_ubicacion": "106-01-A-L"
}
```

Part number not found: `404 Not Found`

```json
{
  "detail": "El SKU UNKNOWN-PART no se encuentra en el almacen o la base de datos esta vacia"
}
```

Frontend implementation requirements:

- URL-encode the part number.
- On `200`, display `part_number`, `rack`, `columna`, `nivel`, and `posicion`.
- On `404`, display the backend's `detail` message as a user-facing not-found state.
- Do not assume partial matching, suggestions, or case-insensitive search exists. They have not been implemented.

JavaScript example:

```js
async function searchPartNumber(partNumber) {
  const response = await fetch(
    `/inventario/${encodeURIComponent(partNumber.trim())}`
  );
  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail);
  }

  return data;
}
```

### Endpoint: Replace inventory from an Excel layout

**Current fact:** Uploading a valid file deletes existing inventory and location records, then imports the new layout. It is a full replacement, not an incremental update.

```http
POST /importar-layout
Content-Type: multipart/form-data
```

Required multipart field:

```text
archivo: <Excel .xlsx file>
```

Expected first worksheet layout:

| Excel column | Zero-based index | Required meaning |
| --- | --- | --- |
| A | 0 | Part number |
| B | 1 | Rack |
| C | 2 | Column |
| D | 3 | Level |
| E | 4 | Position |
| F | 5 | Location ID |

Rules:

- The first row is treated as headers and is ignored.
- Rows missing a Location ID are ignored.
- The file extension must be `.xlsx`.
- Excel upload requires HTTP Basic authentication with the temporary shared admin account.

Successful response: `200 OK`

```json
{
  "status": "success",
  "mensaje": "Carga completa. Se crearon 10 ubicaciones y se asignaron 10 SKUs."
}
```

Invalid file extension: `400 Bad Request`

```json
{
  "detail": "El archivo debe ser formato .xlsx"
}
```

Unreadable Excel or failed import: `500 Internal Server Error`

```json
{
  "detail": "Error al leer el Excel: ..."
}
```

or:

```json
{
  "detail": "Error al importar el Excel: ..."
}
```

JavaScript example:

```js
async function uploadLayout(file) {
  const formData = new FormData();
  formData.append("archivo", file);

const response = await fetch("/importar-layout", {
  method: "POST",
  headers: {
    Authorization: `Basic ${btoa(`${username}:${password}`)}`
  },
  body: formData
});
  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail);
  }

  return data;
}
```

Do not set the `Content-Type` header manually when using `FormData`; the browser sets the required multipart boundary. The temporary local page asks for the admin username and password before making this request.

## Integration Constraints

### Frontend/backend hosting

The final frontend host is not chosen. The frontend can call the backend directly when both are on the same origin. If they are deployed on different domains, the backend must be updated with CORS settings for the final frontend domain.

Do not add broad CORS settings now. The correct allowed domain depends on the future deployment decision.

### Database and deployment

SQLite is correct for current local development and mostly fixed inventory. A deployed application needs persistent storage for `almacen_ptl.db`; serverless hosting may remove local file changes between requests. Do not choose the production database or deployment design without a project-owner decision.

### Upload safety

Because the upload endpoint replaces all inventory, it uses one temporary shared admin account for the current two-person team. The final public system needs individual warehouse-supervisor accounts and a proper authorization design before public deployment.

## Frontend Handoff Checklist

Before claiming frontend/backend integration is complete, verify all of the following:

- Search an existing part number, for example `DZ133127`.
- Display the returned rack, column, level, and position.
- Search a non-existing part number and show the `404` message.
- Select a non-`.xlsx` file and show the upload error.
- Upload an approved `.xlsx` layout and show the success message.
- Search a part from the newly uploaded layout.
- Confirm the frontend calls the intended backend URL in the selected deployment environment.

## Backend Test Commands

Run the automated backend tests from the project folder:

```powershell
python -m unittest discover -s tests -v
```

The tests create their own temporary database. They do not modify `almacen_ptl.db` or the Excel layout file.

## Rules for Future Changes

1. Update this document whenever a route, request field, response field, or import rule changes.
2. Keep field names stable unless both backend and frontend owners agree to a change.
3. Add automated tests before changing existing search or import behavior.
4. Keep temporary frontend work independent from backend business logic.
5. Do not add hardware, authentication, cloud database, or deployment assumptions without an explicit decision.

## Instructions for an AI Coding Assistant

When asked to work on this project:

1. Read this file first.
2. Inspect the current code before proposing or making edits.
3. Preserve the API contract unless the user explicitly asks to change it.
4. State assumptions before implementing a change that affects deployment, access control, database design, hardware, or frontend architecture.
5. Add concise comments beside new non-obvious code.
6. Verify changed behavior with focused tests.
7. Do not commit, deploy, delete inventory, or overwrite the database unless explicitly requested.
