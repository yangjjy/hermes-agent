"""Read-only Bitable extension of the admitted turn-scoped Feishu client."""
import re
from urllib.parse import parse_qs, urlsplit

from tools.feishu_lark import _check_feishu, build_request, get_client, response_data
from tools.registry import registry, tool_error, tool_result

_FIELDS = '/open-apis/bitable/v1/apps/:app_token/tables/:table_id/fields'
_RECORDS = '/open-apis/bitable/v1/apps/:app_token/tables/:table_id/records'
_MAX_PAGES = 32
_PAGE_SIZE = 200


def _reference(args):
    url = urlsplit(args.get('base_url', ''))
    host = url.hostname or ''
    trusted = any(host == d or host.endswith('.' + d) for d in ('feishu.cn', 'larksuite.com'))
    match = re.fullmatch(r'/base/([A-Za-z0-9_-]+)/?', url.path)
    if url.scheme != 'https' or not trusted or url.username or url.password or not match or url.port not in (None, 443):
        raise ValueError('Expected an HTTPS Feishu/Lark /base/ URL')
    query = parse_qs(url.query, keep_blank_values=True)
    ids = {}
    for key, prefix in [('table', 'tbl'), ('view', 'vew')]:
        values = query.get(key, [])
        explicit = args.get(key + '_id')
        if len(values) > 1 or (explicit and values and explicit != values[0]):
            raise ValueError('Conflicting table/view identity')
        value = explicit or (values[0] if values else None)
        if value is None and key == 'view':
            continue
        if not isinstance(value, str) or not re.fullmatch(prefix + r'[A-Za-z0-9_-]+', value):
            raise ValueError('An exact table ID and valid optional view ID are required')
        ids[key + '_id'] = value
    return match.group(1), ids


def _identity(client):
    return {'app_id': getattr(getattr(client, '_config', None), 'app_id', None),
            'token_type': 'tenant_access_token'}


def _page(client, uri, paths, view_id, cursor):
    queries = [('page_size', str(_PAGE_SIZE))]
    if view_id:
        queries.append(('view_id', view_id))
    if cursor:
        queries.append(('page_token', cursor))
    request = build_request('GET', uri, paths=paths, queries=queries)
    try:
        response = client.request(request)
    except (OSError, ValueError, RuntimeError):
        raise RuntimeError('Bitable transport failed') from None
    code = getattr(response, 'code', None)
    if code != 0:
        return None, code
    return response_data(response), 0


def _collect(client, uri, paths, view_id, fields):
    cursor = None
    cursors, record_ids = set(), set()
    items, counts = [], []
    total = None
    for _ in range(_MAX_PAGES):
        data, code = _page(client, uri, paths, view_id, cursor)
        if data is None:
            return {'error': 'Bitable API refused the read; no retry or identity fallback',
                    'api_code': code, 'complete': False, 'page_count': len(counts)}
        rows = data.get('items')
        if not isinstance(rows, list) or type(data.get('has_more')) is not bool:
            raise ValueError('Incomplete Bitable page envelope')
        observed_total = data.get('total')
        if observed_total is not None:
            if type(observed_total) is not int or observed_total < 0 or (total is not None and total != observed_total):
                raise ValueError('Bitable total changed across pages')
            total = observed_total
        for item in rows:
            key = item.get('field_id' if fields else 'record_id')
            if not isinstance(key, str) or not key or key in record_ids:
                raise ValueError('Missing or duplicate source ID')
            record_ids.add(key)
            if fields:
                items.append({k: item.get(k) for k in ('field_id', 'field_name', 'type')})
        counts.append(len(rows))
        if data['has_more'] is False:
            if total is not None and total != len(record_ids):
                raise ValueError('Bitable total does not reconcile with unique source IDs')
            result = {'complete': True, 'page_count': len(counts), 'page_record_counts': counts,
                      'identity': _identity(client), 'view_id': view_id}
            if fields:
                result.update(field_count=len(items), fields=items)
            else:
                result.update(record_count=len(record_ids), unique_record_count=len(record_ids),
                              api_total=total, independent_count_verified=False)
            return result
        cursor = data.get('page_token')
        if not isinstance(cursor, str) or not cursor or cursor in cursors:
            raise ValueError('Missing or repeated pagination cursor')
        cursors.add(cursor)
    raise ValueError('Bitable page budget exceeded; count is not complete')


def _read(args, fields):
    client = get_client()
    if client is None:
        return tool_error('Feishu client not available in this turn; no credential fallback')
    try:
        token, ids = _reference(args)
        paths = {'app_token': token, 'table_id': ids['table_id']}
        result = _collect(client, _FIELDS if fields else _RECORDS, paths, ids.get('view_id'), fields)
    except ValueError as exc:
        return tool_result(error=str(exc), complete=False)
    except (OSError, ImportError, RuntimeError):
        # SDK/network exceptions may embed credentials or business payloads.
        return tool_result(error='Bitable transport failed; no retry performed', complete=False)
    result.setdefault('identity', _identity(client))
    return tool_result(**result)


def read_fields(args, **kwargs):
    return _read(args, fields=True)


def read_records(args, **kwargs):
    return _read(args, fields=False)


_PARAMETERS = {'type': 'object', 'properties': {
    'base_url': {'type': 'string', 'description': 'Full authorized Feishu/Lark /base/ URL, including table and view when present.'},
    'table_id': {'type': 'string', 'description': 'Exact table ID if absent from the URL.'},
    'view_id': {'type': 'string', 'description': 'Exact optional view ID; must agree with the URL.'},
}, 'required': ['base_url'], 'additionalProperties': False}
for _name, _handler, _description in [
    ('feishu_bitable_read_fields', read_fields, 'Read all field definitions from an authorized Feishu Bitable /base/ URL in this DM. Uses the bound application identity; read-only, no user credential fallback.'),
    ('feishu_bitable_read_records', read_records, 'Read and count authorized Feishu Bitable /base/ records across bounded pages in this DM. Returns counts only, never company payloads. Uses the bound application identity; no writes, retry or credential fallback.'),
]:
    registry.register(name=_name, toolset='feishu_bitable',
                      schema={'name': _name, 'description': _description, 'parameters': _PARAMETERS},
                      handler=_handler, check_fn=_check_feishu, requires_env=[], is_async=False,
                      description=_description)
