"""
Placeholder/sanity tests for the mock data layer. Add real module tests
alongside your models as each module's logic is built.
"""

import os
import sqlite3

MOCK_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "app", "mock_data")


def test_cms_mock_db_has_core_tables():
    db_path = os.path.join(MOCK_DATA_DIR, "twin_mock.db")
    assert os.path.exists(db_path), "twin_mock.db not found — did seed.py run?"

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cur.fetchall()}
    conn.close()

    expected = {"students", "faculty", "courses", "departments", "theses"}
    assert expected.issubset(tables)


def test_unitime_mock_db_has_core_tables():
    db_path = os.path.join(MOCK_DATA_DIR, "unitime_mock.db")
    assert os.path.exists(db_path), "unitime_mock.db not found — did unitime_seed.py run?"

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cur.fetchall()}
    conn.close()

    expected = {"classes", "assignments", "rooms", "student_class_enrollments"}
    assert expected.issubset(tables)
