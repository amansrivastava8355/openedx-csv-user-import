"""Unit tests for CSV parsing helpers (no Open edX runtime required)."""

import io

from openedx_csv_user_import.services import (
    aggregate_student_records,
    is_valid_email,
    iter_emails_from_csv,
    iter_student_records_from_csv,
    normalize_email,
    parse_course_ids,
    username_from_email,
    CsvStudentRecord,
)


def test_normalize_email():
    assert normalize_email("  Alice@Uni.EDU ") == "alice@uni.edu"


def test_is_valid_email():
    assert is_valid_email("a@b.co")
    assert not is_valid_email("not-an-email")
    assert not is_valid_email("")


def test_username_from_email():
    assert username_from_email("alice.student@university.edu") == "alice.student"
    assert username_from_email("weird!!!name@x.com") == "weirdname"
    long_local = "a" * 50 + "@x.com"
    assert len(username_from_email(long_local)) == 30


def test_parse_course_ids():
    assert parse_course_ids("") == []
    assert parse_course_ids("course-v1:Org+C1+Run") == ["course-v1:Org+C1+Run"]
    assert parse_course_ids("course-v1:A+B+C;course-v1:D+E+F") == [
        "course-v1:A+B+C",
        "course-v1:D+E+F",
    ]
    assert parse_course_ids("course-v1:A+B+C|course-v1:D+E+F") == [
        "course-v1:A+B+C",
        "course-v1:D+E+F",
    ]


def test_iter_emails_header():
    data = "email\none@test.com\ntwo@test.com\n"
    assert list(iter_emails_from_csv(io.StringIO(data))) == [
        "one@test.com",
        "two@test.com",
    ]


def test_iter_emails_no_header():
    data = "one@test.com\ntwo@test.com\n"
    assert list(iter_emails_from_csv(io.StringIO(data))) == [
        "one@test.com",
        "two@test.com",
    ]


def test_iter_emails_alias_column():
    data = "full_name,e-mail\nAda,ada@lovelace.org\n"
    assert list(iter_emails_from_csv(io.StringIO(data))) == ["ada@lovelace.org"]


def test_iter_emails_semicolon_delimited():
    data = "email;role\na@b.com;student\n"
    assert list(iter_emails_from_csv(io.StringIO(data))) == ["a@b.com"]


def test_iter_student_records_with_course():
    data = (
        "email,course_id\n"
        "a@test.com,course-v1:OpenedX+DemoX+DemoCourse\n"
        "b@test.com,course-v1:Org+C1+2024;course-v1:Org+C2+2024\n"
    )
    records = list(iter_student_records_from_csv(io.StringIO(data)))
    assert records[0].email == "a@test.com"
    assert records[0].course_ids == ["course-v1:OpenedX+DemoX+DemoCourse"]
    assert records[1].email == "b@test.com"
    assert records[1].course_ids == ["course-v1:Org+C1+2024", "course-v1:Org+C2+2024"]


def test_iter_student_records_default_course():
    data = "email\na@test.com\n"
    records = list(
        iter_student_records_from_csv(
            io.StringIO(data),
            default_course_id="course-v1:OpenedX+DemoX+DemoCourse",
        )
    )
    assert records[0].course_ids == ["course-v1:OpenedX+DemoX+DemoCourse"]


def test_aggregate_student_records_merges_courses():
    records = [
        CsvStudentRecord("a@test.com", ["course-v1:A+B+C"]),
        CsvStudentRecord("a@test.com", ["course-v1:D+E+F"]),
        CsvStudentRecord("b@test.com", ["course-v1:A+B+C"]),
    ]
    merged = aggregate_student_records(records)
    assert len(merged) == 2
    assert merged[0].email == "a@test.com"
    assert merged[0].course_ids == ["course-v1:A+B+C", "course-v1:D+E+F"]
    assert merged[1].course_ids == ["course-v1:A+B+C"]
