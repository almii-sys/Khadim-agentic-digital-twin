"""
schedule_tool.py — example of an agent "tool" the LLM calls when a student
asks something like "when and where is my DBMS class?"

This is the piece that sits between your LLM agent's function-calling and
the DataGateway. In a real agent framework you'd register `answer_schedule_query`
as a callable tool with a JSON schema description; this file shows the plain
Python logic underneath that tool call.
"""

from app.services.data_gateway import get_gateway


def answer_schedule_query(sap_id: str, course_name: str) -> str:
    """
    sap_id: the logged-in student's SAP ID (from their session/login)
    course_name: extracted by the LLM from the student's message,
                 e.g. student said "DBMS" or "database" or "CS-702"
    """
    gateway = get_gateway()  # <- the ONLY place this file touches the data layer

    schedule = gateway.get_class_schedule(sap_id, course_name_contains=course_name)

    if not schedule:
        return (
            f"I couldn't find a class matching '{course_name}' in your current "
            f"enrollments. Want me to check your full schedule instead?"
        )

    lines = []
    for cls in schedule:
        lines.append(
            f"{cls.course_title} ({cls.course_code}) — {cls.section_type}: "
            f"{cls.days}, {cls.start_time}–{cls.end_time}, "
            f"{cls.building} Room {cls.room_number}"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    # Quick manual test: pull a real SAP ID out of the mock DB and try it
    import sqlite3
    import os

    db_path = os.path.join(os.path.dirname(__file__), "..", "mock_data", "twin_mock.db")
    conn = sqlite3.connect(db_path)
    sap_id = conn.execute("SELECT sap_id FROM students LIMIT 1").fetchone()[0]
    conn.close()

    print(f"Testing with student SAP ID: {sap_id}")
    print(answer_schedule_query(sap_id, "Database"))
