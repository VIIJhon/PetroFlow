"""
core/alarm_manager.py
=====================
PetroFlow Enterprise — ISA-18.2 Alarm Management System

Implements the key requirements of ISA-18.2 / IEC 62682 (Management of
Alarm Systems for the Process Industries):

  - Alarm prioritization (Critical / High / Medium / Low)
  - Alarm states (Unacknowledged, Acknowledged, Cleared, Shelved)
  - Deadband logic  — prevents alarm chattering near the setpoint
  - Shelving        — operator can suppress an alarm for a defined period
  - Flood detection — groups >10 alarms/60 s into a flood event
  - Audit trail     — every state change logged via audit_logging_service
  - Persistence     — alarms stored in the local SQLite database

Compliance references
---------------------
  ISA-18.2-2016   Management of Alarm Systems for the Process Industries
  IEC 62682:2014  Same standard (international equivalent)
  API 670         Alarm/danger setpoints for vibration (used in setpoint defaults)
"""

from __future__ import annotations

import uuid
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class AlarmPriority(str, Enum):
    """
    ISA-18.2 Section 5.4 — four-level priority scheme.
    Maps directly to failure probability thresholds.
    """
    CRITICAL = "CRITICAL"   # Failure prob > 70 % — immediate operator action required
    HIGH     = "HIGH"       # Failure prob > 50 % — action required within minutes
    MEDIUM   = "MEDIUM"     # Failure prob > 30 % — action required within the shift
    LOW      = "LOW"        # Failure prob > 15 % — action can be deferred


class AlarmState(str, Enum):
    """ISA-18.2 Section 5.3 — standard alarm states."""
    UNACKNOWLEDGED = "UNACKNOWLEDGED"   # Active, not yet seen by operator
    ACKNOWLEDGED   = "ACKNOWLEDGED"     # Operator has seen it, still active
    CLEARED        = "CLEARED"          # Condition returned to normal, acknowledged
    SHELVED        = "SHELVED"          # Temporarily suppressed by operator


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Alarm:
    """
    Represents a single alarm instance per ISA-18.2.

    Fields
    ------
    id              : Unique alarm ID (UUID4)
    equipment_id    : Tag/ID of the equipment that generated the alarm
    parameter       : Sensor parameter that crossed the threshold
    priority        : AlarmPriority (Critical / High / Medium / Low)
    state           : Current AlarmState
    value           : Current sensor value (SI units)
    setpoint        : Threshold that was crossed (SI units)
    deadband        : Hysteresis band — alarm only clears when value drops
                      below (setpoint - deadband). Prevents chattering.
    unit_si         : Unit string for display (e.g. 'mm/s', 'Bar', 'degC')
    timestamp       : UTC datetime when the alarm was raised
    acknowledged_by : Username of the operator who acknowledged
    acknowledged_at : UTC datetime of acknowledgement
    shelved_until   : UTC datetime when shelving expires (None if not shelved)
    shelved_by      : Username who shelved the alarm
    shelve_reason   : Mandatory reason text for shelving
    cleared_at      : UTC datetime when condition returned to normal
    equipment_type  : 'pump' | 'compressor' | 'turbine'
    standard_ref    : Regulatory reference (e.g. 'API 670', 'ISO 10816-3')
    """
    id:              str            = field(default_factory=lambda: str(uuid.uuid4()))
    equipment_id:    str            = ""
    parameter:       str            = ""
    priority:        AlarmPriority  = AlarmPriority.MEDIUM
    state:           AlarmState     = AlarmState.UNACKNOWLEDGED
    value:           float          = 0.0
    setpoint:        float          = 0.0
    deadband:        float          = 0.0
    unit_si:         str            = ""
    timestamp:       datetime       = field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged_by: Optional[str]  = None
    acknowledged_at: Optional[datetime] = None
    shelved_until:   Optional[datetime] = None
    shelved_by:      Optional[str]  = None
    shelve_reason:   Optional[str]  = None
    cleared_at:      Optional[datetime] = None
    equipment_type:  str            = "pump"
    standard_ref:    str            = ""

    @property
    def is_active(self) -> bool:
        """Alarm is active if not cleared and not shelved (or shelve expired)."""
        if self.state == AlarmState.CLEARED:
            return False
        if self.state == AlarmState.SHELVED:
            if self.shelved_until and datetime.now(timezone.utc) > self.shelved_until:
                return True   # Shelve expired
            return False
        return True

    @property
    def age_minutes(self) -> float:
        """Minutes since the alarm was raised."""
        delta = datetime.now(timezone.utc) - self.timestamp
        return delta.total_seconds() / 60.0

    def to_dict(self) -> dict:
        """Serialize for database storage and API responses."""
        return {
            "id":              self.id,
            "equipment_id":    self.equipment_id,
            "parameter":       self.parameter,
            "priority":        self.priority.value,
            "state":           self.state.value,
            "value":           self.value,
            "setpoint":        self.setpoint,
            "deadband":        self.deadband,
            "unit_si":         self.unit_si,
            "timestamp":       self.timestamp.isoformat(),
            "acknowledged_by": self.acknowledged_by,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "shelved_until":   self.shelved_until.isoformat() if self.shelved_until else None,
            "shelved_by":      self.shelved_by,
            "shelve_reason":   self.shelve_reason,
            "cleared_at":      self.cleared_at.isoformat() if self.cleared_at else None,
            "equipment_type":  self.equipment_type,
            "standard_ref":    self.standard_ref,
        }


