from collections import defaultdict
from enum import Enum
from functools import reduce
from itertools import starmap
import sys

import eventlet
from promise import Promise


class Message:
    def __init__(self, type, data):
        self.type = type
        self.data = data


class InvalidInput(Exception):
    pass


class StateMachine:
    def __init__(self, State, initial):
        self.state = State(initial)
        self._transition_table = defaultdict(list)
        self.input_queue = []
        self.transition_pool = eventlet.GreenPool()

    def on(self, old, new):
        '''Should only be used to decorate free functions. If you must use a
        self argument, pass it in as a member of the "data" dictionary when you
        call input().
        '''
        def decorate(f):
            self._transition_table[(old, new)].append(f)
            return f

        return decorate

    def input(self, signal, data=None) -> Promise:
        promise = getattr(self, self.state.name)(Message(signal, data))
        if promise is None:
            raise InvalidInput(
                '{} is not a valid input for state {}'.format(
                    signal,
                    self.state
                )
            )
        self.input_queue.append(promise)
        return promise

    def transition(self, state, data=None) -> Promise:
        def promise_fn(resolve, reject):
            def complete_transition():
                try:
                    self.transition_pool.waitall()
                except Exception as e:
                    reject(e)
                else:
                    print('{} -> {}'.format(self.state, state))
                    self.state = state
                    resolve(data)

            for listener in self._transition_table[(self.state.name, state.name)]:
                self.transition_pool.spawn(listener)
            eventlet.spawn(complete_transition)

        return Promise(promise_fn)

    def state_sequence(self, states, data=None) -> Promise:
        def next_trans(state, data):
            ret = self.transition(state, data)
            return ret

        def reducer(promise, state):
            return promise.then(
                lambda data: next_trans(state, data)
            )

        return reduce(
            lambda promise, state: promise.then(
                lambda data: self.transition(state, data)
            ),
            states,
            Promise.resolve(data)
        )

    def input_sequence(self, actions, data=None) -> Promise:
        return reduce(
            lambda prev, action: prev.then(
                lambda data: self.input(action, data)
            ),
            actions,
            Promise.resolve(data)
        )


def from_table(states, inputs, table):
    class Machine(StateMachine):
        State = Enum('State', ' '.join(states))
        Input = Enum('Input', ' '.join(inputs))

        def __init__(self):
            super().__init__(self.State, 1)

    def attach_behavior(state, transitions):
        def behavior(self, msg):
            try:
                transition = transitions[msg.type.name]
            except KeyError:
                return None
            else:
                return self.state_sequence(
                    getattr(self.State, state) for state in transition
                )
        setattr(Machine, state, behavior)

    list(starmap(attach_behavior, table.items()))
    return Machine
