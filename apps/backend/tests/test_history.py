from __future__ import annotations

import asyncio
import gzip
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select

from timetabler.api.app import create_app
from timetabler.config import Settings, repository_root
from timetabler.db.models import (
    HistoricalArchiveManifest,
    HistoricalCourseOffering,
    HistoricalCourseRelation,
    HistoricalCurriculumDepartment,
    HistoricalTermDataset,
)
from timetabler.db.session import Database
from timetabler.history.importer import import_dreams_archive


@dataclass(slots=True)
class FakeMailer:
    deliveries: list[tuple[str, str, str]] = field(default_factory=list)

    async def send_otp(self, recipient: str, code: str, *, challenge_id: str) -> None:
        self.deliveries.append((recipient, code, challenge_id))


def _gzip_json(value: dict[str, Any]) -> bytes:
    return gzip.compress(
        json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode(), mtime=0
    )


def _archive(tmp_path: Path) -> tuple[Path, dict[str, Any]]:
    root = tmp_path / "dreams"
    (root / "terms").mkdir(parents=True)
    (root / "curricula").mkdir()
    section = {
        "courseCode": "123456",
        "sectionCode": "01",
        "koreanName": "데이터와 사회",
        "englishName": "Data and Society",
        "professorName": "홍교수",
        "completionCategory": "교선",
        "credits": 3,
        "lectureHours": 3,
        "practiceHours": 0,
        "rawLectureTime": "월1,2,3",
        "rawLocation": "정보전산원 101",
        "targetGrade": "2",
        "listingStatus": "LISTED",
        "detailStatus": "AVAILABLE",
        "categoryContexts": [
            {
                "code": "B41002",
                "name": "교양선택",
                "areaCode": "B42001",
                "areaName": "제1영역:인간과소통",
            }
        ],
        "departmentContexts": [{"code": "CSE", "name": "컴퓨터공학전공"}],
        "syllabus": {
            "overview": "원본 개요",
            "weeklyPlans": [{"week": 1, "topic": "데이터"}],
            "futurePortalField": {"mustRemain": True},
        },
        "unknownSectionField": ["절대", "삭제하지 않음"],
    }
    term = {
        "schemaVersion": "1.0.0",
        "kind": "dreams-term-catalog",
        "academicYear": 2020,
        "termCode": "1",
        "termName": "1학기",
        "dataStatus": "FINAL",
        "collectedAt": "2026-07-14T00:00:00.000Z",
        "source": {"system": "DREAMS2", "futureRootField": "보존"},
        "collection": {"storedSections": 1},
        "sections": [section],
    }
    curriculum = {
        "schemaVersion": "1.0.0",
        "kind": "dreams-curriculum",
        "academicYear": 2020,
        "collectedAt": "2026-07-14T00:00:00.000Z",
        "source": {"system": "DREAMS2"},
        "departments": [
            {
                "collegeCode": "ENG",
                "collegeName": "공과대학",
                "departmentCode": "CSE",
                "departmentName": "컴퓨터공학전공",
                "courses": [
                    {
                        "grade": "2",
                        "recommendedTerm": "1",
                        "completionCategory": "전선",
                        "courseName": "데이터와 사회",
                        "credits": 3,
                        "lectureHours": 3,
                        "practiceHours": 0,
                        "lectureType": "이론",
                        "unknownCurriculumField": "보존",
                    }
                ],
            }
        ],
    }
    relations = {
        "schemaVersion": "1.0.0",
        "kind": "dreams-course-relations",
        "collectedAt": "2026-07-14T00:00:00.000Z",
        "source": {"system": "DREAMS2"},
        "replacementCourses": [
            {
                "designatedYear": "2020",
                "originalCourseName": "구데이터",
                "originalCategory": "전선",
                "originalCredits": 3,
                "originalDepartment": "컴퓨터공학전공",
                "replacementCourseName": "데이터와 사회",
                "replacementCategory": "전선",
                "replacementCredits": 3,
                "replacementDepartment": "컴퓨터공학전공",
                "note": None,
                "unknownRelationField": "보존",
            }
        ],
        "equivalentCourses": [],
    }
    raw_files = {
        "terms/2020-1.json.gz": _gzip_json(term),
        "curricula/curriculum-2020.json.gz": _gzip_json(curriculum),
        "relations.json.gz": _gzip_json(relations),
    }
    for relative_path, payload in raw_files.items():
        (root / relative_path).write_bytes(payload)
    datasets = [
        {
            "kind": "term",
            "path": "terms/2020-1.json.gz",
            "academicYear": 2020,
            "termCode": "1",
            "records": 1,
            "sha256": hashlib.sha256(raw_files["terms/2020-1.json.gz"]).hexdigest(),
        },
        {
            "kind": "curriculum",
            "path": "curricula/curriculum-2020.json.gz",
            "academicYear": 2020,
            "departments": 1,
            "records": 1,
            "sha256": hashlib.sha256(raw_files["curricula/curriculum-2020.json.gz"]).hexdigest(),
        },
        {
            "kind": "relations",
            "path": "relations.json.gz",
            "replacementRecords": 1,
            "equivalentRecords": 0,
            "records": 1,
            "sha256": hashlib.sha256(raw_files["relations.json.gz"]).hexdigest(),
        },
    ]
    manifest = {
        "schemaVersion": "1.0.0",
        "generatedAt": "2026-07-14T00:00:00.000Z",
        "source": {"system": "DREAMS2"},
        "requestedRange": {"years": [2020], "terms": ["1"]},
        "totals": {"datasets": 3, "termDatasets": 1, "sectionTermRecords": 1},
        "datasets": datasets,
        "unknownManifestField": {"mustRemain": True},
    }
    (root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    return root, section


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        environment="test",
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'history.db'}",
        data_root=repository_root() / "data",
        catalog_validate_checksums=True,
        auto_create_schema=True,
        cors_origins=["https://testserver"],
        auth_enabled=True,
        auth_hmac_secret="history-test-secret-that-is-more-than-32-bytes",
        auth_email_provider="disabled",
    )


