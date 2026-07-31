# From beginner to pro — a full curriculum for this codebase

This is the expanded version of the tier list from our last conversation —
every single concept, explained from scratch, with a real example pulled
directly from this repository (never a made-up snippet), plus *why it
matters for debugging*. Work through it roughly in order — later tiers
build on earlier ones.

Read this alongside the code, not instead of it. Every example below names
the exact file it comes from — open it, find the line, look around it.

---

## Tier 0 — Python fundamentals

### Classes, objects, and `self`

A **class** is a blueprint; an **object** (or *instance*) is one real thing
built from that blueprint. `self` is how a method refers to "the specific
object I was called on."

```python
class Dog:
    def __init__(self, name):
        self.name = name          # store data ON this specific object

    def bark(self):
        return f"{self.name} says woof"

rex = Dog("Rex")        # rex is an OBJECT, an instance of the Dog CLASS
rex.bark()                # Python secretly calls Dog.bark(rex)
```

**In this repo:** `execution/domain/command.py`'s `Command` class. Every
`self._status = ...` line is storing data on one specific command — the
command for *this* order, not some abstract idea of a command.

**Why it matters for debugging:** if a value looks wrong, the first
question is always "wrong on *which object*?" — two `Command` instances
never share state unless you deliberately pass the same object around.

### Type hints

Annotations telling you (and tools like `mypy`) what type a value should
be. They don't change how Python runs — they're a promise, checked
separately by a tool, not enforced at runtime by the language itself.

```python
def add(a: int, b: int) -> int:
    return a + b
```

`int` = the type of `a`. `-> int` = the type it returns. `X | None` means
"either an `X`, or `None`."

**In this repo:** `def get_current(self, site_id: SiteId) -> EnergyState | None:`
(`telemetry/application/state_manager.py`) — reads as "give me a `SiteId`,
you'll get back an `EnergyState`, or nothing if there isn't one yet."

**Why it matters for debugging:** `mypy --strict` (part of this project's
dev tooling) catches an entire category of bugs — passing the wrong type,
forgetting a function can return `None` — *before* you ever run the code.
Reading the type hints on a function tells you what it expects without
reading its whole body.

### Exceptions

Python's way of saying "something went wrong, stop normal execution, and
let something further up decide what to do about it."

```python
try:
    result = 10 / 0
except ZeroDivisionError as e:
    print(f"that failed: {e}")
```

**In this repo:** the whole exception family in `shared_kernel/exceptions.py`
— `FailSafeTriggered`, `PolicyViolation`, etc., all inheriting from one
`DomainError`. Look at `safety/application/safety_validator.py`:
```python
except Exception as exc:
    raise FailSafeTriggered(f"safety validator internal error: {exc}") from exc
```
Catches *any* unexpected error and converts it into the one exception type
that means "refuse the command" — nothing slips through as a silent bug.

**Why it matters for debugging:** when a test fails with a traceback, read
it from the **bottom up** — the last line is the actual exception and
message; everything above it is the chain of function calls that led there.

### Decorators

A decorator wraps a function or class with extra behavior, written with
`@` above the definition.

```python
def shout(func):
    def wrapper(*args):
        return func(*args).upper()
    return wrapper

@shout
def greet(name):
    return f"hello {name}"

greet("sam")   # "HELLO SAM" — shout() silently wrapped it
```

**In this repo:** `@dataclass`, `@property`, `@classmethod`,
`@staticmethod`, `@field_validator` appear constantly. You don't need to
know how to *write* a decorator to use one — just recognize that
`@dataclass` above a class means "generate `__init__`, `__eq__`, etc. for
me automatically, based on the fields I list."

**Why it matters for debugging:** if a class looks like it has no
`__init__` but you can still do `Policy(policy_id=..., site_id=...)`,
that's `@dataclass` generating it invisibly — check for the decorator
before assuming something's missing.

### Context managers (`with` statements)

A pattern that guarantees setup *and* cleanup happen, even if an error
occurs in between.

```python
with open("file.txt") as f:
    data = f.read()
# file is automatically closed here, even if read() raised an error
```

