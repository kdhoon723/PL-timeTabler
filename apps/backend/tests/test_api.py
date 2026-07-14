from fastapi.testclient import TestClient


def test_liveness_and_readiness(client: TestClient) -> None:
    live = client.get("/api/v1/health/live")
    ready = client.get("/api/v1/health/ready")

    assert live.status_code == 200
    assert live.json() == {"status": "live"}
    assert ready.status_code == 200
    assert ready.json() == {"status": "ready", "catalog": "ready", "database": "ready"}
    assert live.headers["x-request-id"]


def test_catalog_api(client: TestClient) -> None:
    semesters = client.get("/api/v1/semesters")
    assert semesters.status_code == 200
    semester = semesters.json()[0]
    assert semester["id"] == "2026-1"
    assert semester["sectionCount"] == 1576

    catalog = client.get("/api/v1/catalog/2026-1", params={"q": "김선경", "limit": 10})
    assert catalog.status_code == 200
    payload = catalog.json()
    assert payload["total"] >= 1
    assert all("김선경" in (item["professor"] or "") for item in payload["sections"])


def test_optimization_queue_api(client: TestClient) -> None:
    semester = client.get("/api/v1/semesters").json()[0]
    create = client.post(
        "/api/v1/optimizations",
        json={
            "semester": semester["id"],
            "datasetVersion": semester["datasetVersion"],
            "requiredCourseCodes": ["922601"],
            "lockedSectionIds": ["922601-01"],
            "minCredits": 2,
            "maxCredits": 18,
            "targetCredits": 15,
            "preferences": {
                "gapWeightPercent": 75,
                "minimizeChanges": False,
            },
        },
    )
    assert create.status_code == 202
    created = create.json()
    assert created["status"] == "QUEUED"
    assert create.headers["location"].endswith(created["id"])

    fetched = client.get(f"/api/v1/optimizations/{created['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["request"]["requiredCourseCodes"] == ["922601"]
    assert fetched.json()["request"]["targetCredits"] == 15
    assert fetched.json()["request"]["preferences"]["gapWeightPercent"] == 75
    assert fetched.json()["request"]["preferences"]["minimizeChanges"] is False

    cancelled = client.delete(f"/api/v1/optimizations/{created['id']}")
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "CANCELLED"


def test_reject_stale_dataset_and_unknown_sections(client: TestClient) -> None:
    stale = client.post(
        "/api/v1/optimizations",
        json={"datasetVersion": "0" * 64},
    )
    assert stale.status_code == 409

    semester = client.get("/api/v1/semesters").json()[0]
    unknown = client.post(
        "/api/v1/optimizations",
        json={
            "datasetVersion": semester["datasetVersion"],
            "lockedSectionIds": ["missing-01"],
        },
    )
    assert unknown.status_code == 422


def test_reject_invalid_or_duplicate_preferred_days(client: TestClient) -> None:
    semester = client.get("/api/v1/semesters").json()[0]
    base = {"datasetVersion": semester["datasetVersion"]}

    invalid = client.post(
        "/api/v1/optimizations",
        json={**base, "preferences": {"preferredDaysOff": ["Funday"]}},
    )
    duplicate = client.post(
        "/api/v1/optimizations",
        json={**base, "preferences": {"preferredDaysOff": ["금", "금"]}},
    )

    assert invalid.status_code == 422
    assert duplicate.status_code == 422


def test_reject_locked_section_whose_course_is_excluded(client: TestClient) -> None:
    semester = client.get("/api/v1/semesters").json()[0]
    response = client.post(
        "/api/v1/optimizations",
        json={
            "datasetVersion": semester["datasetVersion"],
            "lockedSectionIds": ["922601-01"],
            "excludedCourseCodes": ["922601"],
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == {"lockedSectionsWithExcludedCourses": ["922601-01"]}


def test_reject_unavailable_professor_constraint(client: TestClient) -> None:
    semester = client.get("/api/v1/semesters").json()[0]
    response = client.post(
        "/api/v1/optimizations",
        json={
            "datasetVersion": semester["datasetVersion"],
            "candidateCourseCodes": ["922601"],
            "professorConstraints": [{"courseCode": "922601", "professor": "없는교수"}],
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == {
        "unavailableProfessorConstraints": [{"courseCode": "922601", "professor": "없는교수"}]
    }


def test_reject_fractional_credit_bounds_instead_of_rounding(client: TestClient) -> None:
    semester = client.get("/api/v1/semesters").json()[0]
    response = client.post(
        "/api/v1/optimizations",
        json={
            "datasetVersion": semester["datasetVersion"],
            "minCredits": 12.5,
            "maxCredits": 18,
        },
    )

    assert response.status_code == 422


def test_openapi_exposes_only_implemented_product_endpoints(client: TestClient) -> None:
    document = client.get("/openapi.json").json()
    paths = set(document["paths"])

    assert "/api/v1/health/live" in paths
    assert "/api/v1/catalog/{semester}" in paths
    assert "/api/v1/optimizations" in paths
    assert "/api/v1/optimizations/compare" in paths
    assert "/api/v1/timetables/{timetable_id}/shares" in paths
    assert not any("curricula" in path for path in paths)


def test_compare_timetable_candidates(client: TestClient) -> None:
    compared = client.post(
        "/api/v1/optimizations/compare",
        json={
            "currentSectionIds": ["922601-01"],
            "candidateSectionIds": [["922601-02"], ["922601-01", "927283-01"]],
        },
    )

    assert compared.status_code == 200, compared.text
    candidates = compared.json()["candidates"]
    assert candidates[0]["swapped"] == [
        {"fromSectionId": "922601-01", "toSectionId": "922601-02"}
    ]
    assert candidates[0]["added"] == []
    assert candidates[0]["removed"] == []
    assert candidates[1]["metrics"]["totalCredits"] > 0
