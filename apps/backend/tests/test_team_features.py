from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from fastapi.testclient import TestClient

from timetabler.api.app import create_app
from timetabler.config import Settings, repository_root


@dataclass(slots=True)
class FakeMailer:
    deliveries: list[tuple[str, str, str]] = field(default_factory=list)

    async def send_otp(self, recipient: str, code: str, *, challenge_id: str) -> None:
        self.deliveries.append((recipient, code, challenge_id))


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        environment="test",
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'features.db'}",
        data_root=repository_root() / "data",
        catalog_validate_checksums=True,
        auto_create_schema=True,
        cors_origins=["https://testserver"],
        auth_enabled=True,
        auth_hmac_secret="team-feature-test-secret-that-is-more-than-32-bytes",
        auth_email_provider="disabled",
    )


def _login(client: TestClient, mailer: FakeMailer, student_number: str = "20260001") -> None:
    assert (
        client.post("/api/v1/auth/otp/start", json={"studentNumber": student_number}).status_code
        == 202
    )
    code = mailer.deliveries[-1][1]
    assert (
        client.post(
            "/api/v1/auth/otp/verify",
            json={"studentNumber": student_number, "code": code},
        ).status_code
        == 200
    )


def test_account_profile_consent_and_deletion(tmp_path: Path) -> None:
    mailer = FakeMailer()
    with TestClient(
        create_app(_settings(tmp_path), otp_mailer=mailer), base_url="https://testserver"
    ) as client:
        _login(client, mailer)
        account = client.get("/api/v1/users/me")
        assert account.status_code == 200
        assert account.json()["studentNumber"] == "20260001"
        assert account.json()["profileCompleted"] is False

        updated = client.patch(
            "/api/v1/users/me",
            json={
                "name": "홍길동",
                "grade": 3,
                "department": "컴퓨터공학전공",
                "admissionYear": 2024,
                "entryType": "FRESHMAN",
                "studentType": "DOMESTIC",
                "sectionGroup": "ODD",
                "majorPath": "ADVANCED_MAJOR",
            },
        )
        assert updated.status_code == 200
        assert updated.json()["profileCompleted"] is False

        consent = client.post(
            "/api/v1/users/me/consents",
            json={"consentVersion": "2026-07", "agreed": True},
        )
        assert consent.status_code == 201
        assert client.get("/api/v1/users/me/consents").json()[0]["consentVersion"] == "2026-07"
        assert client.get("/api/v1/users/me").json()["profileCompleted"] is True

        deleted = client.request("DELETE", "/api/v1/users/me", json={"confirmation": "회원탈퇴"})
        assert deleted.status_code == 200
        assert client.get("/api/v1/users/me").status_code == 401


def test_timetable_review_completed_course_and_popularity_flows(tmp_path: Path) -> None:
    mailer = FakeMailer()
    with TestClient(
        create_app(_settings(tmp_path), otp_mailer=mailer), base_url="https://testserver"
    ) as client:
        _login(client, mailer)
        timetable = client.post(
            "/api/v1/timetables",
            json={
                "name": "1학기 계획",
                "semester": "2026-1",
                "items": [
                    {
                        "sectionId": "922601-01",
                        "role": "want",
                        "locked": False,
                        "professorLocked": False,
                    }
                ],
                "preferences": {"targetCredits": 18},
            },
        )
        assert timetable.status_code == 201, timetable.text
        timetable_id = timetable.json()["timetable"]["id"]
        assert timetable.json()["metrics"]["credits"] == 2
        assert client.get("/api/v1/timetables").json()["total"] == 1

        favorite = client.patch(
            f"/api/v1/timetables/{timetable_id}/favorite", json={"favorite": True}
        )
        assert favorite.status_code == 200 and favorite.json()["favorite"] is True
        copied = client.post(f"/api/v1/timetables/{timetable_id}/copy", json={})
        assert copied.status_code == 201
        assert client.get("/api/v1/timetables", params={"favorite": True}).json()["total"] == 1

        share = client.post(f"/api/v1/timetables/{timetable_id}/shares", json={})
        assert share.status_code == 201
        shared = client.get(f"/api/v1/shared-timetables/{share.json()['shareCode']}")
        assert shared.status_code == 200
        assert shared.json()["timetable"]["name"] == "1학기 계획"

        imported = client.post(
            "/api/v1/users/me/completed-courses/import-timetable",
            json={"timetableId": timetable_id, "status": "IN_PROGRESS"},
        )
        assert imported.status_code == 200
        imported_id = imported.json()["importedCourses"][0]["id"]
        completed = client.patch(
            f"/api/v1/users/me/completed-courses/{imported_id}",
            json={"status": "COMPLETED"},
        )
        assert completed.status_code == 200
        summary = client.get("/api/v1/users/me/completed-courses/summary")
        assert summary.json()["totalCredits"] == 2
        assert summary.json()["liberalCredits"] == 2

        evaluation = client.post(
            "/api/v1/requirements/evaluate",
            json={
                "admissionYear": 2026,
                "departmentId": "컴퓨터공학전공",
                "studentType": "DOMESTIC",
                "programPath": "ADVANCED_MAJOR",
            },
        )
        assert evaluation.status_code == 200, evaluation.text
        major_required = next(
            item
            for item in evaluation.json()["requiredCourseStatus"]
            if item["kind"] == "MAJOR_REQUIRED_COURSES"
        )
        assert major_required["satisfied"] is False
        assert "운영체제론" in major_required["missing"]

        review = client.post(
            "/api/v1/courses/922601/reviews",
            json={
                "professor": "김선경",
                "semester": "2026-1",
                "rating": 5,
                "content": "수업 구성이 좋았습니다.",
            },
        )
        assert review.status_code == 201, review.text
        review_id = review.json()["review"]["id"]
        assert review.json()["ratingSummary"]["averageRating"] == 5
        assert client.get("/api/v1/users/me/reviews").json()["total"] == 1
        popular = client.get(
            "/api/v1/courses",
            params={"sort": "POPULARITY", "order": "DESC", "size": 5},
        )
        assert popular.status_code == 200
        assert popular.json()["courses"][0]["courseCode"] == "922601"
        updated_review = client.patch(
            f"/api/v1/reviews/{review_id}", json={"rating": 4, "content": "수정한 리뷰"}
        )
        assert updated_review.json()["review"]["rating"] == 4
        assert client.delete(f"/api/v1/reviews/{review_id}").status_code == 200
