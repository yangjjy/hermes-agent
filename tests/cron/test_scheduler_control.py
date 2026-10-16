"""Pinned job-scoped control decisions; no network or operator profile."""
import hashlib,json
from pathlib import Path
from unittest.mock import patch
import pytest
from cron import jobs
from cron import scheduler_control as control

def stage(tmp_path,outcome='ALLOW'):
    root=tmp_path/'scripts';root.mkdir(exist_ok=True)
    handler=root/'control.py';handler.write_text('import json,sys\np=json.load(sys.stdin)\nprint(json.dumps({"outcome":'+repr(outcome)+',"condition":"HEALTHY","success":True}))\n')
    manifest=root/'manifest.json';manifest.write_text(json.dumps({'files':{'control.py':hashlib.sha256(handler.read_bytes()).hexdigest()}}))
    job=dict(id='owned',script='control.py',enabled=True,state='scheduled',no_agent=True,deliver='local',schedule=dict(kind='cron',expr='0 * * * *'),next_run_at=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).replace(second=0,microsecond=0).isoformat(),failure_streak=0,dispatch_control=dict(handler='control.py',handler_sha256=hashlib.sha256(handler.read_bytes()).hexdigest(),manifest='manifest.json',manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),timeout_seconds=5,timezone="Asia/Shanghai"))
    jobs.save_jobs([job]);return job

def test_unmarked_job_never_inherits_policy(tmp_path):
    with patch.object(control,'invoke',side_effect=AssertionError('must not call')):
        assert control.gate(dict(id='unrelated'),tmp_path) is None

@pytest.mark.parametrize('outcome',['PAUSED','REFUSED','CONTRACT_VIOLATION'])
def test_refusal_keeps_slot_and_failure_streak(tmp_path,monkeypatch,outcome):
    monkeypatch.setenv('HERMES_HOME',str(tmp_path));job=stage(tmp_path,outcome);slot=job['next_run_at']
    assert control.gate(job,tmp_path)['outcome']==outcome
    stored=jobs.get_job(job['id']);assert stored['next_run_at']==slot;assert stored['failure_streak']==0


def test_bad_handler_pin_zero_invocations_and_individual_pause(tmp_path,monkeypatch):
    monkeypatch.setenv('HERMES_HOME',str(tmp_path));job=stage(tmp_path);job['dispatch_control']['handler_sha256']='0'*64
    with patch('subprocess.Popen',side_effect=AssertionError('no transport')):
        assert control.gate(job,tmp_path)['outcome']=='CONTRACT_VIOLATION'
    assert jobs.get_job(job['id'])['enabled'] is False


def test_gate_filters_before_recurring_advance(tmp_path,monkeypatch):
    monkeypatch.setenv('HERMES_HOME',str(tmp_path));allowed=stage(tmp_path)
    refused=dict(allowed,id='refused');legacy=dict(id='legacy')
    with patch.object(control,'gate',side_effect=lambda job,home:None if job is legacy else {'outcome':'ALLOW' if job is allowed else 'REFUSED'}):
        assert control.admit_due([allowed,refused,legacy],tmp_path)==[allowed,legacy]


def test_explicit_skip_advances_without_run_or_failure(tmp_path,monkeypatch):
    monkeypatch.setenv('HERMES_HOME',str(tmp_path));job=stage(tmp_path,'SKIPPED')
    with patch.object(control,'advance_next_runs') as advance:
        assert control.admit_due([job],tmp_path)==[];advance.assert_called_once_with([job['id']])
    assert jobs.get_job(job['id'])['failure_streak']==0


def test_pause_outcome_materializes_native_pause(tmp_path,monkeypatch):
    monkeypatch.setenv('HERMES_HOME',str(tmp_path));job=stage(tmp_path,'PAUSED')
    control.gate(job,tmp_path)
    assert jobs.get_job(job['id'])['enabled'] is False


def test_skip_storage_error_does_not_block_unrelated_job(tmp_path,monkeypatch):
    monkeypatch.setenv('HERMES_HOME',str(tmp_path));job=stage(tmp_path,'SKIPPED');legacy={'id':'legacy'}
    with patch.object(control,'advance_next_runs',side_effect=OSError('synthetic')):
        assert control.admit_due([job,legacy],tmp_path)==[legacy]
    assert jobs.get_job(job['id'])['enabled'] is False


