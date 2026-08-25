from api.scoring import features_from_redis_hash

def test_redis_hash_skips_metadata_and_keeps_train_order() -> None:
    raw = {
        "frequency_90d": "2",
        "monetary_90d": "30",
        "_observation_time": "2026-08-25T11:00:00+00:00",
        "_features_version": "v1",
    }
    vector, values, version = features_from_redis_hash(raw, ["monetary_90d", "frequency_90d"])
    assert version == "v1"
    assert values["frequency_90d"] == 2.0
    assert list(vector) == [30.0, 2.0]


def test_missing_feature_raises() -> None:
    try:
        features_from_redis_hash({"frequency_90d": "1"}, ["frequency_90d", "monetary_90d"])
    except ValueError as exc:
        assert "monetary_90d" in str(exc)
    else:
        raise AssertionError("expected ValueError")
