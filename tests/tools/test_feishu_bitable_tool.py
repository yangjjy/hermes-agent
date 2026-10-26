"""Bitable reads use the admitted DM client, never a Runtime/CLI credential fallback."""
import json
from types import SimpleNamespace
import pytest
from tools import feishu_bitable_tool as bitable
from tools import feishu_lark
from toolsets import resolve_toolset

URL = 'https://example.feishu.cn/base/base123?table=tbl123&view=vew123'

@pytest.fixture(autouse=True)
def clear_client():
    with feishu_lark.client_scope(None):
        yield


def bind(monkeypatch, pages):
    seen = []
    monkeypatch.setattr(bitable, 'build_request', lambda method, uri, **kw: (method, uri, kw))
    def request(req):
        seen.append(req)
        return pages.pop(0)
    client = SimpleNamespace(request=request, _config=SimpleNamespace(app_id='synthetic-app'))
    feishu_lark.set_client(client)
    return seen


def response(data, code=0):
    return SimpleNamespace(code=code, data=data)


def test_fields_use_existing_client_and_keep_application_identity(monkeypatch):
    seen = bind(monkeypatch, [response({'items': [{'field_id': 'fld1', 'field_name': '企业名称', 'type': 1}], 'has_more': False})])
    result = json.loads(bitable.read_fields({'base_url': URL}))
    assert result['field_count'] == 1
    assert result['identity'] == {'app_id': 'synthetic-app', 'token_type': 'tenant_access_token'}
    assert seen[0][0] == 'GET'
    assert seen[0][2]['paths'] == {'app_token': 'base123', 'table_id': 'tbl123'}
    assert ('view_id', 'vew123') in seen[0][2]['queries']


def test_all_1463_records_are_counted_across_eight_pages_without_payload_leak(monkeypatch):
    pages = []
    for page in range(8):
        start, end = page * 200, min((page + 1) * 200, 1463)
        pages.append(response({'items': [{'record_id': f'rec{i}', 'fields': {'企业名称': 'private-company'}} for i in range(start, end)], 'has_more': page < 7, 'page_token': f'cursor{page}' if page < 7 else None, 'total': 1463}))
    seen = bind(monkeypatch, pages)
    result = json.loads(bitable.read_records({'base_url': URL}))
    assert result['complete'] is True
    assert result['record_count'] == result['unique_record_count'] == 1463
    assert result['page_count'] == 8
    assert len(seen) == 8
    assert 'private-company' not in json.dumps(result)
    assert 'items' not in result


@pytest.mark.parametrize('url', ['https://evil.test/base/base123?table=tbl123', 'https://feishu.cn.evil.test/base/base123?table=tbl123', 'https://example.feishu.cn/base/base123?table=tbl123&table=tbl456', 'https://u:p@example.feishu.cn/base/base123?table=tbl123'])
def test_invalid_reference_never_dispatches(monkeypatch, url):
    seen = bind(monkeypatch, [])
    assert 'error' in json.loads(bitable.read_records({'base_url': url}))
    assert not seen


def test_no_bound_client_has_no_credential_or_runtime_fallback():
    assert 'error' in json.loads(bitable.read_records({'base_url': URL}))


def test_role_denial_stops_without_retry_or_user_fallback(monkeypatch):
    seen = bind(monkeypatch, [response({}, code=1254302)])
    result = json.loads(bitable.read_records({'base_url': URL}))
    assert result['api_code'] == 1254302
    assert result['identity']['token_type'] == 'tenant_access_token'
    assert result['complete'] is False
    assert len(seen) == 1


@pytest.mark.parametrize('second', ['duplicate_record', 'repeated_cursor', 'missing_cursor'])
def test_broken_pagination_never_claims_complete(monkeypatch, second):
    pages = [response({'items': [{'record_id': 'rec1'}], 'has_more': True, 'page_token': 'cursor1'})]
    pages.append(response({'items': [{'record_id': 'rec1' if second == 'duplicate_record' else 'rec2'}], 'has_more': True, 'page_token': 'cursor1' if second == 'repeated_cursor' else None}))
    seen = bind(monkeypatch, pages)
    result = json.loads(bitable.read_records({'base_url': URL}))
    assert result['complete'] is False
    assert 'error' in result
    assert len(seen) == 2


def test_feishu_exposes_bitable_without_enabling_terminal_or_comment_writes():
    names = resolve_toolset('feishu_bitable')
    assert set(names) == {'feishu_bitable_read_fields', 'feishu_bitable_read_records'}
    assert set(names) <= set(resolve_toolset('hermes-feishu'))
    assert 'terminal' not in names
    assert 'feishu_bitable_read_records' not in resolve_toolset('feishu_drive')


def test_explicit_runtime_only_profile_still_gets_scoped_native_bitable_tools():
    from hermes_cli.tools_config import _get_platform_tools
    from model_tools import get_tool_definitions
    config = {'platform_toolsets': {'feishu': ['aios_runtime']}, 'mcp_servers': {}}
    enabled = _get_platform_tools(config, 'feishu')
    assert 'feishu_bitable' in enabled
    definitions = get_tool_definitions(enabled_toolsets=sorted(enabled), quiet_mode=True, skip_tool_search_assembly=True)
    names = {s['function']['name'] for s in definitions}
    assert {'feishu_bitable_read_fields', 'feishu_bitable_read_records'} <= names
    assert 'terminal' not in names


def test_native_request_allows_tenant_identity_only():
    from lark_oapi.core.enum import AccessTokenType
    req = bitable.build_request('GET', '/open-apis/bitable/v1/apps/:app_token/tables/:table_id/fields', paths={'app_token': 'base123', 'table_id': 'tbl123'})
    assert req.token_types == {AccessTokenType.TENANT}


def test_transport_error_does_not_leak_credentials_or_retry(monkeypatch):
    seen = []
    monkeypatch.setattr(bitable, 'build_request', lambda *a, **k: object())
    def fail(request):
        seen.append(request)
        raise ValueError('synthetic-sensitive-token')
    feishu_lark.set_client(SimpleNamespace(request=fail))
    result = bitable.read_records({'base_url': URL})
    assert json.loads(result)['complete'] is False
    assert 'synthetic-sensitive-token' not in result
    assert len(seen) == 1
