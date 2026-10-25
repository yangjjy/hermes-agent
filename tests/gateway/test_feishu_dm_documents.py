"""DM document access must use the admitted adapter, including across tool workers."""

import asyncio
import json
from types import SimpleNamespace

import pytest

from plugins.platforms.feishu.adapter import FeishuAdapter
from tools import feishu_doc_tool, feishu_lark


def test_dm_client_reaches_worker_and_is_cleared():
    adapter = object.__new__(FeishuAdapter)
    adapter._chat_locks = {}
    adapter._client = object()
    event = SimpleNamespace(source=SimpleNamespace(chat_id="dm"))
    seen = []

    async def handle(_event):
        seen.append(await asyncio.to_thread(feishu_lark.get_client))

    adapter.handle_message = handle
    asyncio.run(adapter._handle_message_with_guards(event))
    assert seen == [adapter._client]
    assert feishu_lark.get_client() is None


def test_concurrent_adapters_keep_their_clients_and_restore_on_error():
    async def exercise():
        seen = []
        ready = asyncio.Event()
        async def run(label):
            adapter = object.__new__(FeishuAdapter)
            adapter._chat_locks = {}
            adapter._client = object()
            async def handle(event):
                ready.set()
                await asyncio.sleep(0)
                await ready.wait()
                seen.append((label, await asyncio.to_thread(feishu_lark.get_client), adapter._client))
                raise RuntimeError("turn failed")
            adapter.handle_message = handle
            with pytest.raises(RuntimeError, match="turn failed"):
                await adapter._handle_message_with_guards(SimpleNamespace(source=None))
            assert feishu_lark.get_client() is None
        await asyncio.gather(run("a"), run("b"))
        assert len(seen) == 2
        assert all(actual is expected for _, actual, expected in seen)
    asyncio.run(exercise())


@pytest.mark.parametrize("reference,wiki", [
    ("doc123", False),
    ("https://example.feishu.cn/docx/doc123?from=share", False),
    ("https://example.feishu.cn/wiki/wiki123", True),
])
def test_document_and_wiki_reads_reuse_bound_client(monkeypatch, reference, wiki):
    requests = []
    monkeypatch.setattr(feishu_doc_tool, "build_request", lambda method, uri, **kw: (method, uri, kw))
    class Client:
        def request(self, request):
            requests.append(request)
            data = {"node": {"obj_type": "docx", "obj_token": "doc123"}} if "wiki/v2" in request[1] else {"content": "shared content"}
            return SimpleNamespace(code=0, data=data)
    feishu_lark.set_client(Client())
    try:
        result = json.loads(feishu_doc_tool._handle_feishu_doc_read({"doc_token": reference}))
    finally:
        feishu_lark.set_client(None)
    assert result["content"] == "shared content"
    assert len(requests) == (2 if wiki else 1)
    assert all(req[0] == "GET" for req in requests)
    assert requests[-1][2]["paths"] == {"document_id": "doc123"}


def test_wiki_permission_denial_never_reads_document(monkeypatch):
    requests = []
    monkeypatch.setattr(feishu_doc_tool, "build_request", lambda method, uri, **kw: uri)
    class Client:
        def request(self, request):
            requests.append(request)
            return SimpleNamespace(code=99991672, msg="access denied", data={})
    feishu_lark.set_client(Client())
    try:
        result = json.loads(feishu_doc_tool._handle_feishu_doc_read({"doc_token": "https://example.feishu.cn/wiki/wiki123"}))
    finally:
        feishu_lark.set_client(None)
    assert "error" in result
    assert len(requests) == 1
    assert "wiki/v2" in requests[0]


def test_unbound_document_read_fails_closed():
    feishu_lark.set_client(None)
    assert "error" in json.loads(feishu_doc_tool._handle_feishu_doc_read({"doc_token": "doc123"}))


def test_comment_client_propagates_to_worker_and_nested_scope_restores():
    comment_client, dm_client = object(), object()
    feishu_lark.set_client(comment_client)
    try:
        async def observe():
            assert await asyncio.to_thread(feishu_lark.get_client) is comment_client
            with feishu_lark.client_scope(dm_client):
                assert await asyncio.to_thread(feishu_lark.get_client) is dm_client
            assert feishu_lark.get_client() is comment_client
        asyncio.run(observe())
    finally:
        feishu_lark.set_client(None)


@pytest.mark.parametrize("reference", ["https://evil.example/wiki/wiki123", "https://feishu.cn.evil.example/docx/doc123", "../doc123"])
def test_invalid_reference_has_no_transport(monkeypatch, reference):
    def no_request(*args, **kwargs):
        pytest.fail("invalid reference reached transport")
    feishu_lark.set_client(SimpleNamespace(request=no_request))
    try:
        assert "error" in json.loads(feishu_doc_tool._handle_feishu_doc_read({"doc_token": reference}))
    finally:
        feishu_lark.set_client(None)


@pytest.mark.parametrize("node", [{"obj_type": "sheet", "obj_token": "sheet123"}, {"obj_type": "docx"}])
def test_non_document_or_incomplete_wiki_target_stops(monkeypatch, node):
    calls = []
    monkeypatch.setattr(feishu_doc_tool, "build_request", lambda method, uri, **kw: uri)
    def request(req):
        calls.append(req)
        return SimpleNamespace(code=0, data={"node": node})
    feishu_lark.set_client(SimpleNamespace(request=request))
    try:
        assert "error" in json.loads(feishu_doc_tool._handle_feishu_doc_read({"doc_token": "https://example.feishu.cn/wiki/wiki123"}))
    finally:
        feishu_lark.set_client(None)
    assert calls == ["/open-apis/wiki/v2/spaces/get_node"]
