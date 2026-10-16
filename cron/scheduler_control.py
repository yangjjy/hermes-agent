"""Opt-in per-job pinned dispatch control, before recurring advance.

Unmarked jobs retain the existing scheduler path. A control is a local reviewed
script, not a model, provider, second ticker, or global admission gate.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import signal
import sqlite3
import subprocess
import sys
import time

from cron.jobs import advance_next_runs, pause_job, update_job, mark_job_run
from cron.executions import create_execution, finish_execution

OUTCOMES = frozenset({'ALLOW', 'PAUSED', 'SKIPPED', 'REFUSED', 'CONTRACT_VIOLATION'})


def _pinned(home, relative, digest):
    root = Path(home).resolve() / 'scripts'
    path = root / relative
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('BLOCKING_DRIFT')
    if any(p.is_symlink() for p in [path, *path.parents] if p == root or root in p.parents):
        raise ValueError('BLOCKING_DRIFT')
    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise ValueError('BLOCKING_DRIFT')
    return path


def invoke(job, home, phase):
    spec = job['dispatch_control']
    handler = _pinned(home, spec['handler'], spec['handler_sha256'])
    manifest_path = _pinned(home, spec['manifest'], spec['manifest_sha256'])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    files = manifest['files']
    if not files or files.get(spec['handler']) != spec['handler_sha256']:
        raise ValueError('BLOCKING_DRIFT')
    for relative, digest in files.items():
        _pinned(home, relative, digest)
    bundle = handler.parent
    observed = {str(p.relative_to(Path(home).resolve() / 'scripts')) for p in bundle.rglob('*') if p.suffix in {'.py', '.pyc'}}
    if observed != set(files):
        raise ValueError('BLOCKING_DRIFT')
    if job.get('script') != spec['handler'] or job.get('no_agent') is not True or job.get('deliver') != 'local':
        raise ValueError('CONTRACT_VIOLATION')
    timeout = spec['timeout_seconds']
    if type(timeout) not in (int, float) or not 0 < timeout <= 60:
        raise ValueError('CONTRACT_VIOLATION')
    from tools.environments.local import build_subprocess_env
    env = build_subprocess_env(strip_launch_profile=True)
    env.update(HERMES_HOME=str(home), PYTHONDONTWRITEBYTECODE='1')
    # The owning scope is explicit; a launch-profile selector must not redirect it.
    env.pop('HERMES_PROFILE', None)
    fields = ('id', 'script', 'no_agent', 'deliver', 'schedule', 'next_run_at', '_scheduled_instant', 'dispatch_control', '_control_deadline')
    payload = {'job': {k: job[k] for k in fields if k in job}, 'home': str(home), 'native_source': str(Path(__file__).resolve().parents[1])}
    if phase == 'execute':
        timeout = min(timeout, job.get('_control_deadline', time.monotonic()) - time.monotonic())
        if timeout <= 0:
            raise ValueError('TIMEOUT')
    proc = subprocess.Popen([sys.executable, '-B', str(handler), phase],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            env=env, start_new_session=True)
    try:
        output, _ = proc.communicate(json.dumps(payload).encode(), timeout=min(5, timeout) if phase == 'prepare' else timeout)
    except subprocess.TimeoutExpired:
        from agent.deadline import kill_process_tree
        try:
            kill_process_tree(proc.pid)
        finally:
            try:
                if os.name != "nt":
                    os.killpg(proc.pid, getattr(signal, "SIGKILL", signal.SIGTERM))  # windows-footgun: ok — POSIX-only fallback after portable tree kill
                elif proc.poll() is None:
                    proc.kill()
            except ProcessLookupError:
                pass
            proc.communicate(timeout=1)
        raise ValueError('TIMEOUT') from None
    if proc.returncode or len(output) > 4096:
        raise ValueError('CONTRACT_VIOLATION')
    result = json.loads(output)
    if result.get('outcome') not in OUTCOMES or type(result.get('success')) is not bool:
        raise ValueError('CONTRACT_VIOLATION')
    return {key: result[key] for key in ('outcome', 'success')}


def gate(job, home):
    if 'dispatch_control' not in job:
        return None
    receipt = None
    try:
        receipt = create_execution(job['id'], source='dispatch_control', scheduled_instant=None)
        started = time.monotonic()
        verdict = invoke(job, home, 'prepare')
        if verdict['outcome'] == 'ALLOW':
            job['_control_deadline'] = started + job['dispatch_control']['timeout_seconds']
        finish_execution(receipt['id'], success=True, error='dispatch:' + verdict['outcome'])
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, ImportError, sqlite3.Error, subprocess.SubprocessError):
        pause_job(job['id'], reason='dispatch_control:BLOCKING_DRIFT_OR_CONTROL_UNAVAILABLE')
        if receipt:
            finish_execution(receipt['id'], success=False, error='dispatch:CONTRACT_VIOLATION')
        return {'outcome': 'CONTRACT_VIOLATION', 'success': False}
    if verdict['outcome'] in {'CONTRACT_VIOLATION', 'REFUSED', 'PAUSED'}:
        pause_job(job['id'], reason='dispatch_control:' + verdict['outcome'])
    return verdict


def admit_due(jobs, home):
    allowed = []
    for job in jobs:
        verdict = gate(job, home)
        if verdict is None or verdict['outcome'] == 'ALLOW':
            allowed.append(job)
        elif verdict['outcome'] == 'SKIPPED':
            try:
                advance_next_runs([job['id']])
                update_job(job['id'], {'pending_slot': None})
            except OSError:
                pause_job(job['id'], reason='dispatch_control:AUDIT_UNAVAILABLE')
    return allowed


def run_admitted(job, home):
    """After the existing native fire claim, revalidate and execute the same pin.

    Refusal here restores the occurrence and pauses, without calling mark_job_run:
    an unexecuted occurrence is never reported as a failed business observation.
    """
    try:
        verdict = invoke(job, home, 'execute')
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, ImportError, sqlite3.Error, subprocess.SubprocessError):
        verdict = {'outcome': 'CONTRACT_VIOLATION', 'success': False}
    if verdict['outcome'] == 'SKIPPED':
        update_job(job['id'], {'fire_claim': None, 'pending_slot': None})
        finish_execution(job['execution_id'], success=True)
        return True
    if verdict['outcome'] != 'ALLOW':
        pause_job(job['id'], reason='dispatch_control:' + verdict['outcome'])
        slot = job.get('_scheduled_instant')
        fields = {'fire_claim': None, 'pending_slot': None}
        if slot:
            fields['next_run_at'] = slot
        update_job(job['id'], fields)
        finish_execution(job['execution_id'], success=False, error='not executed:' + verdict['outcome'])
        return False
    success = verdict['success']
    mark_job_run(job['id'], success, None if success else 'CONTROLLED_OBSERVATION_FAILURE')
    finish_execution(job['execution_id'], success=success, error=None if success else 'CONTROLLED_OBSERVATION_FAILURE')
    return success


def next_run(job, now):
    """Marked cron jobs bind their own IANA timezone; never change profile TZ."""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from croniter import croniter
    if job['schedule']['kind'] != 'cron':
        raise ValueError('CONTRACT_VIOLATION')
    moment = datetime.fromisoformat(now).astimezone(ZoneInfo(job['dispatch_control']['timezone']))
    return croniter(job['schedule']['expr'], moment).get_next(datetime).isoformat()


def refuse_direct(job):
    pause_job(job['id'], reason='dispatch_control:UNAUTHORIZED_EXECUTION')
    receipt = create_execution(job['id'], source='dispatch_control', scheduled_instant=None)
    finish_execution(receipt['id'], success=False, error='dispatch:REFUSED_DIRECT')
    return False
