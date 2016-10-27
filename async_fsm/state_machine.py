import asyncio
from collections import defaultdict
from enum import Enum
from functools import reduce
from itertools import starmap

from promise import Promise

from async_fsm.exceptions import InvalidInput


class Message:
    def __init__(self, type, data):
        self.type = type
        self.data = data


class StateMachine:
    def __init__(self, State, initial):
        self.state = State(initial)
        self._transition_table = defaultdict(list)

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
        return promise

    def transition(self, state, data=None) -> Promise:
        async def do_side_effects():
            await asyncio.wait(map(
                lambda f: asyncio.ensure_future(f()),
                self._transition_table[(self.state.name, state.name)]
            ))
            self.state = state
        return Promise.promisify(asyncio.ensure_future(do_side_effects()))

    def state_sequence(self, states, data=None) -> Promise:
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

    @classmethod
    def from_table(cls, states, inputs, table):
        class Machine(cls):
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
