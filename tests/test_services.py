"""Tests for the curated services manager (win32 layer mocked)."""

from __future__ import annotations

from sifty.core import services
from sifty.windows import services_api


def test_can_manage_allowlist_and_denylist():
    assert services.can_manage("DiagTrack") is True       # on the allowlist
    assert services.can_manage("RpcSs") is False           # critical denylist
    assert services.can_manage("SomeRandomSvc") is False   # not curated


def test_set_start_type_refuses_off_allowlist(monkeypatch):
    called = []
    monkeypatch.setattr(services_api, "set_start_type", lambda n, m: called.append((n, m)) or True)
    # Off-allowlist is refused without ever touching the OS layer.
    assert services.set_start_type("RpcSs", "disabled") is False
    assert called == []
    # Invalid mode refused too.
    assert services.set_start_type("DiagTrack", "bogus") is False
    assert called == []
    # Allowed service + valid mode goes through.
    assert services.set_start_type("DiagTrack", "disabled") is True
    assert called == [("DiagTrack", "disabled")]


def test_list_services_maps_state(monkeypatch):
    monkeypatch.setattr(
        services_api, "get_start_type",
        lambda name: "disabled" if name == "DiagTrack" else None,
    )
    items = {s.name: s for s in services.list_services()}
    assert items["DiagTrack"].start_type == "disabled" and items["DiagTrack"].present
    assert items["Fax"].start_type == "absent" and items["Fax"].present is False
