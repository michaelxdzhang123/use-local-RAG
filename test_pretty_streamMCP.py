import json
import sys
import types

import pytest

# Stub optional runtime deps so unit tests can import module helpers
anyio_stub = types.ModuleType("anyio")
anyio_stub.run = lambda *args, **kwargs: None
sys.modules.setdefault("anyio", anyio_stub)

mcp_stub = types.ModuleType("mcp")
mcp_stub.ClientSession = object
sys.modules.setdefault("mcp", mcp_stub)

mcp_client_stub = types.ModuleType("mcp.client")
sys.modules.setdefault("mcp.client", mcp_client_stub)

mcp_streamable_stub = types.ModuleType("mcp.client.streamable_http")
mcp_streamable_stub.streamable_http_client = object
sys.modules.setdefault("mcp.client.streamable_http", mcp_streamable_stub)

from pretty_streamMCP import _normalize_ids, load_dataset_ids_from_mcp_info


def test_normalize_ids_with_string():
    assert _normalize_ids(" abc ") == ["abc"]


def test_normalize_ids_with_list_and_blanks():
    assert _normalize_ids([" a ", "", "  ", "b"]) == ["a", "b"]


def test_load_dataset_ids_prefers_dataset_ids(tmp_path):
    p = tmp_path / "mcp_info.json"
    payload = [
        {
            "name": "HWind",
            "dataset_ids": ["id-1", "id-2"],
            "content_id": "legacy-id",
        }
    ]
    p.write_text(json.dumps(payload), encoding="utf-8")

    assert load_dataset_ids_from_mcp_info("hwind", str(p)) == ["id-1", "id-2"]


def test_load_dataset_ids_fallback_to_content_id(tmp_path):
    p = tmp_path / "mcp_info.json"
    payload = [{"name": "Others", "content_id": "single-id"}]
    p.write_text(json.dumps(payload), encoding="utf-8")

    assert load_dataset_ids_from_mcp_info("others", str(p)) == ["single-id"]


def test_load_dataset_ids_missing_file():
    with pytest.raises(FileNotFoundError):
        load_dataset_ids_from_mcp_info("HWind", "missing.json")


def test_load_dataset_ids_invalid_top_level(tmp_path):
    p = tmp_path / "mcp_info.json"
    p.write_text(json.dumps({"name": "bad"}), encoding="utf-8")

    with pytest.raises(ValueError):
        load_dataset_ids_from_mcp_info("HWind", str(p))


def test_load_dataset_ids_missing_content_name(tmp_path):
    p = tmp_path / "mcp_info.json"
    p.write_text(json.dumps([{"name": "Others", "content_id": "x"}]), encoding="utf-8")

    with pytest.raises(KeyError):
        load_dataset_ids_from_mcp_info("HWind", str(p))


def test_load_dataset_ids_content_without_ids(tmp_path):
    p = tmp_path / "mcp_info.json"
    p.write_text(json.dumps([{"name": "HWind"}]), encoding="utf-8")

    with pytest.raises(ValueError):
        load_dataset_ids_from_mcp_info("HWind", str(p))