def test_actual_tick_runs_once_and_retains_unmarked_behavior(tmp_path,monkeypatch):
    monkeypatch.setenv('HERMES_HOME',str(tmp_path));job=stage(tmp_path)
    handler=tmp_path/'scripts/control.py'
    handler.write_text('import json,sys\nfrom pathlib import Path\np=json.load(sys.stdin)\nif sys.argv[1]=="execute":\n with (Path(p["home"])/"observations").open("a") as f:f.write("one\\n")\nprint(json.dumps({"outcome":"ALLOW","success":True}))\n')
    manifest=tmp_path/'scripts/manifest.json';manifest.write_text(json.dumps({'files':{'control.py':hashlib.sha256(handler.read_bytes()).hexdigest()}}))
    job['dispatch_control'].update(handler_sha256=hashlib.sha256(handler.read_bytes()).hexdigest(),manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest())
    jobs.save_jobs([job])
    from cron import scheduler
    with patch.object(scheduler,'_should_yield_tick_to_fresh_gateway',return_value=None),patch.object(scheduler,'_maybe_reap_dead_owners'),patch.object(scheduler,'_maybe_run_worktree_maintenance'),patch.object(scheduler,'_sweep_mcp_orphans'),patch('cron.bot_chat_delivery.drain'):
        scheduler.tick(verbose=False,sync=True)
        scheduler.tick(verbose=False,sync=True)
    assert (tmp_path/'observations').read_text()=='one\n'
    assert jobs.get_job(job['id'])['failure_streak']==0


def test_job_timezone_independent_of_profile(tmp_path):
    job=stage(tmp_path)
    assert control.next_run(job,'2026-10-15T23:30:00+00:00')=='2026-10-16T08:00:00+08:00'


def test_claim_keeps_job_timezone_and_worker_skip_has_no_failure(tmp_path,monkeypatch):
    import time
    from cron.executions import create_execution
    monkeypatch.setenv('HERMES_HOME',str(tmp_path));job=stage(tmp_path,'SKIPPED')
    # The pre-gate's ALLOW decision was already reviewed, but the queued D run
    # crosses its explicit skip boundary before it reaches the worker.
    jobs.advance_next_runs([job['id']]);claimed=jobs.claim_job_for_fire(job['id'],return_job=True)
    assert claimed and jobs.get_job(job['id'])['next_run_at'].endswith('+08:00')
    claimed.update(_control_deadline=time.monotonic()+5,execution_id=create_execution(job['id'],source='builtin')['id'])
    assert control.run_admitted(claimed,tmp_path) is True
    current=jobs.get_job(job['id']);assert current['failure_streak']==0;assert current['enabled'] is True
    assert current['next_run_at'].endswith('+08:00')



def test_profile_home_alias_normalized_before_inventory(tmp_path,monkeypatch):
    monkeypatch.setenv('HERMES_HOME',str(tmp_path));job=stage(tmp_path)
    alias=tmp_path/'alias';alias.symlink_to(tmp_path,target_is_directory=True)
    assert control.invoke(job,alias,'prepare')['outcome']=='ALLOW'


@pytest.mark.parametrize('malformed',['result_list','result_null','files_list'])
def test_malformed_protocol_pauses_only_owned_and_preserves_other_jobs(tmp_path,monkeypatch,malformed):
    monkeypatch.setenv('HERMES_HOME',str(tmp_path));job=stage(tmp_path)
    handler=tmp_path/'scripts/control.py';manifest=tmp_path/'scripts/manifest.json'
    if malformed.startswith('result_'):
        handler.write_text('print('+repr('[]' if malformed=='result_list' else 'null')+')\n',encoding='utf-8')
    files=['x'] if malformed=='files_list' else {'control.py':hashlib.sha256(handler.read_bytes()).hexdigest()}
    manifest.write_text(json.dumps({'files':files}),encoding='utf-8')
    job['dispatch_control'].update(handler_sha256=hashlib.sha256(handler.read_bytes()).hexdigest(),manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest())
    jobs.save_jobs([job]);slot=job['next_run_at']
    assert control.admit_due([job,{'id':'unrelated'}],tmp_path)==[{'id':'unrelated'}]
    current=jobs.get_job(job['id'])
    assert current['enabled'] is False and current['next_run_at']==slot and current['failure_streak']==0


def test_worker_interruption_does_not_claim_inflight_action_was_undone(tmp_path,monkeypatch):
    from cron.executions import create_execution,get_execution
    monkeypatch.setenv('HERMES_HOME',str(tmp_path));job=stage(tmp_path)
    receipt=create_execution(job['id'],source='builtin');job['execution_id']=receipt['id']
    with patch.object(control,'invoke',side_effect=ValueError('TIMEOUT')):
        assert control.run_admitted(job,tmp_path) is False
    assert 'not executed' not in get_execution(receipt['id'])['error']
    assert jobs.get_job(job['id'])['enabled'] is False