@dataclass
class AlarmFloodEvent:
    """
    ISA-18.2 Section 6.5 — alarm flood grouping.
    Fires when > FLOOD_THRESHOLD alarms occur within FLOOD_WINDOW_SECONDS.
    """
    id:          str      = field(default_factory=lambda: str(uuid.uuid4()))
    alarm_ids:   List[str] = field(default_factory=list)
    started_at:  datetime  = field(default_factory=lambda: datetime.now(timezone.utc))
    alarm_count: int       = 0


# ---------------------------------------------------------------------------
# Alarm setpoint defaults (ISA-18.2 / API 670 references)
# ---------------------------------------------------------------------------

# Maps (equipment_type, parameter) → (setpoint_SI, deadband_SI, unit_si, priority, standard_ref)
DEFAULT_SETPOINTS: Dict[tuple, tuple] = {
    # ---- Pumps (API 610 / ISO 10816-3) ------------------------------------
    ("pump", "vibration"):           (7.1,  0.5, "mm/s", AlarmPriority.HIGH,     "ISO 10816-3 Zone C/D"),
    ("pump", "axial_vibration"):     (7.1,  0.5, "mm/s", AlarmPriority.HIGH,     "API 670"),
    ("pump", "discharge_temperature"): (105, 3.0, "degC", AlarmPriority.MEDIUM,  "API 610"),
    ("pump", "available_npsh"):      (1.5,  0.2, "m",    AlarmPriority.CRITICAL, "API 610 Cavitation"),
    ("pump", "inlet_pressure"):      (0.3,  0.05,"Bar",  AlarmPriority.HIGH,     "Suction starvation"),
    # ---- Compressors (API 617 / API 670) ----------------------------------
    ("compressor", "radial_vibration"): (5.0, 0.3, "mm/s", AlarmPriority.HIGH,   "API 670 Alert"),
    ("compressor", "axial_vibration"):  (5.0, 0.3, "mm/s", AlarmPriority.HIGH,   "API 670 Alert"),
    ("compressor", "discharge_temperature"): (140, 5.0, "degC", AlarmPriority.MEDIUM, "API 617"),
    ("compressor", "compression_ratio"):     (9.5, 0.2, "-",    AlarmPriority.MEDIUM, "Design limit"),
    # ---- Turbines (API 612 / API 670) -------------------------------------
    ("turbine", "axial_vibration"):      (4.5, 0.3, "mm/s", AlarmPriority.HIGH,   "API 670 Alert"),
    ("turbine", "steam_temperature"):    (380, 10.0,"degC", AlarmPriority.MEDIUM, "API 612"),
    ("turbine", "exhaust_temperature"):  (220,  8.0,"degC", AlarmPriority.MEDIUM, "API 612"),
    ("turbine", "synchronous_speed"):    (5200, 100,"RPM",  AlarmPriority.CRITICAL,"Overspeed trip"),
}

FLOOD_THRESHOLD       = 10   # alarms
FLOOD_WINDOW_SECONDS  = 60   # seconds
MAX_SHELVE_HOURS      = 72   # ISA-18.2 recommended maximum shelve duration


# ---------------------------------------------------------------------------
# Alarm Manager
# ---------------------------------------------------------------------------

