"""
Advanced Interactive Event System for PetroFlow Visual Simulation

This module provides a comprehensive event-driven architecture for real-time
equipment interactions, parameter changes, and user interface events.

Features:
- Event-driven architecture with callback system
- Real-time parameter validation and updates
- Equipment selection and multi-select
- Drag-and-drop functionality
- Context menus and keyboard shortcuts
- Undo/redo functionality
- State synchronization
- Visual feedback and animations

Author: PetroFlow Development Team
Date: 2026-05-13
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from datetime import datetime
import json
import copy
import logging
from collections import deque

# Configure logging
logger = logging.getLogger(__name__)


class EventType(Enum):
    """Enumeration of all possible interaction event types."""
    
    # Mouse events
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    RIGHT_CLICK = "right_click"
    HOVER = "hover"
    HOVER_END = "hover_end"
    
    # Drag and drop events
    DRAG_START = "drag_start"
    DRAG_MOVE = "drag_move"
    DRAG_END = "drag_end"
    DROP = "drop"
    
    # Selection events
    SELECT = "select"
    DESELECT = "deselect"
    MULTI_SELECT = "multi_select"
    SELECT_ALL = "select_all"
    CLEAR_SELECTION = "clear_selection"
    
    # Parameter events
    PARAMETER_CHANGE = "parameter_change"
    PARAMETER_VALIDATE = "parameter_validate"
    PARAMETER_COMMIT = "parameter_commit"
    PARAMETER_CANCEL = "parameter_cancel"
    
    # Equipment events
    EQUIPMENT_ADD = "equipment_add"
    EQUIPMENT_DELETE = "equipment_delete"
    EQUIPMENT_DUPLICATE = "equipment_duplicate"
    EQUIPMENT_MOVE = "equipment_move"
    
    # State events
    STATE_CHANGE = "state_change"
    CALCULATION_START = "calculation_start"
    CALCULATION_COMPLETE = "calculation_complete"
    CALCULATION_ERROR = "calculation_error"
    
    # Alert events
    ALERT = "alert"
    WARNING = "warning"
    ERROR = "error"
    INFO = "info"
    
    # View events
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"
    PAN = "pan"
    FIT_TO_SCREEN = "fit_to_screen"
    RESET_VIEW = "reset_view"
    
    # Context menu events
    CONTEXT_MENU_OPEN = "context_menu_open"
    CONTEXT_MENU_CLOSE = "context_menu_close"
    CONTEXT_MENU_ACTION = "context_menu_action"
    
    # Keyboard events
    KEY_PRESS = "key_press"
    KEY_RELEASE = "key_release"
    SHORTCUT = "shortcut"
    
    # Copy/Paste events
    COPY = "copy"
    PASTE = "paste"
    CUT = "cut"
    
    # Undo/Redo events
    UNDO = "undo"
    REDO = "redo"
    
    # Search/Filter events
    SEARCH = "search"
    FILTER = "filter"
    CLEAR_FILTER = "clear_filter"


class InteractionMode(Enum):
    """Current interaction mode of the system."""
    
    NORMAL = "normal"
    SELECTING = "selecting"
    DRAGGING = "dragging"
    EDITING = "editing"
    PANNING = "panning"
    ZOOMING = "zooming"


@dataclass
class InteractionEvent:
    """
    Dataclass representing a single interaction event.
    
    Attributes:
        event_type: Type of the event
        timestamp: When the event occurred
        equipment_id: ID of equipment involved (if applicable)
        position: Screen/canvas position (x, y)
        data: Additional event-specific data
        modifiers: Keyboard modifiers (ctrl, shift, alt)
        propagate: Whether to propagate to other handlers
        handled: Whether the event has been handled
    """
    
    event_type: EventType
    timestamp: datetime = field(default_factory=datetime.now)
    equipment_id: Optional[str] = None
    position: Optional[Tuple[float, float]] = None
    data: Dict[str, Any] = field(default_factory=dict)
    modifiers: Dict[str, bool] = field(default_factory=lambda: {
        "ctrl": False,
        "shift": False,
        "alt": False
    })
    propagate: bool = True
    handled: bool = False
    
    def stop_propagation(self) -> None:
        """Stop event from propagating to other handlers."""
        self.propagate = False
        self.handled = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "equipment_id": self.equipment_id,
            "position": self.position,
            "data": self.data,
            "modifiers": self.modifiers,
            "handled": self.handled
        }


@dataclass
class ParameterChange:
    """
    Represents a parameter change for undo/redo functionality.
    
    Attributes:
        equipment_id: ID of equipment
        parameter_name: Name of parameter changed
        old_value: Previous value
        new_value: New value
        timestamp: When change occurred
        validated: Whether change was validated
    """
    
    equipment_id: str
    parameter_name: str
    old_value: Any
    new_value: Any
    timestamp: datetime = field(default_factory=datetime.now)
    validated: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "equipment_id": self.equipment_id,
            "parameter_name": self.parameter_name,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "timestamp": self.timestamp.isoformat(),
            "validated": self.validated
        }


class EventHandler:
    """
    Manages event callbacks and dispatching.
    
    Supports multiple callbacks per event type with priority ordering.
    """
    
    def __init__(self):
        """Initialize event handler."""
        self._callbacks: Dict[EventType, List[Tuple[int, Callable]]] = {}
        self._global_callbacks: List[Tuple[int, Callable]] = []
        
    def register(
        self,
        event_type: EventType,
        callback: Callable[[InteractionEvent], None],
        priority: int = 0
    ) -> None:
        """
        Register a callback for a specific event type.
        
        Args:
            event_type: Type of event to listen for
            callback: Function to call when event occurs
            priority: Higher priority callbacks execute first
        """
        if event_type not in self._callbacks:
            self._callbacks[event_type] = []
        
        self._callbacks[event_type].append((priority, callback))
        self._callbacks[event_type].sort(key=lambda x: x[0], reverse=True)
        
        logger.debug(f"Registered callback for {event_type.value} with priority {priority}")
    
    def register_global(
        self,
        callback: Callable[[InteractionEvent], None],
        priority: int = 0
    ) -> None:
        """
        Register a global callback that receives all events.
        
        Args:
            callback: Function to call for all events
            priority: Higher priority callbacks execute first
        """
        self._global_callbacks.append((priority, callback))
        self._global_callbacks.sort(key=lambda x: x[0], reverse=True)
        
        logger.debug(f"Registered global callback with priority {priority}")
    
    def unregister(
        self,
        event_type: EventType,
        callback: Callable[[InteractionEvent], None]
    ) -> None:
        """
        Unregister a callback for a specific event type.
        
        Args:
            event_type: Type of event
            callback: Callback to remove
        """
        if event_type in self._callbacks:
            self._callbacks[event_type] = [
                (p, cb) for p, cb in self._callbacks[event_type]
                if cb != callback
            ]
    
    def dispatch(self, event: InteractionEvent) -> None:
        """
        Dispatch an event to all registered callbacks.
        
        Args:
            event: Event to dispatch
        """
        # Call global callbacks first
        for priority, callback in self._global_callbacks:
            if not event.propagate:
                break
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Error in global callback: {e}", exc_info=True)
        
        # Call event-specific callbacks
        if event.event_type in self._callbacks:
            for priority, callback in self._callbacks[event.event_type]:
                if not event.propagate:
                    break
                try:
                    callback(event)
                except Exception as e:
                    logger.error(
                        f"Error in {event.event_type.value} callback: {e}",
                        exc_info=True
                    )
    
    def clear(self, event_type: Optional[EventType] = None) -> None:
        """
        Clear callbacks.
        
        Args:
            event_type: Specific event type to clear, or None for all
        """
        if event_type:
            self._callbacks.pop(event_type, None)
        else:
            self._callbacks.clear()
            self._global_callbacks.clear()


class SelectionManager:
    """
    Manages equipment selection state and operations.
    
    Supports single and multi-select with visual feedback.
    """
    
    def __init__(self):
        """Initialize selection manager."""
        self._selected: Set[str] = set()
        self._last_selected: Optional[str] = None
        self._selection_history: deque = deque(maxlen=50)
        
    @property
    def selected(self) -> Set[str]:
        """Get currently selected equipment IDs."""
        return self._selected.copy()
    
    @property
    def last_selected(self) -> Optional[str]:
        """Get last selected equipment ID."""
        return self._last_selected
    
    def select(self, equipment_id: str, multi: bool = False) -> bool:
        """
        Select equipment.
        
        Args:
            equipment_id: ID of equipment to select
            multi: Whether to add to existing selection
            
        Returns:
            True if selection changed
        """
        if not multi:
            changed = len(self._selected) > 1 or equipment_id not in self._selected
            self._selected.clear()
        else:
            changed = equipment_id not in self._selected
        
        self._selected.add(equipment_id)
        self._last_selected = equipment_id
        
        if changed:
            self._selection_history.append(self._selected.copy())
            logger.debug(f"Selected equipment: {equipment_id} (multi={multi})")
        
        return changed
    
    def deselect(self, equipment_id: str) -> bool:
        """
        Deselect equipment.
        
        Args:
            equipment_id: ID of equipment to deselect
            
        Returns:
            True if selection changed
        """
        if equipment_id in self._selected:
            self._selected.remove(equipment_id)
            if self._last_selected == equipment_id:
                self._last_selected = next(iter(self._selected), None)
            self._selection_history.append(self._selected.copy())
            logger.debug(f"Deselected equipment: {equipment_id}")
            return True
        return False
    
    def toggle(self, equipment_id: str) -> bool:
        """
        Toggle equipment selection.
        
        Args:
            equipment_id: ID of equipment to toggle
            
        Returns:
            True if now selected, False if deselected
        """
        if equipment_id in self._selected:
            self.deselect(equipment_id)
            return False
        else:
            self.select(equipment_id, multi=True)
            return True
    
    def clear(self) -> bool:
        """
        Clear all selections.
        
        Returns:
            True if selection changed
        """
        if self._selected:
            self._selected.clear()
            self._last_selected = None
            self._selection_history.append(set())
            logger.debug("Cleared all selections")
            return True
        return False
    
    def select_all(self, equipment_ids: List[str]) -> bool:
        """
        Select all equipment.
        
        Args:
            equipment_ids: List of all equipment IDs
            
        Returns:
            True if selection changed
        """
        old_count = len(self._selected)
        self._selected = set(equipment_ids)
        self._last_selected = equipment_ids[-1] if equipment_ids else None
        
        if len(self._selected) != old_count:
            self._selection_history.append(self._selected.copy())
            logger.debug(f"Selected all {len(self._selected)} equipment")
            return True
        return False
    
    def is_selected(self, equipment_id: str) -> bool:
        """Check if equipment is selected."""
        return equipment_id in self._selected
    
    def get_selection_count(self) -> int:
        """Get number of selected equipment."""
        return len(self._selected)


class UndoRedoManager:
    """
    Manages undo/redo functionality for parameter changes.
    
    Maintains history of changes with configurable limits.
    """
    
    def __init__(self, max_history: int = 100):
        """
        Initialize undo/redo manager.
        
        Args:
            max_history: Maximum number of changes to track
        """
        self._undo_stack: deque = deque(maxlen=max_history)
        self._redo_stack: deque = deque(maxlen=max_history)
        self._max_history = max_history
        
    def record_change(self, change: ParameterChange) -> None:
        """
        Record a parameter change.
        
        Args:
            change: Parameter change to record
        """
        self._undo_stack.append(change)
        self._redo_stack.clear()  # Clear redo stack on new change
        logger.debug(
            f"Recorded change: {change.equipment_id}.{change.parameter_name} "
            f"{change.old_value} -> {change.new_value}"
        )
    
    def can_undo(self) -> bool:
        """Check if undo is available."""
        return len(self._undo_stack) > 0
    
    def can_redo(self) -> bool:
        """Check if redo is available."""
        return len(self._redo_stack) > 0
    
    def undo(self) -> Optional[ParameterChange]:
        """
        Undo last change.
        
        Returns:
            Parameter change that was undone, or None
        """
        if not self.can_undo():
            return None
        
        change = self._undo_stack.pop()
        self._redo_stack.append(change)
        logger.debug(f"Undo: {change.equipment_id}.{change.parameter_name}")
        return change
    
    def redo(self) -> Optional[ParameterChange]:
        """
        Redo last undone change.
        
        Returns:
            Parameter change that was redone, or None
        """
        if not self.can_redo():
            return None
        
        change = self._redo_stack.pop()
        self._undo_stack.append(change)
        logger.debug(f"Redo: {change.equipment_id}.{change.parameter_name}")
        return change
    
    def clear(self) -> None:
        """Clear all undo/redo history."""
        self._undo_stack.clear()
        self._redo_stack.clear()
        logger.debug("Cleared undo/redo history")
    
    def get_undo_count(self) -> int:
        """Get number of available undo operations."""
        return len(self._undo_stack)
    
    def get_redo_count(self) -> int:
        """Get number of available redo operations."""
        return len(self._redo_stack)


class ClipboardManager:
    """
    Manages copy/paste operations for equipment configurations.
    """
    
    def __init__(self):
        """Initialize clipboard manager."""
        self._clipboard: Optional[Dict[str, Any]] = None
        self._clipboard_type: Optional[str] = None
        
    def copy(self, equipment_data: Dict[str, Any], equipment_type: str) -> None:
        """
        Copy equipment configuration to clipboard.
        
        Args:
            equipment_data: Equipment configuration data
            equipment_type: Type of equipment
        """
        self._clipboard = copy.deepcopy(equipment_data)
        self._clipboard_type = equipment_type
        logger.debug(f"Copied {equipment_type} to clipboard")
    
    def paste(self) -> Optional[Tuple[Dict[str, Any], str]]:
        """
        Paste equipment configuration from clipboard.
        
        Returns:
            Tuple of (equipment_data, equipment_type) or None
        """
        if self._clipboard is None or self._clipboard_type is None:
            return None
        
        logger.debug(f"Pasted {self._clipboard_type} from clipboard")
        return copy.deepcopy(self._clipboard), self._clipboard_type
    
    def has_data(self) -> bool:
        """Check if clipboard has data."""
        return self._clipboard is not None
    
    def clear(self) -> None:
        """Clear clipboard."""
        self._clipboard = None
        self._clipboard_type = None
        logger.debug("Cleared clipboard")


class ValidationEngine:
    """
    Real-time parameter validation engine.
    
    Validates parameter changes against constraints and business rules.
    """
    
    def __init__(self):
        """Initialize validation engine."""
        self._validators: Dict[str, List[Callable]] = {}
        self._constraints: Dict[str, Dict[str, Any]] = {}
        
    def register_validator(
        self,
        parameter_name: str,
        validator: Callable[[Any], Tuple[bool, str]]
    ) -> None:
        """
        Register a validator for a parameter.
        
        Args:
            parameter_name: Name of parameter
            validator: Function that returns (is_valid, error_message)
        """
        if parameter_name not in self._validators:
            self._validators[parameter_name] = []
        self._validators[parameter_name].append(validator)
        logger.debug(f"Registered validator for {parameter_name}")
    
    def set_constraints(
        self,
        parameter_name: str,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        allowed_values: Optional[List[Any]] = None,
        regex: Optional[str] = None
    ) -> None:
        """
        Set constraints for a parameter.
        
        Args:
            parameter_name: Name of parameter
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            allowed_values: List of allowed values
            regex: Regular expression pattern for string validation
        """
        self._constraints[parameter_name] = {
            "min_value": min_value,
            "max_value": max_value,
            "allowed_values": allowed_values,
            "regex": regex
        }
        logger.debug(f"Set constraints for {parameter_name}")
    
    def validate(
        self,
        parameter_name: str,
        value: Any,
        equipment_type: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Validate a parameter value.
        
        Args:
            parameter_name: Name of parameter
            value: Value to validate
            equipment_type: Type of equipment (for context)
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check constraints
        if parameter_name in self._constraints:
            constraints = self._constraints[parameter_name]
            
            if constraints["min_value"] is not None:
                if value < constraints["min_value"]:
                    return False, f"Value must be >= {constraints['min_value']}"
            
            if constraints["max_value"] is not None:
                if value > constraints["max_value"]:
                    return False, f"Value must be <= {constraints['max_value']}"
            
            if constraints["allowed_values"] is not None:
                if value not in constraints["allowed_values"]:
                    return False, f"Value must be one of {constraints['allowed_values']}"
            
            if constraints["regex"] is not None:
                import re
                if not re.match(constraints["regex"], str(value)):
                    return False, f"Value does not match required pattern"
        
        # Run custom validators
        if parameter_name in self._validators:
            for validator in self._validators[parameter_name]:
                is_valid, error_msg = validator(value)
                if not is_valid:
                    return False, error_msg
        
        return True, ""


class InteractionManager:
    """
    Main coordinator for all interaction functionality.
    
    Integrates event handling, selection, undo/redo, clipboard, and validation.
    """
    
    def __init__(self):
        """Initialize interaction manager."""
        self.event_handler = EventHandler()
        self.selection_manager = SelectionManager()
        self.undo_redo_manager = UndoRedoManager()
        self.clipboard_manager = ClipboardManager()
        self.validation_engine = ValidationEngine()
        
        self._mode: InteractionMode = InteractionMode.NORMAL
        self._equipment_data: Dict[str, Dict[str, Any]] = {}
        self._event_history: deque = deque(maxlen=1000)
        self._state_callbacks: List[Callable] = []
        
        # Register internal event handlers
        self._register_internal_handlers()
        
        logger.info("InteractionManager initialized")
    
    def _register_internal_handlers(self) -> None:
        """Register internal event handlers."""
        # Selection events
        self.event_handler.register(
            EventType.CLICK,
            self._handle_click,
            priority=10
        )
        
        self.event_handler.register(
            EventType.DOUBLE_CLICK,
            self._handle_double_click,
            priority=10
        )
        
        # Keyboard shortcuts
        self.event_handler.register(
            EventType.SHORTCUT,
            self._handle_shortcut,
            priority=100
        )
        
        # Parameter changes
        self.event_handler.register(
            EventType.PARAMETER_CHANGE,
            self._handle_parameter_change,
            priority=50
        )
    
    def _handle_click(self, event: InteractionEvent) -> None:
        """Handle click events for selection."""
        if event.equipment_id:
            multi = event.modifiers.get("ctrl", False)
            if self.selection_manager.select(event.equipment_id, multi=multi):
                self._notify_state_change()
    
    def _handle_double_click(self, event: InteractionEvent) -> None:
        """Handle double-click events for editing."""
        if event.equipment_id:
            self._mode = InteractionMode.EDITING
            logger.debug(f"Entering edit mode for {event.equipment_id}")
    
    def _handle_shortcut(self, event: InteractionEvent) -> None:
        """Handle keyboard shortcuts."""
        shortcut = event.data.get("shortcut", "")
        
        if shortcut == "ctrl+z":
            self.undo()
        elif shortcut == "ctrl+y" or shortcut == "ctrl+shift+z":
            self.redo()
        elif shortcut == "ctrl+c":
            self.copy_selected()
        elif shortcut == "ctrl+v":
            self.paste()
        elif shortcut == "ctrl+x":
            self.cut_selected()
        elif shortcut == "delete":
            self.delete_selected()
        elif shortcut == "ctrl+a":
            self.select_all()
        elif shortcut == "escape":
            self.clear_selection()
    
    def _handle_parameter_change(self, event: InteractionEvent) -> None:
        """Handle parameter change events."""
        equipment_id = event.equipment_id
        parameter_name = event.data.get("parameter_name")
        new_value = event.data.get("new_value")
        
        # Type guard: ensure all required values are present
        if not equipment_id or not parameter_name or new_value is None:
            return
        
        # Validate
        equipment_data = self._equipment_data.get(equipment_id, {})
        equipment_type = equipment_data.get("type") if equipment_data else None
        is_valid, error_msg = self.validation_engine.validate(
            parameter_name,
            new_value,
            equipment_type
        )
        
        if not is_valid:
            logger.warning(f"Validation failed: {error_msg}")
            self.emit_event(InteractionEvent(
                event_type=EventType.ERROR,
                equipment_id=equipment_id,
                data={"message": error_msg}
            ))
            return
        
        # Record for undo
        old_value = equipment_data.get(parameter_name) if equipment_data else None
        change = ParameterChange(
            equipment_id=equipment_id,
            parameter_name=parameter_name,
            old_value=old_value,
            new_value=new_value,
            validated=True
        )
        self.undo_redo_manager.record_change(change)
        
        # Apply change
        if equipment_id not in self._equipment_data:
            self._equipment_data[equipment_id] = {}
        self._equipment_data[equipment_id][parameter_name] = new_value
        
        self._notify_state_change()
    
    def _notify_state_change(self) -> None:
        """Notify all state change callbacks."""
        for callback in self._state_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Error in state callback: {e}", exc_info=True)
    
    def register_state_callback(self, callback: Callable[[], None]) -> None:
        """
        Register a callback for state changes.
        
        Args:
            callback: Function to call on state changes
        """
        self._state_callbacks.append(callback)
    
    def emit_event(self, event: InteractionEvent) -> None:
        """
        Emit an event to all handlers.
        
        Args:
            event: Event to emit
        """
        self._event_history.append(event)
        self.event_handler.dispatch(event)
    
    def set_mode(self, mode: InteractionMode) -> None:
        """
        Set interaction mode.
        
        Args:
            mode: New interaction mode
        """
        old_mode = self._mode
        self._mode = mode
        logger.debug(f"Mode changed: {old_mode.value} -> {mode.value}")
    
    def get_mode(self) -> InteractionMode:
        """Get current interaction mode."""
        return self._mode
    
    def update_equipment_data(
        self,
        equipment_id: str,
        data: Dict[str, Any]
    ) -> None:
        """
        Update equipment data.
        
        Args:
            equipment_id: ID of equipment
            data: Equipment data
        """
        self._equipment_data[equipment_id] = data
    
    def get_equipment_data(self, equipment_id: str) -> Optional[Dict[str, Any]]:
        """
        Get equipment data.
        
        Args:
            equipment_id: ID of equipment
            
        Returns:
            Equipment data or None
        """
        return self._equipment_data.get(equipment_id)
    
    def undo(self) -> bool:
        """
        Undo last parameter change.
        
        Returns:
            True if undo was performed
        """
        change = self.undo_redo_manager.undo()
        if change:
            # Revert the change
            if change.equipment_id in self._equipment_data:
                self._equipment_data[change.equipment_id][change.parameter_name] = change.old_value
            
            self.emit_event(InteractionEvent(
                event_type=EventType.UNDO,
                equipment_id=change.equipment_id,
                data=change.to_dict()
            ))
            self._notify_state_change()
            return True
        return False
    
    def redo(self) -> bool:
        """
        Redo last undone change.
        
        Returns:
            True if redo was performed
        """
        change = self.undo_redo_manager.redo()
        if change:
            # Reapply the change
            if change.equipment_id in self._equipment_data:
                self._equipment_data[change.equipment_id][change.parameter_name] = change.new_value
            
            self.emit_event(InteractionEvent(
                event_type=EventType.REDO,
                equipment_id=change.equipment_id,
                data=change.to_dict()
            ))
            self._notify_state_change()
            return True
        return False
    
    def copy_selected(self) -> bool:
        """
        Copy selected equipment to clipboard.
        
        Returns:
            True if copy was performed
        """
        selected = self.selection_manager.selected
        if not selected:
            return False
        
        # Copy first selected equipment
        equipment_id = next(iter(selected))
        equipment_data = self._equipment_data.get(equipment_id)
        
        if equipment_data:
            equipment_type = equipment_data.get("type", "unknown")
            self.clipboard_manager.copy(equipment_data, equipment_type)
            
            self.emit_event(InteractionEvent(
                event_type=EventType.COPY,
                equipment_id=equipment_id
            ))
            return True
        return False
    
    def paste(self) -> bool:
        """
        Paste equipment from clipboard.
        
        Returns:
            True if paste was performed
        """
        clipboard_data = self.clipboard_manager.paste()
        if not clipboard_data:
            return False
        
        equipment_data, equipment_type = clipboard_data
        
        self.emit_event(InteractionEvent(
            event_type=EventType.PASTE,
            data={
                "equipment_data": equipment_data,
                "equipment_type": equipment_type
            }
        ))
        return True
    
    def cut_selected(self) -> bool:
        """
        Cut selected equipment to clipboard.
        
        Returns:
            True if cut was performed
        """
        if self.copy_selected():
            self.delete_selected()
            return True
        return False
    
    def delete_selected(self) -> bool:
        """
        Delete selected equipment.
        
        Returns:
            True if delete was performed
        """
        selected = self.selection_manager.selected
        if not selected:
            return False
        
        for equipment_id in selected:
            self.emit_event(InteractionEvent(
                event_type=EventType.EQUIPMENT_DELETE,
                equipment_id=equipment_id
            ))
            self._equipment_data.pop(equipment_id, None)
        
        self.selection_manager.clear()
        self._notify_state_change()
        return True
    
    def select_all(self) -> bool:
        """
        Select all equipment.
        
        Returns:
            True if selection changed
        """
        equipment_ids = list(self._equipment_data.keys())
        return self.selection_manager.select_all(equipment_ids)
    
    def clear_selection(self) -> bool:
        """
        Clear all selections.
        
        Returns:
            True if selection changed
        """
        return self.selection_manager.clear()
    
    def get_state(self) -> Dict[str, Any]:
        """
        Get current interaction state.
        
        Returns:
            Dictionary with current state
        """
        return {
            "mode": self._mode.value,
            "selected": list(self.selection_manager.selected),
            "can_undo": self.undo_redo_manager.can_undo(),
            "can_redo": self.undo_redo_manager.can_redo(),
            "has_clipboard": self.clipboard_manager.has_data(),
            "equipment_count": len(self._equipment_data)
        }
    
    def reset(self) -> None:
        """Reset interaction manager to initial state."""
        self.selection_manager.clear()
        self.undo_redo_manager.clear()
        self.clipboard_manager.clear()
        self._mode = InteractionMode.NORMAL
        self._equipment_data.clear()
        self._event_history.clear()
        logger.info("InteractionManager reset")


class StreamlitIntegration:
    """
    Helper class for integrating with Streamlit's session state.
    
    Handles state persistence across reruns and provides Streamlit-specific
    event handling.
    """
    
    @staticmethod
    def initialize_session_state(st_session_state: Any) -> InteractionManager:
        """
        Initialize or retrieve interaction manager from session state.
        
        Args:
            st_session_state: Streamlit session state object
            
        Returns:
            InteractionManager instance
        """
        if "interaction_manager" not in st_session_state:
            st_session_state.interaction_manager = InteractionManager()
            logger.info("Created new InteractionManager in session state")
        
        return st_session_state.interaction_manager
    
    @staticmethod
    def handle_rerun(
        manager: InteractionManager,
        st_session_state: Any
    ) -> None:
        """
        Handle Streamlit rerun by syncing state.
        
        Args:
            manager: InteractionManager instance
            st_session_state: Streamlit session state object
        """
        # Sync state to session
        st_session_state.interaction_state = manager.get_state()
    
    @staticmethod
    def create_event_from_widget(
        widget_key: str,
        widget_value: Any,
        event_type: EventType,
        st_session_state: Any
    ) -> InteractionEvent:
        """
        Create an event from a Streamlit widget interaction.
        
        Args:
            widget_key: Key of the widget
            widget_value: Current value of the widget
            event_type: Type of event
            st_session_state: Streamlit session state object
            
        Returns:
            InteractionEvent instance
        """
        return InteractionEvent(
            event_type=event_type,
            data={
                "widget_key": widget_key,
                "widget_value": widget_value,
                "session_id": id(st_session_state)
            }
        )


# Example usage and testing
if __name__ == "__main__":
    # Configure logging for testing
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create interaction manager
    manager = InteractionManager()
    
    # Register some validators
    manager.validation_engine.set_constraints(
        "pressure",
        min_value=0,
        max_value=1000
    )
    
    manager.validation_engine.set_constraints(
        "temperature",
        min_value=-50,
        max_value=500
    )
    
    # Register event handlers
    def on_selection_change(event: InteractionEvent):
        print(f"Selection changed: {event.equipment_id}")
    
    manager.event_handler.register(EventType.SELECT, on_selection_change)
    
    # Simulate some interactions
    print("\n=== Testing Equipment Selection ===")
    manager.emit_event(InteractionEvent(
        event_type=EventType.CLICK,
        equipment_id="pump_001"
    ))
    
    print(f"Selected: {manager.selection_manager.selected}")
    
    print("\n=== Testing Parameter Change ===")
    manager.update_equipment_data("pump_001", {"type": "pump", "pressure": 100})
    
    manager.emit_event(InteractionEvent(
        event_type=EventType.PARAMETER_CHANGE,
        equipment_id="pump_001",
        data={
            "parameter_name": "pressure",
            "new_value": 150
        }
    ))
    
    print(f"Equipment data: {manager.get_equipment_data('pump_001')}")
    
    print("\n=== Testing Undo/Redo ===")
    print(f"Can undo: {manager.undo_redo_manager.can_undo()}")
    manager.undo()
    print(f"After undo: {manager.get_equipment_data('pump_001')}")
    
    manager.redo()
    print(f"After redo: {manager.get_equipment_data('pump_001')}")
    
    print("\n=== Testing Copy/Paste ===")
    manager.copy_selected()
    print(f"Has clipboard data: {manager.clipboard_manager.has_data()}")
    
    print("\n=== Current State ===")
    print(json.dumps(manager.get_state(), indent=2))
    
    print("\n=== Interactive Event System Test Complete ===")