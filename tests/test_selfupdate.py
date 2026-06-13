"""Tests for self-update version checks and the editable-install guard."""

from __future__ import annotations

import json

from sifty.core import selfupdate


class _FakeDist:
    """Stand-in for importlib.metadata.Distribution with a canned direct_url.json."""

    def __init__(self, payload: str | None) -> None:
        self._payload = payload

    def read_text(self, name: str) -> str | None:
        assert name == "direct_url.json"
        return self._payload


def _patch_dist(monkeypatch, payload: str | None) -> None:
    monkeypatch.setattr(selfupdate, "distribution", lambda _pkg: _FakeDist(payload))


def test_editable_install_detected(monkeypatch):
    payload = json.dumps({"url": "file:///C:/Users/u/proj", "dir_info": {"editable": True}})
    _patch_dist(monkeypatch, payload)
    assert selfupdate.is_editable_install() is True
    assert selfupdate.editable_install_path() is not None


def test_normal_pypi_install_not_editable(monkeypatch):
    # A wheel install from an index records a https url and no editable marker.
    payload = json.dumps({"url": "https://files.pythonhosted.org/x/sifty.whl"})
    _patch_dist(monkeypatch, payload)
    assert selfupdate.is_editable_install() is False
    assert selfupdate.editable_install_path() is None


def test_no_direct_url_metadata(monkeypatch):
    # Most index installs have no direct_url.json at all.
    _patch_dist(monkeypatch, None)
    assert selfupdate.is_editable_install() is False


def test_editable_marker_false(monkeypatch):
    payload = json.dumps({"url": "file:///x", "dir_info": {"editable": False}})
    _patch_dist(monkeypatch, payload)
    assert selfupdate.is_editable_install() is False


def test_malformed_direct_url(monkeypatch):
    _patch_dist(monkeypatch, "{not valid json")
    assert selfupdate.is_editable_install() is False


def test_package_not_found(monkeypatch):
    def _raise(_pkg):
        raise selfupdate.PackageNotFoundError

    monkeypatch.setattr(selfupdate, "distribution", _raise)
    assert selfupdate.is_editable_install() is False


def test_apply_update_refuses_editable(monkeypatch):
    # The guard must short-circuit before any pipx subprocess runs.
    monkeypatch.setattr(selfupdate, "is_editable_install", lambda: True)
    called = False

    def _fail(*a, **k):
        nonlocal called
        called = True
        raise AssertionError("pipx must not be invoked on an editable install")

    monkeypatch.setattr(selfupdate.subprocess, "run", _fail)
    ok, msg = selfupdate.apply_update()
    assert ok is False
    assert "editable" in msg.lower()
    assert called is False