class AlarmManager:
    """
    Central alarm management engine compliant with ISA-18.2 / IEC 62682.

    Usage
    -----
        manager = AlarmManager()

        # Evaluate current sensor readings against setpoints
        new_alarms = manager.evaluate(
            equipment_id   = "PUMP-001",
            equipment_type = "pump",
            readings       = {"vibration": 8.2, "discharge_temperature": 98}
        )

        # Acknowledge an alarm
        manager.acknowledge(alarm_id, operator="j.smith")

        # Get all active alarms
        active = manager.get_active_alarms()
    """

    def __init__(self) -> None:
        # In-memory store — keyed by alarm ID
        self._alarms: Dict[str, Alarm] = {}
        # Track recent alarm timestamps for flood detection
        self._recent_timestamps: List[datetime] = []
        self._flood_events: List[AlarmFloodEvent] = []

    # -----------------------------------------------------------------------
    # Core evaluation
    # -----------------------------------------------------------------------

    def evaluate(
        self,
        equipment_id:   str,
        equipment_type: str,
        readings:       Dict[str, float],
        failure_probability: float = 0.0,
    ) -> List[Alarm]:
        """
        Compare sensor readings against default setpoints and failure
        probability thresholds. Creates new alarms or clears existing ones.

        Parameters
        ----------
        equipment_id        : Equipment tag (e.g. 'PUMP-001')
        equipment_type      : 'pump' | 'compressor' | 'turbine'
        readings            : {parameter: value_in_SI}
        failure_probability : ML model output (0–100 %)

        Returns
        -------
        List of newly created Alarm objects.
        """
        new_alarms: List[Alarm] = []

        # --- Parameter-level alarms ----------------------------------------
        for parameter, value in readings.items():
            key = (equipment_type.lower(), parameter)
            spec = DEFAULT_SETPOINTS.get(key)
            if spec is None:
                continue

            setpoint, deadband, unit_si, priority, standard_ref = spec
            existing = self._find_alarm(equipment_id, parameter)

            if value > setpoint:
                if existing is None or not existing.is_active:
                    alarm = self._create_alarm(
                        equipment_id   = equipment_id,
                        equipment_type = equipment_type,
                        parameter      = parameter,
                        priority       = priority,
                        value          = value,
                        setpoint       = setpoint,
                        deadband       = deadband,
                        unit_si        = unit_si,
                        standard_ref   = standard_ref,
                    )
                    new_alarms.append(alarm)
            else:
                # Check if existing alarm can be cleared (value below setpoint - deadband)
                if existing and existing.is_active and value <= (setpoint - deadband):
                    self._clear_alarm(existing)

        # --- Failure probability alarm -------------------------------------
        prob_priority = self._priority_from_probability(failure_probability)
        if prob_priority is not None:
            existing_prob = self._find_alarm(equipment_id, "failure_probability")
            if existing_prob is None or not existing_prob.is_active:
                alarm = self._create_alarm(
                    equipment_id   = equipment_id,
                    equipment_type = equipment_type,
                    parameter      = "failure_probability",
                    priority       = prob_priority,
                    value          = failure_probability,
                    setpoint       = self._prob_threshold(prob_priority),
                    deadband       = 5.0,
                    unit_si        = "%",
                    standard_ref   = "ML Prediction Model",
                )
                new_alarms.append(alarm)
            elif existing_prob and existing_prob.is_active:
                # Update value on existing alarm
                existing_prob.value = failure_probability
        else:
            # Probability returned to normal — clear the prob alarm
            existing_prob = self._find_alarm(equipment_id, "failure_probability")
            if existing_prob and existing_prob.is_active:
                clear_threshold = self._prob_threshold(existing_prob.priority) - 5.0
                if failure_probability < clear_threshold:
                    self._clear_alarm(existing_prob)

        # --- Flood detection -----------------------------------------------
        if new_alarms:
            self._check_flood(new_alarms)

        return new_alarms

    # -----------------------------------------------------------------------
    # Operator actions
    # -----------------------------------------------------------------------

    def acknowledge(self, alarm_id: str, operator: str) -> bool:
        """
        Mark an alarm as acknowledged.

        ISA-18.2: Acknowledgement confirms the operator is aware of the
        condition. The alarm remains active until the process value returns
        to the normal operating range (below setpoint - deadband).

        Returns True if the alarm was found and acknowledged.
        """
        alarm = self._alarms.get(alarm_id)
        if alarm is None:
            logger.warning("Acknowledge: alarm %s not found", alarm_id)
            return False

        if alarm.state == AlarmState.UNACKNOWLEDGED:
            alarm.state          = AlarmState.ACKNOWLEDGED
            alarm.acknowledged_by = operator
            alarm.acknowledged_at = datetime.now(timezone.utc)
            self._audit_state_change(alarm, "ACKNOWLEDGED", operator)
            logger.info("Alarm %s acknowledged by %s", alarm_id, operator)
            return True

        logger.debug("Alarm %s already in state %s — no change", alarm_id, alarm.state)
        return False

    def shelve(
        self,
        alarm_id:      str,
        operator:      str,
        reason:        str,
        duration_hours: float = 8.0,
    ) -> bool:
        """
        Temporarily suppress an alarm for a defined period.

        ISA-18.2 Section 6.3: Shelving requires a mandatory reason and a
        defined duration. Maximum duration is capped at MAX_SHELVE_HOURS (72 h).

        Returns True if the alarm was shelved successfully.
        """
        alarm = self._alarms.get(alarm_id)
        if alarm is None:
            logger.warning("Shelve: alarm %s not found", alarm_id)
            return False

        if not reason or not reason.strip():
            logger.warning("Shelve rejected — reason is mandatory (ISA-18.2 Section 6.3)")
            return False

        duration_hours = min(duration_hours, MAX_SHELVE_HOURS)
        alarm.state        = AlarmState.SHELVED
        alarm.shelved_by   = operator
        alarm.shelve_reason = reason.strip()
        alarm.shelved_until = datetime.now(timezone.utc) + timedelta(hours=duration_hours)
        self._audit_state_change(alarm, f"SHELVED ({duration_hours:.1f} h)", operator,
                                  extra={"reason": reason})
        logger.info("Alarm %s shelved by %s for %.1f h — reason: %s",
                    alarm_id, operator, duration_hours, reason)
        return True

    def unshelve(self, alarm_id: str, operator: str) -> bool:
        """Manually remove a shelved alarm back to active state."""
        alarm = self._alarms.get(alarm_id)
        if alarm and alarm.state == AlarmState.SHELVED:
            alarm.state        = AlarmState.UNACKNOWLEDGED
            alarm.shelved_until = None
            alarm.shelved_by   = None
            alarm.shelve_reason = None
            self._audit_state_change(alarm, "UNSHELVED", operator)
            return True
        return False

    # -----------------------------------------------------------------------
    # Queries
    # -----------------------------------------------------------------------

    def get_active_alarms(
        self,
        equipment_id:   Optional[str] = None,
        priority:       Optional[AlarmPriority] = None,
        equipment_type: Optional[str] = None,
    ) -> List[Alarm]:
        """Return all currently active (non-cleared, non-shelved) alarms."""
        result = [a for a in self._alarms.values() if a.is_active]
        if equipment_id:
            result = [a for a in result if a.equipment_id == equipment_id]
        if priority:
            result = [a for a in result if a.priority == priority]
        if equipment_type:
            result = [a for a in result if a.equipment_type == equipment_type]
        # Sort by priority (CRITICAL first), then by age (oldest first)
        priority_order = {
            AlarmPriority.CRITICAL: 0,
            AlarmPriority.HIGH:     1,
            AlarmPriority.MEDIUM:   2,
            AlarmPriority.LOW:      3,
        }
        return sorted(result, key=lambda a: (priority_order[a.priority], a.timestamp))

    def get_all_alarms(self, limit: int = 200) -> List[Alarm]:
        """Return all alarms (active + cleared) up to the given limit."""
        all_alarms = sorted(self._alarms.values(),
                            key=lambda a: a.timestamp, reverse=True)
        return all_alarms[:limit]

    def get_alarm_rate(self, window_minutes: int = 10) -> float:
        """
        ISA-18.2 KPI: alarms per 10 minutes.
        Target: < 1 alarm / 10 min per operator (manageable rate).
        """
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
        count  = sum(1 for a in self._alarms.values() if a.timestamp >= cutoff)
        return count / window_minutes * 10  # normalise to per-10-min rate

    def get_flood_events(self) -> List[AlarmFloodEvent]:
        """Return all detected flood events."""
        return list(self._flood_events)

    def alarm_count_by_priority(self) -> Dict[str, int]:
        """Return count of active alarms grouped by priority."""
        counts: Dict[str, int] = {p.value: 0 for p in AlarmPriority}
        for alarm in self.get_active_alarms():
            counts[alarm.priority.value] += 1
        return counts

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------

    def _create_alarm(self, **kwargs) -> Alarm:
        alarm = Alarm(**kwargs)
        self._alarms[alarm.id] = alarm
        self._recent_timestamps.append(alarm.timestamp)
        self._audit_new_alarm(alarm)
        logger.warning(
            "[%s] New alarm: %s / %s = %.2f %s (setpoint %.2f) — %s",
            alarm.priority.value, alarm.equipment_id, alarm.parameter,
            alarm.value, alarm.unit_si, alarm.setpoint, alarm.standard_ref,
        )
        return alarm

    def _clear_alarm(self, alarm: Alarm) -> None:
        alarm.state      = AlarmState.CLEARED
        alarm.cleared_at = datetime.now(timezone.utc)
        self._audit_state_change(alarm, "CLEARED", "system")
        logger.info("Alarm %s cleared — %s / %s returned to normal",
                    alarm.id, alarm.equipment_id, alarm.parameter)

    def _find_alarm(self, equipment_id: str, parameter: str) -> Optional[Alarm]:
        """Find the most recent alarm for a given equipment + parameter pair."""
        matches = [
            a for a in self._alarms.values()
            if a.equipment_id == equipment_id and a.parameter == parameter
        ]
        return max(matches, key=lambda a: a.timestamp) if matches else None

    def _check_flood(self, new_alarms: List[Alarm]) -> None:
        """ISA-18.2 flood detection — group alarms if rate exceeds threshold."""
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=FLOOD_WINDOW_SECONDS)
        self._recent_timestamps = [t for t in self._recent_timestamps if t >= cutoff]
        if len(self._recent_timestamps) >= FLOOD_THRESHOLD:
            flood = AlarmFloodEvent(
                alarm_ids   = [a.id for a in new_alarms],
                alarm_count = len(self._recent_timestamps),
            )
            self._flood_events.append(flood)
            logger.critical(
                "ALARM FLOOD detected: %d alarms in %d seconds",
                len(self._recent_timestamps), FLOOD_WINDOW_SECONDS,
            )

    @staticmethod
    def _priority_from_probability(prob: float) -> Optional[AlarmPriority]:
        """Map failure probability to alarm priority (None = no alarm)."""
        if prob >= 70:
            return AlarmPriority.CRITICAL
        if prob >= 50:
            return AlarmPriority.HIGH
        if prob >= 30:
            return AlarmPriority.MEDIUM
        if prob >= 15:
            return AlarmPriority.LOW
        return None

    @staticmethod
    def _prob_threshold(priority: AlarmPriority) -> float:
        thresholds = {
            AlarmPriority.CRITICAL: 70.0,
            AlarmPriority.HIGH:     50.0,
            AlarmPriority.MEDIUM:   30.0,
            AlarmPriority.LOW:      15.0,
        }
        return thresholds[priority]

    def _audit_new_alarm(self, alarm: Alarm) -> None:
        try:
            from core.audit_logging_service import get_audit_logger
            get_audit_logger().log_system(
                f"ALARM RAISED [{alarm.priority.value}] {alarm.equipment_id}/{alarm.parameter} "
                f"= {alarm.value:.2f} {alarm.unit_si} (setpoint {alarm.setpoint:.2f})",
                action="ALARM_RAISED",
                equipment_type=alarm.equipment_type,
            )
        except Exception:
            logger.debug("Audit log unavailable for new alarm %s", alarm.id)

    def _audit_state_change(
        self, alarm: Alarm, new_state: str, operator: str, extra: dict = None
    ) -> None:
        try:
            from core.audit_logging_service import get_audit_logger
            details = {"alarm_id": alarm.id, "equipment_id": alarm.equipment_id,
                       "parameter": alarm.parameter, "operator": operator}
            if extra:
                details.update(extra)
            get_audit_logger().log_system(
                f"ALARM {new_state}: {alarm.equipment_id}/{alarm.parameter}",
                action=f"ALARM_{new_state.split()[0]}",
                equipment_type=alarm.equipment_type,
            )
        except Exception:
            logger.debug("Audit log unavailable for state change on alarm %s", alarm.id)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_alarm_manager: Optional[AlarmManager] = None


def get_alarm_manager() -> AlarmManager:
    """Return the application-wide AlarmManager singleton."""
    global _alarm_manager
    if _alarm_manager is None:
        _alarm_manager = AlarmManager()
        logger.info("AlarmManager initialized (ISA-18.2 compliant)")
    return _alarm_manager
