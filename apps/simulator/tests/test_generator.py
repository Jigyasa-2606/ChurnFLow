from simulator.generator import EVENT_TYPES, make_event


def test_make_event_has_stable_schema() -> None:
    event = make_event("cust_0042", event_type="purchase")
    assert event["event_id"].startswith("evt_")
    assert event["customer_id"] == "cust_0042"
    assert event["event_type"] == "purchase"
    assert event["ts"].endswith("Z")
    assert "amount" in event["payload"]
    assert "category" in event["payload"]


def test_event_types_are_the_v1_set() -> None:
    assert EVENT_TYPES == (
        "page_view",
        "add_to_cart",
        "purchase",
        "session_end",
        "support_ticket",
    )


def test_event_ids_are_unique() -> None:
    ids = {make_event("cust_0001")["event_id"] for _ in range(50)}
    assert len(ids) == 50
