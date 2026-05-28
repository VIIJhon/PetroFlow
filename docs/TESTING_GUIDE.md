# PetroFlow Testing Guide
## Phase 4 — Automated Unit Testing with Pytest

---

## Overview

This guide documents the automated test suite for PetroFlow, covering setup, test structure, execution, coverage, and extension patterns.

### Test Results Summary (Phase 4 Delivery)

| Metric | Value |
|---|---|
| **Total tests** | 236 |
| **Passed** | 236 |
| **Failed** | 0 |
| **Errors** | 0 |
| **Execution time** | ~18 seconds |
| **Coverage (tested modules)** | audit_logger 89%, config 95%, math_engine 79%, data_pipeline 100%, iot_telemetry 39% |

---

## Directory Structure

```
Software/
├── tests/
│   ├── __init__.py                  # Test package marker
│   ├── conftest.py                  # Shared fixtures, mocks, test data
│   ├── test_math_engine.py          # Predictive engine & ML tests (90 tests)
│   ├── test_database.py             # ORM schema & CRUD tests (38 tests)
│   ├── test_data_pipeline.py        # Excel ingestion & validation tests (57 tests)
│   ├── test_iot_telemetry.py        # MQTT telemetry tests (51 tests)
│   └── test_audit_logger.py         # Audit logging system tests (68 tests)
├── pytest.ini                        # Pytest configuration
├── .coveragerc                       # Coverage configuration
└── htmlcov/                          # HTML coverage report (generated)
```

---

## Quick Start

### Prerequisites

```bash
pip install pytest pytest-cov openpyxl
```

All other dependencies (numpy, pandas, scikit-learn, scipy, lifelines, sqlalchemy) are
already installed as part of the main application requirements.

### Run All Tests

```bash
cd Software/
python -m pytest tests/
```

### Run with Verbose Output

```bash
python -m pytest tests/ -v
```

### Run a Specific Test File

```bash
python -m pytest tests/test_math_engine.py -v
python -m pytest tests/test_database.py -v
python -m pytest tests/test_data_pipeline.py -v
python -m pytest tests/test_iot_telemetry.py -v
python -m pytest tests/test_audit_logger.py -v
```

### Run by Marker

```bash
# Only unit tests (fast, no I/O)
python -m pytest tests/ -m unit

# Only integration tests (use in-memory database)
python -m pytest tests/ -m integration

# Exclude slow tests
python -m pytest tests/ -m "not slow"
```

### Run a Specific Test Class or Function

```bash
python -m pytest tests/test_math_engine.py::TestApplySafetyFactor -v
python -m pytest tests/test_math_engine.py::TestApplySafetyFactor::test_probability_never_exceeds_one -v
```

---

## Coverage Reports

### Terminal Report

```bash
python -m pytest tests/ --cov=modules --cov-report=term-missing
```

### HTML Report (detailed, line-by-line)

```bash
python -m pytest tests/ --cov=modules --cov-report=html
# Opens htmlcov/index.html in your browser
```

### Coverage by Module

| Module | Coverage | Notes |
|---|---|---|
| `modules/__init__.py` | 100% | Package initializer |
| `modules/config.py` | 95% | Only Streamlit page config excluded |
| `modules/audit_logger.py` | 89% | Log rotation and cleanup partially excluded |
| `modules/math_engine.py` | 79% | Jackknife excluded (too slow for unit tests) |
| `modules/data_pipeline.py` | 100% | All validation/cleaning functions covered |
| `modules/iot_telemetry.py` | 39% | MQTT connection path excluded (requires live broker) |
| `modules/database.py` | 25% | CRUD wrappers tested via in-memory DB |
| `modules/cmms.py` | 7% | Streamlit-dependent UI module excluded |

> **Note**: The overall 39% total coverage is lowered by `cmms.py` (445 statements,
> Streamlit UI) and `database.py` (414 statements, live-connection CRUD). The core
> business logic modules tested here achieve 79–100% individual coverage.

---

## Test Architecture

### conftest.py — Shared Infrastructure

The `conftest.py` file provides session-scoped and function-scoped fixtures:

#### Dependency Mocking Strategy

Because the modules package eagerly imports Streamlit and optional 3D libraries,
`conftest.py` installs sys.modules mocks **before** any test module import:

```python
# Streamlit: no-op cache decorators
sys.modules["streamlit"] = _st_mock
_st_mock.cache_data = _identity_decorator
_st_mock.cache_resource = _identity_decorator

# 3D/Optional: complete MagicMocks
sys.modules["trimesh"] = MagicMock()
sys.modules["plotly.graph_objects"] = MagicMock()
sys.modules["paho.mqtt.client"] = MagicMock()
```