**In this repo:** `execution/infrastructure/postgres_audit_log.py`:
```python
with self._engine.begin() as connection:
    connection.execute(insert(audit_log_table).values(...))
```
Opens a database transaction, runs the insert, and commits (or rolls back
on error) automatically when the `with` block ends.

**Why it matters for debugging:** if you ever see a database connection
"left open" or a resource leak, check whether the code used a `with` block
or manually called `.close()` (and maybe forgot to, on an error path).

---

## Tier 1 — the patterns this specific project leans on hardest

### `@dataclass(frozen=True, slots=True)`

`@dataclass` auto-generates `__init__`, `__repr__`, `__eq__` from a list of
fields. `frozen=True` makes it **immutable** — you can't change a field
after construction. `slots=True` means the object can't have any attribute
that isn't explicitly declared (saves memory, catches typos).

```python
@dataclass(frozen=True, slots=True)
class Point:
    x: float
    y: float

p = Point(1.0, 2.0)
p.x = 5.0     # raises FrozenInstanceError — frozen means frozen
```

**In this repo:** nearly every value object — `shared_kernel/ids.py`,
`safety/domain/policy.py`, `safety/domain/command_intent.py`. This is *why*
`Command.risk_assessment` can be trusted once set — nothing downstream can
sneakily mutate it later.

