# async-fsm

This is a helper class for building state machines which need to be
drivable by asynchronous events, launch some side effects in parallel when they
transition from one state to another, and optionally transition to
another state immediately once all their (asynchronous) side effects
have completed. It is not nearly as feature-complete, actively
maintained, or practical as a serious Python state machine library
like [transitions](https://github.com/tyarkoni/transitions). This
repository also is intended to act as some kind of approximation
of my understanding of how to set up a Python project with some
niceties like setup/automated testing/coverage reports.

## Project setup

The state machine uses `asyncio` (and the Python 3.5 `async
def`/`await` syntax) so the tests need the `pytest-asyncio` extension
to `pytest`, which should be pulled in automatically if you run the
bash thingy below. I'm also using `tox` to run `pytest` which can
easily be adapted to automatically run a test suite on multiple Python
versions, but it's not being used for this now because 3.5 is the only
version where the code will work. Doing installation the way described
below means that all the dependencies for the library and tests are
installed into a virtualenv but still links in the current directory
so you don't have to run `pip install` again.  You _do_ need
`eventlet` installed to run coverage (I think) because the `eventlet`
concurrency model is the only one that worked for me.

## Running the test suite

```bash
git clone git://github.com/csboling/async-fsm
cd async-fsm
pip install virtualenv
virtualenv .
pip install -r requirements.txt
tox
```

## Using the library

You can inherit from StateMachine and define state and input enums if
you want, but the easiest way to specify a state machine is to use a
YAML/JSON/whatever file to load a table definition dictionary with the
class method `from_table`. This is
demonstrated with YAML syntax [here](async_fsm/tests/test_fsm.yaml). For
each state listed under `table` you may list one or more inputs, then
give a sequence of states the machine should transition to once all
registered side effects are completed.

Once you have a `StateMachine` instance (say `machine`) you can
register side effects that you wish to fire when a state transition
occurs as `asyncio` coroutines using the `machine.on` decorator:

``` python
@machine.on('init', 'active')
async def behave():
    await asyncio.sleep(1)
```

and trigger state transitions using `machine.input` or
`machine.input_sequence`.