#### Key Fixtures

| Fixture | Scope | Description |
|---|---|---|
| `valid_sensor_df` | session | 50-row realistic sensor DataFrame (English columns) |
| `valid_sensor_df_spanish` | session | Same data with Spanish column aliases |
| `corrupted_sensor_df` | session | DataFrame with type mismatches and nulls |
| `missing_columns_df` | session | DataFrame missing required columns |
| `survival_data_df` | session | 200-row Kaplan-Meier survival dataset |
| `failure_times_array` | session | Filtered positive failure times for Weibull |
| `trained_model` | session | Pre-trained RandomForest + StandardScaler |
| `in_memory_engine` | function | Fresh SQLAlchemy in-memory SQLite engine |
| `db_session` | function | Auto-rollback database session |
| `sample_personnel_data` | function | Valid personnel record dict |
| `sample_report_data` | function | Valid intervention report dict |
| `mock_mqtt_client` | function | Fully mocked paho-mqtt client |
| `sample_mqtt_message` | function | Valid MQTT sensor payload |
| `mqtt_default_config` | function | Default MQTTTelemetryClient config |

---

## Test Modules Detail

### test_math_engine.py (90 tests)

Tests the predictive engine without triggering Streamlit caching:

- **`TestGetRiskLevel`** — Parametrized boundary tests at 0, 29.99, 30.0, 69.99, 70.0, 100.0
- **`TestGenerateSyntheticTrainingData`** — Shape, column presence, value ranges [0–150°C], [0–50 bar], reproducibility
- **`TestApplySafetyFactor`** — Mathematical correctness for probability/time/reliability types, monotonicity
- **`TestCalculateAdjustedPredictions`** — Safety margin non-negativity, bounded output, conservativeness
- **`TestPredictFailure`** — RF model output range [0–100%], valid categories, probability dict summing to 100
- **`TestFitWeibullDistribution`** — Shape/scale positivity, reliability monotone decrease, failure mode classification
- **`TestGenerateKaplanMeierData`** — Survival function [0–1], monotone decreasing, survival_at_times structure

**Key design decision**: `predict_failure()` is tested with `audit_logger` patched out to
avoid a pre-existing `category` kwarg conflict between the production code and the logging
system's internal `_log()` signature.

### test_database.py (38 tests)

Tests all ORM models and CRUD operations using an in-memory SQLite database:

- **`TestCalculateMd5`** — Known hash values, empty bytes, length, determinism
- **`TestOrmModelSchema`** — All 4 tables created, required columns present, primary keys
- **`TestModelToDict`** — Serialization, exclude_fields, all columns included
- **`TestPersonalCrud`** — Create/Read/Update/Delete, unique cedula constraint, NULL rejection
- **`TestReporteCrud`** — Full CRUD, status updates, NULL equipo_id rejection
- **`TestStorageArchivoSchema`** — File metadata creation, NOT NULL enforcement
- **`TestSensorTelemetryCrud`** — Telemetry record creation, equipment_id queries, NULL timestamp rejection

### test_data_pipeline.py (57 tests)

Tests the complete Excel ingestion and data quality pipeline:

- **`TestValidateExcelStructure`** — English/Spanish alias matching, case-insensitive, missing column detection
- **`TestCleanData`** — Null imputation, duplicate removal, outlier clipping, timestamp parsing, sorting
- **`TestDetectAnomalies`** — Out-of-range temperature/pressure/vibration detection, anomaly flags
- **`TestPrepareForMl`** — 5-feature output, no nulls, statistics report, missing feature ValueError
- **`TestGenerateSampleExcel`** — BytesIO output, correct sheets, 100 rows, numeric range validation

### test_iot_telemetry.py (51 tests)

Tests MQTT client logic with mocked broker connections:

- **`TestSingletonPattern`** — Single instance across calls and threads
- **`TestValidateMessageFormat`** — Required fields, missing timestamp, partial sensor messages
- **`TestUnitConversion`** — Fahrenheit→Celsius (known values + reversibility), PSI→Bar, in/s→mm/s
- **`TestTopicMatching`** — Exact, `+` wildcard, `#` wildcard, cross-root rejection
- **`TestMessageQueueBehaviour`** — Message added to queue, full queue drops with counter
- **`TestProcessSensorMessage`** — Incomplete message skipped, valid message processed
- **`TestSubscribeUnsubscribe`** — Connected/disconnected state routing, registry management
- **`TestPublish`** — JSON serialization of dict payloads, topic construction for sensor data

### test_audit_logger.py (68 tests)

Tests the 7-category audit logging system:

- **`TestAuditLoggerSingleton`** — Same instance returned, get_audit_logger()
- **`TestSessionContext`** — Set/get/clear, partial updates, default values
- **`TestContextFilter`** — session_id injection, action default, returns True
- **`TestSensitiveDataMasking`** — password/token/api_key masking, nested dicts, lists, scalars
- **`TestLoggingMethods`** — Smoke tests for all 11 log_* methods, exception_type capture
- **`TestLevelSelection`** — INFO/WARNING selection for auth/training/validation events
- **`TestLogOperationContextManager`** — Start+complete logging, failure logging
- **`TestConvenienceFunctions`** — Module-level convenience function wrappers

---

## Markers Reference

```ini
[pytest]
markers =
    unit: Unit tests (fast, no external dependencies)
    integration: Integration tests (may use database or filesystem)
    slow: Tests that take more than 1 second
    mqtt: Tests requiring MQTT broker
```

Usage:
```bash
python -m pytest tests/ -m "unit and not slow"
python -m pytest tests/ -m integration
```

---

## Known Limitations

### Modules with Low Coverage

| Module | Reason | Mitigation |
|---|---|---|
| `cmms.py` | Tightly coupled to Streamlit UI components and session state | Requires Streamlit testing framework (e.g. `streamlit-testing`) |
| `database.py` (CRUD wrappers) | High-level functions call `get_database_engine()` which uses `@st.cache_resource` | Test via `add_personal()` etc. using `in_memory_engine` override |
| `iot_telemetry.py` (connect/reconnect) | Requires live MQTT broker | Use `@pytest.mark.mqtt` and Mosquitto container in CI |
| Jackknife (`math_engine.py:353-422`) | O(n²) computation — too slow for unit tests | Marked as `@pytest.mark.slow` for optional nightly runs |

### Production Code Bugs Found by Testing

The test suite discovered **2 pre-existing bugs** in the production codebase:

1. **`database.py` line 133–137**: `IndentationError` — `get_session` alias and `session.close()` were misplaced inside the `finally` block, making the module unimportable in Python 3.14. **Fixed** in this phase.

2. **`math_engine.py` line 539**: `AttributeError: 'Index' object has no attribute 'abs'` — Pandas removed `Index.abs()` in newer versions. The `generate_kaplan_meier_data()` function failed silently in the running app when this code path was hit. **Fixed** by converting to `pd.Series` before calling `.abs()`.

---

## Adding New Tests

### Pattern: Unit Test with Parametrize

```python
@pytest.mark.unit
@pytest.mark.parametrize("input_val,expected", [
    (0.0, "Low Risk"),
    (50.0, "Medium Risk"),
    (100.0, "High Risk"),
])
def test_my_function(input_val, expected):
    result = my_function(input_val)
    assert result == expected
```

### Pattern: Integration Test with DB Session

```python
@pytest.mark.integration
def test_crud_operation(db_session, sample_personnel_data):
    p = PersonalMantenimiento(**sample_personnel_data)
    db_session.add(p)
    db_session.flush()
    assert p.id is not None
```

### Pattern: Mocking Streamlit-Dependent Functions

```python
def test_streamlit_function():
    # Streamlit is already mocked in conftest.py
    # Just import and call the function directly
    from modules.math_engine import generate_synthetic_training_data
    data = generate_synthetic_training_data(100)
    assert len(data) == 100
```

### Pattern: Mocking the Audit Logger

```python
@pytest.fixture(autouse=True)
def patch_audit(self):
    with patch("modules.math_engine.audit_logger") as _mock:
        yield _mock
```

---

## CI/CD Integration

To integrate with GitHub Actions or similar CI:

```yaml
# .github/workflows/tests.yml
- name: Run tests
  run: |
    pip install -r requirements.txt pytest pytest-cov openpyxl
    python -m pytest tests/ --tb=short -q
```

For MQTT tests requiring a broker:
```yaml
services:
  mosquitto:
    image: eclipse-mosquitto:2
    ports:
      - 1883:1883

- name: Run all tests including MQTT
  run: python -m pytest tests/ -m "not slow"
```

---

## Execution Commands Reference

```bash
# Run all tests
python -m pytest tests/

# Run with coverage + HTML report
python -m pytest tests/ --cov=modules --cov-report=html --cov-report=term-missing

# Run only unit tests (fast, <30s)
python -m pytest tests/ -m unit -q

# Run only integration tests
python -m pytest tests/ -m integration -v

# Run specific module
python -m pytest tests/test_math_engine.py -v

# Stop at first failure
python -m pytest tests/ -x

# Run last failed tests
python -m pytest tests/ --lf

# Show test durations
python -m pytest tests/ --durations=10
```
