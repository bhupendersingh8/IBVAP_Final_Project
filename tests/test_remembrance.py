import pytest
import os
import shutil
from services.tracking.remembrance_store import LongTermRemembranceStore

TEST_STORE_PATH = os.path.join(os.path.dirname(__file__), "test_remembrance_store.json")

@pytest.fixture(autouse=True)
def cleanup():
    if os.path.exists(TEST_STORE_PATH):
        os.remove(TEST_STORE_PATH)
    yield
    if os.path.exists(TEST_STORE_PATH):
        os.remove(TEST_STORE_PATH)

def test_remembrance_store_vehicle_and_plate():
    store = LongTermRemembranceStore(store_path=TEST_STORE_PATH)
    store.clear()

    # 1. Sighting of a truck without plate
    p1 = store.record_sighting(
        camera_id="CAM-01",
        track_id=101,
        class_name="vehicle",
        subclass="truck",
        bbox={"x1": 0.1, "y1": 0.1, "x2": 0.3, "y2": 0.3},
        confidence=0.88
    )
    assert p1.global_id == "REID-V001"
    assert p1.subclass == "truck"
    assert p1.total_sightings == 1

    # 2. Later, ANPR resolves the plate for the same truck
    p2 = store.record_sighting(
        camera_id="CAM-01",
        track_id=101,
        class_name="vehicle",
        subclass="truck",
        plate="DL01AB1234",
        plate_conf=0.92
    )
    assert p2.global_id == "REID-V001"
    assert p2.license_plate == "DL01AB1234"
    assert p2.total_sightings == 2

    # 3. New camera (CAM-02), car with a different plate
    p3 = store.record_sighting(
        camera_id="CAM-02",
        track_id=202,
        class_name="vehicle",
        subclass="car",
        plate="MH12CD5678",
        plate_conf=0.85
    )
    assert p3.global_id == "REID-V002"
    assert p3.subclass == "car"

    # 4. Same truck reappears hours later on CAM-03 with track_id 303, but same plate
    p4 = store.record_sighting(
        camera_id="CAM-03",
        track_id=303,
        class_name="vehicle",
        subclass="truck",
        plate="DL01AB1234",
        plate_conf=0.95
    )
    # Must match existing profile REID-V001!
    assert p4.global_id == "REID-V001"
    assert p4.total_sightings == 3
    assert "CAM-03" in p4.cameras_seen

    # 5. Person re-identification
    p_person = store.record_sighting(
        camera_id="CAM-01",
        track_id=404,
        class_name="person",
        subclass="person"
    )
    assert p_person.global_id == "REID-P001"
    assert p_person.entity_type == "person"

    all_profs = store.get_all_profiles()
    assert len(all_profs) == 3