def test_archive_import_is_lossless_and_idempotent(tmp_path: Path) -> None:
    archive_root, source_section = _archive(tmp_path)
    settings = _settings(tmp_path)

    async def prepare() -> tuple[str, bytes]:
        database = Database(settings.database_url)
        try:
            await database.create_schema()
            first = await import_dreams_archive(database, archive_root)
            second = await import_dreams_archive(database, archive_root)
            assert first.offerings_imported == 1
            assert first.curriculum_departments_imported == 1
            assert first.relations_imported == 1
            assert second.term_datasets_unchanged == 1
            assert second.curriculum_datasets_unchanged == 1
            assert second.relation_datasets_unchanged == 1
            async with database.session_factory() as session:
                offering = (await session.scalars(select(HistoricalCourseOffering))).one()
                term = (await session.scalars(select(HistoricalTermDataset))).one()
                manifest = (await session.scalars(select(HistoricalArchiveManifest))).one()
                department = (await session.scalars(select(HistoricalCurriculumDepartment))).one()
                relation = (await session.scalars(select(HistoricalCourseRelation))).one()
                assert offering.raw_payload == source_section
                assert offering.raw_payload["syllabus"]["futurePortalField"]["mustRemain"]
                assert term.raw_payload["source"]["futureRootField"] == "보존"
                assert manifest.raw_payload["unknownManifestField"]["mustRemain"]
                assert department.raw_payload["courses"][0]["unknownCurriculumField"] == "보존"
                assert relation.raw_payload["unknownRelationField"] == "보존"
                return offering.id, term.source_archive
        finally:
            await database.close()

    offering_id, source_archive = asyncio.run(prepare())
    expected_uncompressed = gzip.decompress((archive_root / "terms/2020-1.json.gz").read_bytes())
    assert gzip.decompress(source_archive) == expected_uncompressed
    assert offering_id


def test_history_search_detail_and_completed_course_import(tmp_path: Path) -> None:
    archive_root, source_section = _archive(tmp_path)
    settings = _settings(tmp_path)

    async def prepare() -> None:
        database = Database(settings.database_url)
        try:
            await database.create_schema()
            await import_dreams_archive(database, archive_root)
        finally:
            await database.close()

    asyncio.run(prepare())
    mailer = FakeMailer()
    with TestClient(
        create_app(settings, otp_mailer=mailer), base_url="https://testserver"
    ) as client:
        semesters = client.get("/api/v1/history/semesters")
        assert semesters.status_code == 200
        assert semesters.json()["semesters"][0]["semester"] == "2020-1"
        search = client.get(
            "/api/v1/history/courses",
            params={"semester": "2020-1", "q": "데이터 사회", "department": "컴퓨터"},
        )
        assert search.status_code == 200, search.text
        assert search.json()["total"] == 1
        offering_id = search.json()["courses"][0]["id"]
        detail = client.get(f"/api/v1/history/courses/{offering_id}")
        assert detail.status_code == 200
        assert detail.json()["rawPayload"] == source_section

        assert (
            client.post("/api/v1/auth/otp/start", json={"studentNumber": "20260001"}).status_code
            == 202
        )
        assert (
            client.post(
                "/api/v1/auth/otp/verify",
                json={"studentNumber": "20260001", "code": mailer.deliveries[-1][1]},
            ).status_code
            == 200
        )
        imported = client.post(
            "/api/v1/users/me/completed-courses/import-history",
            json={"offeringIds": [offering_id], "status": "COMPLETED"},
        )
        assert imported.status_code == 200, imported.text
        completed = imported.json()["importedCourses"][0]
        assert completed["historicalOfferingId"] == offering_id
        assert completed["sectionCode"] == "01"
        assert completed["semester"] == "2020-1"
        assert completed["category"] == "교양선택"
        assert completed["area"] == "제1영역:인간과소통"
        assert completed["inputSource"] == "HISTORICAL_TIMETABLE"
        duplicate = client.post(
            "/api/v1/users/me/completed-courses/import-history",
            json={"offeringIds": [offering_id], "status": "COMPLETED"},
        )
        assert duplicate.json()["importedCourses"] == []
        assert duplicate.json()["skippedOfferingIds"] == [offering_id]
