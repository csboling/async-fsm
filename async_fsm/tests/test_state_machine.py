import os
from unittest import mock

import eventlet
from promise import Promise
import yaml

import pytest

from servicehost.state_machine import from_table, InvalidInput


LOCALROOT = os.path.abspath(os.path.dirname(__file__))


@pytest.fixture
def machine():
    with open(os.path.join(LOCALROOT, 'test_fsm.yaml')) as f:
        table = yaml.load(f)
        Machine = from_table(**table)

    return Machine()


@pytest.fixture
def busy():
    busy = mock.create_autospec(
        lambda was, now: print('busywork: {} -> {}'.format(was, now))
    )
    return busy


@pytest.fixture
def long_busy():
    long_busy = mock.create_autospec(
        lambda was, now: eventlet.sleep(1)
    )
    return long_busy


@pytest.fixture
def behaviors(machine, busy, long_busy):
    class StateMachineClient:
        @machine.on('idle', 'working')
        def do_start():
            busy('idle', 'working')

        @machine.on('working', 'idle')
        def do_cancel():
            busy('working', 'idle')

        @machine.on('working', 'done')
        def do_refresh():
            long_busy('working', 'done')

        @machine.on('done', 'idle')
        def do_reset():
            busy('done', 'idle')
    return StateMachineClient()


class TestStateMachine:
    def test_single_transition(self, machine, busy, long_busy, behaviors):
        machine.input(machine.Input.start, {'input': 'data'}).get()
        busy.assert_called_once_with('idle', 'working')

    def test_input_sequence(self, machine, busy, behaviors):
        machine.input_sequence(
            [
                machine.Input.start,
                machine.Input.cancel,
            ],
            {'input': 'data'}
        ).get()

        busy.assert_has_calls([
            mock.call('idle', 'working'),
            mock.call('working', 'idle'),
        ])

    def test_transition_sequence(self, machine, busy, long_busy, behaviors):
        machine.input(
            machine.Input.start, {'input': 'data'}
        ).then(
            lambda data: machine.input(
                machine.Input.refresh, data
            )
        ).get()

        busy.assert_has_calls([
            mock.call('idle', 'working'),
            mock.call('done', 'idle'),
        ])

        long_busy.assert_has_calls([
            mock.call('working', 'done'),
        ])

    def test_complex_sequence(self, machine, busy, long_busy, behaviors):
        machine.input_sequence(
            [
                machine.Input.start,
                machine.Input.cancel,
                machine.Input.start,
                machine.Input.refresh,
                machine.Input.start,
                machine.Input.complete,
                machine.Input.reset,
            ],
            {'input': 'data'}
        ).get()

        busy.assert_has_calls([
            mock.call('idle', 'working'),
            mock.call('working', 'idle'),
            mock.call('idle', 'working'),
            mock.call('done', 'idle'),
            mock.call('idle', 'working'),
            mock.call('done', 'idle'),
        ])

        long_busy.assert_has_calls([
            mock.call('working', 'done'),
            mock.call('working', 'done'),
        ])

    def test_bad_input(self, machine, busy, long_busy, behaviors):
        with pytest.raises(InvalidInput):
            machine.input(machine.Input.refresh, {})

    def test_mixed_signals(self, machine, busy, long_busy, behaviors):
        seq_one = machine.input_sequence(
            [
                machine.Input.start,
                machine.Input.complete,
            ]
        )
        seq_two = machine.input(machine.Input.start)

        Promise.all([seq_two, seq_one]).wait()
        busy.assert_any_call('idle', 'working')
        long_busy.assert_called_with('working', 'done')
