import importlib.util
from pathlib import Path
import sys
import threading
import types
import unittest
from unittest.mock import Mock, patch


class ReporterSupervisorTests(unittest.TestCase):
    def test_turn_consumer_is_daemon_and_failure_is_observable(self):
        module=self.module(); seen=[]
        active=Mock()
        def run():
            seen.append(threading.current_thread().daemon)
            raise ValueError('SDK failed')
        active.run.side_effect=run
        with self.assertRaisesRegex(ValueError,'SDK failed'): module.consume_turn(active).result(timeout=1)
        self.assertEqual(seen,[True])

    def test_stop_reasons_are_distinct_and_cutoff_has_priority(self):
        m=self.module()
        self.assertEqual(m.stop_reason(False,1000,0,601),'turn_timeout')
        self.assertEqual(m.stop_reason(True,1000,0,601),'operator_stop')
        self.assertEqual(m.stop_reason(True,1000,0,1000),'shift_cutoff')
        self.assertEqual(m.stop_reason(False,1000,0,500),'')
        self.assertEqual(m.final_shift_status('turn_timeout','completed'),'failed')
        self.assertEqual(m.final_shift_status('operator_stop','failed'),'paused')
        self.assertEqual(m.final_shift_status('shift_cutoff','failed'),'completed')

    def module(self):
        path=Path(__file__).parents[1]/'infra/codex-reporter/reporter_supervisor.py'
        spec=importlib.util.spec_from_file_location('pilot_supervisor_test',path)
        module=importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules,local_probe=types.SimpleNamespace(CONTROL=Path('/tmp'))):
            spec.loader.exec_module(module)
        return module

    def test_kills_owned_client_without_a_turn_handle(self):
        module=self.module(); release=threading.Event()
        proc=Mock();proc.poll.return_value=None
        codex=Mock();codex._client._proc=proc
        def hung_close():
            codex._client._proc=None
            release.wait(5)
        codex.close.side_effect=hung_close
        try:
            module.stop_runtime(codex)
            proc.kill.assert_called_once();proc.wait.assert_called_once_with(timeout=1)
        finally: release.set()

    def test_hung_interrupt_does_not_block_client_close(self):
        module=self.module(); release=threading.Event()
        active=Mock();active.interrupt.side_effect=lambda:release.wait(5)
        codex=Mock();codex._client._proc=None
        try:
            module.stop_runtime(codex,active)
            codex.close.assert_called_once()
        finally: release.set()

    def test_exception_context_exit_uses_bounded_close(self):
        module=self.module(); release=threading.Event()
        proc=Mock();proc.poll.return_value=None
        codex=Mock();codex._client._proc=proc
        def hung_close():
            codex._client._proc=None
            release.wait(5)
        codex.close.side_effect=hung_close
        module.probe.client=Mock(return_value=codex)
        try:
            with self.assertRaisesRegex(RuntimeError,'heartbeat failed'):
                with module.bounded_client():
                    raise RuntimeError('heartbeat failed')
            proc.kill.assert_called_once()
        finally: release.set()
