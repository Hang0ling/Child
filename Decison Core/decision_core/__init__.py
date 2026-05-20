"""Decision Core MVP.

The package turns episode state into a validated Execution Brief through:
control flow decision -> normalized context -> strategy/memory composition ->
brief plan -> validation/repair -> template rendering.
"""

from .orchestrator import DecisionCoreOrchestrator

__all__ = ["DecisionCoreOrchestrator"]