**Why it matters for debugging:** if you're trying to "fix" a bug by
mutating an object and Python throws `FrozenInstanceError`, that's not a
bug to work around — it's the design telling you: build a *new* object
instead (see `dataclasses.replace()`, used in
`decision/application/rule_based_optimiser.py`'s `_make_conservative()`).

### `typing.Protocol` — the most important one in this whole codebase

A `Protocol` declares a **shape** (which methods something must have) —
without requiring inheritance. Any class with matching methods
automatically satisfies it. This is called **structural typing** ("if it
walks like a duck and quacks like a duck").

```python
from typing import Protocol

class CanBark(Protocol):
    def bark(self) -> str: ...

class Dog:
    def bark(self) -> str:
        return "woof"

def make_it_bark(thing: CanBark) -> str:
    return thing.bark()

make_it_bark(Dog())   # works! Dog never mentioned CanBark, doesn't need to.
```

**In this repo:** `execution/domain/ports.py::HardwareInterface`,
`telemetry/domain/ports.py::StateStore`, `forecast/domain/ports.py::ForecastModel`
— all Protocols. `SimulatedHardwareInterface` (in `platform/`) never writes
`class SimulatedHardwareInterface(HardwareInterface):` — it just happens to
have a matching `send()` method, and that's enough.

**Why it matters for debugging:** if you're hunting for "which class
actually implements this," `Protocol`s won't show up in a normal
"find all subclasses" search — you have to search for **matching method
names** instead, since there's no inheritance link to follow. This is also
*exactly* the mechanism behind "Way 2" from `ONBOARDING.md`'s data-flow
explanation.

### Pydantic's `BaseModel`

Like `@dataclass`, but adds **runtime validation** and **JSON
serialization**. A `@dataclass` trusts you gave it the right types; a
Pydantic model actually checks, and can convert itself to/from JSON.

```python
from pydantic import BaseModel

class User(BaseModel):
    name: str
    age: int

User(name="Sam", age="30")     # works — Pydantic coerces "30" -> 30
User(name="Sam", age="thirty")  # raises ValidationError
```

**In this repo:** `telemetry/domain/energy_state.py`, every file in
`api/schemas/`. This is why a malformed API request gets a clean 422 error
instead of a crash three functions deep.

**Why it matters for debugging:** `@dataclass` and `BaseModel` *look*
similar but fail differently — a `ValidationError` traceback (Pydantic)
looks very different from a plain `TypeError` (`@dataclass`). Know which
one you're looking at.

### Enums

Covered in an earlier conversation already — a fixed, closed set of named
values (`RiskLevel`, `GridStatus`). Revisit `shared_kernel/enums.py` if
this still feels shaky; it doesn't get more complex than what's there.

---

## Tier 2 — the API stack

### FastAPI

A Python web framework built specifically around type hints and Pydantic —
you declare what a request/response looks like with types, and FastAPI
handles validation, docs generation, and routing.

```python
from fastapi import FastAPI
app = FastAPI()

@app.get("/hello/{name}")
def hello(name: str) -> dict:
    return {"message": f"hello {name}"}
```
Visiting `/hello/sam` returns `{"message": "hello sam"}` — and `/docs`
automatically shows this endpoint, generated from the type hints alone.

**`Depends()`** is FastAPI's dependency injection — a way to say "before
running this route, go get me this other thing first."

**In this repo:** `api/dependencies.py::get_composition` — every router
function takes `composition: SystemComposition = Depends(get_composition)`,
which is how a route gets access to the one shared `SystemComposition`
without a global variable.

**Why it matters for debugging:** a 422 error means Pydantic validation
failed on the request — read the JSON error body, it names the exact field.
A 500 means something crashed *inside* your route code — check
`api/errors.py`'s exception handlers first to see how it's supposed to be
caught.

### Uvicorn

The actual program that runs a FastAPI app — FastAPI describes *what* to
do with a request; Uvicorn is the server that accepts real network
connections and hands them to FastAPI.

**In this repo:** `scripts/run_api.py` — three lines, all Uvicorn. If the
API won't start at all (not a 500, but nothing responds), the error is in
Uvicorn's own startup log, not inside your route code.

### HTTP/REST basics

If these aren't solid yet, get them before FastAPI, not after:
- **GET** = read, no side effects. **POST** = do something / create something.
- **Status codes**: 200 = OK, 404 = not found, 401 = not authenticated,
  422 = your request was malformed, 500 = the server crashed.
- **JSON** = the text format almost every request/response body uses here.

---

## Tier 3 — testing

### pytest fundamentals

A **fixture** is a reusable setup function tests can ask for by name.

```python
import pytest

@pytest.fixture
def three():
    return 3

def test_addition(three):        # pytest sees the parameter name "three"
    assert three + 2 == 5           # and automatically calls the fixture
```

`scope="module"` / `scope="session"` controls how often a fixture gets
rebuilt — `session` means "build it once for the whole test run," useful
when setup is slow (like building a `SystemComposition`, which trains
real ML models at construction).

**In this repo:** `tests/unit/api/conftest.py`'s `client` fixture
(`scope="session"`) — built once, reused by every API test in that run.

**Why it matters for debugging:** run a single failing test in isolation
with `pytest path/to/test_file.py::test_name -q`, not the whole suite —
much faster feedback loop while you're actually debugging.

### `conftest.py`

A specially-named file pytest automatically discovers — any fixture
defined here is available to every test in that folder (and subfolders)
without an explicit import.

**Why it matters for debugging:** if a test uses a fixture you can't find
anywhere in its own file, check `conftest.py` in the same directory (or a
parent directory) before assuming it's missing.

### Fakes instead of mocks

A **mock** is a fake object that just records "was I called, with what
arguments" — it doesn't actually *do* anything. A **fake** is a real,
working, simplified implementation of the same interface.

```python
# a mock: records calls, does nothing real
from unittest.mock import Mock
fake_store = Mock()
fake_store.get("site-1")   # returns a Mock object, not real data

# a fake: actually works, just simplified
class InMemoryStateStore:
    def __init__(self): self._states = {}
    def get(self, site_id): return self._states.get(str(site_id))
    def set(self, state): self._states[str(state.site_id)] = state
```

**In this repo:** almost every `InMemoryX` class (`InMemoryStateStore`,
`InMemoryAuditLog`, `InMemoryPolicyRepository`) is a *fake*, not a mock —
this project barely uses `unittest.mock` at all.

**Why it matters for debugging:** a test using a fake can catch real bugs
in how your code *uses* a `StateStore` (wrong method name, wrong argument
order) — a bare mock often can't, since it accepts anything and returns
nothing meaningful.

---

## Tier 4 — data & infrastructure

### Redis

An in-memory key-value store — think of it as a giant, very fast
dictionary that lives outside your Python process (so multiple processes
can share it) and optionally persists to disk.

```python
import redis
r = redis.Redis()
r.set("key", "value")
r.get("key")   # b"value"
```

**In this repo:** `telemetry/infrastructure/redis_state_store.py` — the
*entire* class is just `.get()`/`.set()` wrapping a Redis client, plus
turning `EnergyState` into/from JSON.

### SQLAlchemy Core (not the full ORM)

A Python library for talking to SQL databases. **Core** (what this project
uses) means writing explicit `Table`/`insert()`/`select()` statements —
more verbose than the full ORM (which maps whole Python classes to
database rows automatically), but much easier to read line-by-line without
knowing SQLAlchemy's deeper "Session" machinery.

```python
from sqlalchemy import Table, Column, String, MetaData, insert

metadata = MetaData()
users = Table("users", metadata, Column("name", String))

with engine.begin() as conn:
    conn.execute(insert(users).values(name="Sam"))
```

**In this repo:** `execution/infrastructure/postgres_audit_log.py` — read
it now that you know this; it should read almost like plain English.

### Basic SQL

Just enough: `SELECT * FROM table WHERE column = value` reads rows;
`INSERT INTO table VALUES (...)` adds one. A **primary key** is a column
guaranteed unique per row (here, `event_id`).

### MLflow

A tool for **experiment tracking**: every time you train/register a model,
it logs the parameters, metrics, and a version number somewhere you can
look up later, independent of your running process.

**In this repo:** `forecast/infrastructure/model_registry.py`'s
`MLflowModelRegistry` — `mlflow.start_run()` opens one tracked "experiment
run," `mlflow.log_metric(...)` records a number against it.

---

## Tier 5 — ML basics

### scikit-learn's fit/predict shape

Nearly every scikit-learn model follows the same two-method interface:
`.fit(data)` trains it, `.predict(new_data)` gives predictions.

```python
from sklearn.ensemble import IsolationForest
model = IsolationForest()
model.fit(training_data)
model.predict(new_data)   # -1 = anomaly, 1 = normal
```

**In this repo:** `anomaly/application/isolation_forest_detector.py` uses
exactly this shape — you don't need to understand *how* Isolation Forest
works internally (it isolates outliers by how few random splits it takes
to separate them) to read the code that calls it.

### XGBoost

A "gradient boosting" model — builds many small decision trees in
sequence, each one correcting the previous ones' mistakes. Same
`.fit()`/`.predict()` shape as scikit-learn. You don't need the boosting
math to debug `xgboost_forecaster.py` — just the interface.

### Accuracy metrics

- **MAE** (Mean Absolute Error) — average of `|predicted - actual|`, in the
  same units as the thing you're predicting (kW).
- **MAPE** (Mean Absolute Percentage Error) — same idea, but as a
  percentage of the actual value, so it's comparable across different
  scales.
- **Precision** — of everything you flagged as an anomaly, what fraction
  actually was one? **Recall** — of everything that actually *was* an
  anomaly, what fraction did you catch?

**In this repo:** `forecast/application/evaluation/metrics.py` — the
literal `mae()`/`mape()` functions used by the accuracy gate you already
know about (Load/Battery-SOC never cleared theirs).

---

## Tier 6 — observability & deployment

### Prometheus concepts

- **Counter** — only goes up (`.inc()`). Total commands ever completed.
- **Histogram** — records individual measurements (`.observe()`) so you
  can later ask "what's the 95th percentile?"
- **Gauge** — can go up or down (`.set()`) — "is this currently true?"

`/metrics` is just **plain text**, scraped periodically by Prometheus —
visit `http://127.0.0.1:8000/metrics` yourself and read it; it's not
mysterious once you've seen the raw format once.

### Grafana + PromQL basics

Grafana draws graphs from data Prometheus has collected. **PromQL** is
the query language — e.g. `rate(solarops_commands_completed_total[5m])`
means "how fast is this counter increasing, averaged over the last 5
minutes." You don't need to write PromQL from scratch to *read* the
provisioned dashboards in `monitoring/grafana/dashboards/`.

### Docker & Docker Compose

**Docker** packages an app plus everything it needs to run into one
portable **image**, run as a **container**. A `Dockerfile` is the recipe
for building that image, line by line (`FROM`, `RUN`, `COPY`, `CMD`).

**Docker Compose** runs *multiple* containers together as one system,
described in `docker-compose.yml` — `depends_on` controls startup order,
`healthcheck` lets one service wait until another is actually ready (not
just started), `profiles` lets you group optional services (like
Prometheus/Grafana here) that don't run by default.

**Why it matters for debugging:** `docker compose logs <service>` shows
you that one container's output — the single most useful command when
something in the stack won't come up.

### Environment variables / `.env` files

A way to configure a program from *outside* its code — `SOLAROPS_ENV=production`
set in the shell (or a `.env` file) changes behavior without editing
Python. `pydantic-settings` (`platform/settings.py`) is what reads these
into a typed Python object automatically.

---

## Tier 7 — frontend

### Streamlit

A way to build a web UI using only Python — no HTML/CSS/JavaScript
required for basic use. `st.metric(...)`, `st.button(...)`,
`st.plotly_chart(...)` each render one widget; the whole script re-runs
top to bottom every time the user interacts with something.

**`st.session_state`** is how a Streamlit app remembers something between
those re-runs (normally, every variable would just reset).

**`streamlit.testing.v1.AppTest`** — lets you run a Streamlit page's
script in a test, without a real browser, and inspect what it rendered.
This is *how* `tests/dashboard/` works at all.

### Plotly (`graph_objects`)

A charting library. `go.Figure()` builds a chart; `go.Scatter(...)`,
`go.Indicator(...)` are individual chart types (a line chart, a gauge).
You've already read real examples of both in `dashboard/pages/overview.py`.

---

## The concept, not a library: Domain-Driven Design & hexagonal architecture

This is the one that ties everything above together, and it's worth
returning to *after* the rest of this document clicks, not before:

- **Bounded context** — one department (Telemetry, Decision, ...) with its
  own vocabulary, not allowed to freely reach into another's.
- **Aggregate** — an object that owns its own consistency rules (`Command`
  enforcing its own state machine — nothing outside it can set `status`
  directly).
- **Value object** — an immutable object defined entirely by its data, not
  its identity (`Power(5.0)` equals any other `Power(5.0)`).
- **Domain event** — a record that "something happened" (`CommandCompleted`),
  decoupled from whoever might care about it later.
- **Ports & adapters (hexagonal architecture)** — the domain defines a
  *shape* it needs (a `Protocol`, the "port"); a concrete class
  elsewhere (the "adapter") fulfills it. This is Tier 1's `Protocol`
  section, at the architecture level instead of the language level.

`ONBOARDING.md` walks every folder through this lens; `PROJECT_DEEP_DIVE.md`
§4 explains *why* it was chosen. Read both again once this document's
Tier 0–3 feel solid — they'll land completely differently the second time.

---

## A practical week-by-week path, with exercises against this actual repo

**Week 1 — Tier 0 + Tier 1.** Read `shared_kernel/` end to end (small,
dependency-free, and now you can explain every line). *Exercise:* add a
new physical quantity type (e.g. `Pressure`) to `units.py`, following the
existing pattern exactly, and write one test for it.

**Week 2 — Tier 3 (pytest) + revisit Tier 0–1.** Run the full test suite,
then pick one test file and intentionally break the source code it tests
— watch it fail, read the traceback, fix it. *Exercise:* find a
`Protocol` in `ports.py` and find every class that satisfies it, by
searching for matching method names (not inheritance).

**Week 3 — Tier 2 (FastAPI).** Trace one endpoint from `api/routers/` all
the way to `platform/api_composition.py` and back. *Exercise:* add a new,
trivial read-only endpoint (e.g. `GET /sites/{id}/battery-soc` returning
just one number) and write a test for it.

**Week 4 onward — everything else, on demand.** Don't front-load Tiers
4–7 — go get them the day you're actually about to touch that folder.
Debugging a Streamlit page doesn't need SQLAlchemy; debugging the audit
log doesn't need Plotly.
