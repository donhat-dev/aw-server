import random
from datetime import datetime, timedelta

import pytest


@pytest.fixture()
def bucket(flask_client):
    "Context manager for creating and deleting a testing bucket"
    try:
        bucket_id = "test"
        r = flask_client.post(
            f"/api/0/buckets/{bucket_id}",
            json={"client": "test", "type": "test", "hostname": "test"},
        )
        assert r.status_code == 200
        yield bucket_id
    finally:
        r = flask_client.delete(f"/api/0/buckets/{bucket_id}")
        assert r.status_code == 200


def test_info(flask_client):
    r = flask_client.get("/api/0/info")
    assert r.status_code == 200
    assert r.json["testing"]


def test_buckets(flask_client, bucket, benchmark):
    @benchmark
    def list_buckets():
        r = flask_client.get("/api/0/buckets/")
        print(r.json)
        assert r.status_code == 200
        assert len(r.json) == 1


def test_heartbeats(flask_client, bucket, benchmark):
    # FIXME: Currently tests using the memory storage method
    # TODO: Test with a longer data section and see if there's a significant difference
    # TODO: Test with a larger bucket and see if there's a significant difference
    @benchmark
    def heartbeat():
        now = datetime.now()
        r = flask_client.post(
            f"/api/0/buckets/{bucket}/heartbeat?pulsetime=1",
            json={"timestamp": now, "duration": 0, "data": {"random": random.random()}},
        )
        assert r.status_code == 200


def test_get_events(flask_client, bucket, benchmark):
    n_events = 100
    start_time = datetime.now() - timedelta(days=100)
    for i in range(n_events):
        now = start_time + timedelta(hours=i)
        r = flask_client.post(
            f"/api/0/buckets/{bucket}/heartbeat?pulsetime=0",
            json={"timestamp": now, "duration": 0, "data": {"random": random.random()}},
        )
        assert r.status_code == 200

    @benchmark
    def get_events():
        r = flask_client.get(f"/api/0/buckets/{bucket}/events")
        assert r.status_code == 200
        assert r.json
        assert len(r.json) == n_events

        r = flask_client.get(f"/api/0/buckets/{bucket}/events?limit=-1")
        assert r.status_code == 200
        assert r.json
        assert len(r.json) == n_events

        r = flask_client.get(f"/api/0/buckets/{bucket}/events?limit=10")
        assert r.status_code == 200
        assert r.json
        assert len(r.json) == 10

        r = flask_client.get(f"/api/0/buckets/{bucket}/events?limit=100")
        assert r.status_code == 200
        assert r.json
        assert len(r.json) == n_events

        r = flask_client.get(f"/api/0/buckets/{bucket}/events?limit=1000")
        assert r.status_code == 200
        assert r.json
        assert len(r.json) == n_events


def test_get_event_asset(flask_client, bucket, tmp_path):
    asset_dir = tmp_path / "screenshots" / "2025" / "01" / "01" / "12"
    asset_dir.mkdir(parents=True)
    asset_path = asset_dir / "screenshot-test-display-0.webp"
    asset_bytes = b"RIFFxxxxWEBPVP8 "
    asset_path.write_bytes(asset_bytes)

    now = datetime.now()
    r = flask_client.post(
        f"/api/0/buckets/{bucket}/heartbeat?pulsetime=0",
        json={
            "timestamp": now,
            "duration": 0,
            "data": {
                "local_dir": str(asset_dir),
                "images": [
                    {
                        "monitor_id": "display-0",
                        "path": str(asset_path),
                        "relative_path": "2025/01/01/12/screenshot-test-display-0.webp",
                    }
                ],
            },
        },
    )
    assert r.status_code == 200
    events_response = flask_client.get(f"/api/0/buckets/{bucket}/events")
    assert events_response.status_code == 200
    assert len(events_response.json) == 1
    event_id = events_response.json[0]["id"]

    asset_response = flask_client.get(
        f"/api/0/buckets/{bucket}/events/{event_id}/assets/0"
    )
    assert asset_response.status_code == 200
    assert asset_response.data == asset_bytes


# TODO: Add benchmark for basic AFK-filtering query
