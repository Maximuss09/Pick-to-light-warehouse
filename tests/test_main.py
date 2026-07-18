"""NEW: automated backend tests that use a temporary SQLite database."""

import asyncio
import io
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import openpyxl
from fastapi import HTTPException, UploadFile
from fastapi.security import HTTPBasicCredentials
from fastapi.testclient import TestClient

import database
import main
import security
from routers import inventory, layout


class PickToLightBackendTests(unittest.TestCase):
    """NEW: verify inventory lookup and Excel replacement without touching real inventory."""

    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.environment_patch = patch.dict(
            "os.environ",
            {
                "PICK_TO_LIGHT_ADMIN_USERNAME": "test-admin",
                "PICK_TO_LIGHT_ADMIN_PASSWORD": "test-password",
            },
            clear=False,
        )
        self.environment_patch.start()
        self.original_database_path = database.DATABASE_PATH
        database.DATABASE_PATH = Path(self.temporary_directory.name) / "test_almacen_ptl.db"

        conn = sqlite3.connect(database.DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE ubicaciones (
                id_ubicacion TEXT PRIMARY KEY,
                rack INTEGER,
                columna INTEGER,
                nivel TEXT,
                posicion TEXT
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE inventario (
                part_number TEXT,
                id_ubicacion TEXT,
                FOREIGN KEY(id_ubicacion) REFERENCES ubicaciones(id_ubicacion)
            )
            """
        )
        cursor.execute(
            "INSERT INTO ubicaciones VALUES (?, ?, ?, ?, ?)",
            ("106-01-A-L", 106, 1, "A", "L"),
        )
        cursor.execute(
            "INSERT INTO inventario VALUES (?, ?)",
            ("DZ133127", "106-01-A-L"),
        )
        conn.commit()
        conn.close()

    def tearDown(self):
        database.DATABASE_PATH = self.original_database_path
        self.environment_patch.stop()
        self.temporary_directory.cleanup()

    def create_excel_upload(self, filename="layout.xlsx"):
        """NEW: create a valid in-memory workbook matching the documented import format."""
        workbook = openpyxl.Workbook()
        # NEW: worksheets always returns a normal Worksheet, which supports append().
        sheet = workbook.worksheets[0]
        sheet.append(["Part Number", "Rack", "Column", "Level", "Position", "Location ID"])
        sheet.append(["NEW-100", 200, 2, "B", "R", "200-02-B-R"])
        content = io.BytesIO()
        workbook.save(content)
        content.seek(0)
        return UploadFile(file=content, filename=filename)

    def test_search_returns_location_for_existing_part_number(self):
        result = inventory.buscar_ubicacion(" DZ133127 ")

        self.assertEqual(result["part_number"], "DZ133127")
        self.assertEqual(result["rack"], 106)
        self.assertEqual(result["columna"], 1)
        self.assertEqual(result["nivel"], "A")
        self.assertEqual(result["posicion"], "L")

    def test_search_returns_404_for_missing_part_number(self):
        with self.assertRaises(HTTPException) as raised_error:
            inventory.buscar_ubicacion("MISSING-PART")

        self.assertEqual(raised_error.exception.status_code, 404)
        self.assertIn("MISSING-PART", raised_error.exception.detail)

    def test_import_rejects_non_excel_file(self):
        upload = self.create_excel_upload(filename="layout.csv")

        with self.assertRaises(HTTPException) as raised_error:
            asyncio.run(layout.importar_layout(upload, authenticated_user="test-admin"))

        self.assertEqual(raised_error.exception.status_code, 400)

    def test_import_replaces_old_inventory_with_new_excel_data(self):
        response = asyncio.run(
            layout.importar_layout(self.create_excel_upload(), authenticated_user="test-admin")
        )

        self.assertEqual(response["status"], "success")
        self.assertIsNone(database.buscar_part_number_en_db("DZ133127"))
        imported_part = database.buscar_part_number_en_db("NEW-100")
        # NEW: make the expected successful import explicit before reading location fields.
        self.assertIsNotNone(imported_part)
        if imported_part is None:
            self.fail("The uploaded part number was not found after import.")
        self.assertEqual(imported_part["id_ubicacion"], "200-02-B-R")
        self.assertEqual(imported_part["rack"], 200)

    def test_upload_access_accepts_configured_admin_credentials(self):
        username = security.require_layout_upload_access(
            HTTPBasicCredentials(username="test-admin", password="test-password")
        )

        self.assertEqual(username, "test-admin")

    def test_upload_access_rejects_incorrect_credentials(self):
        with self.assertRaises(HTTPException) as raised_error:
            security.require_layout_upload_access(
                HTTPBasicCredentials(username="wrong", password="wrong")
            )

        self.assertEqual(raised_error.exception.status_code, 401)

    def test_upload_endpoint_requires_admin_credentials(self):
        client = TestClient(main.app)
        upload_file = {"archivo": ("layout.csv", b"not an Excel file", "text/csv")}

        missing_credentials = client.post("/importar-layout", files=upload_file)
        wrong_credentials = client.post(
            "/importar-layout",
            files=upload_file,
            auth=("wrong", "wrong"),
        )
        valid_credentials = client.post(
            "/importar-layout",
            files=upload_file,
            auth=("test-admin", "test-password"),
        )

        self.assertEqual(missing_credentials.status_code, 401)
        self.assertEqual(wrong_credentials.status_code, 401)
        self.assertEqual(valid_credentials.status_code, 400)


if __name__ == "__main__":
    unittest.main()
