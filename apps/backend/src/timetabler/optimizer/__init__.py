"""Pure timetable optimization domain and solver entry points.

The API and job worker own transport and persistence.  This package accepts an
already-normalized, immutable problem and returns deterministic candidates.
"""

from .cp_sat import CpSatOptimizer
from .models import (
    Candidate,
    ObjectiveWeights,
    OptimizationRequest,
    OptimizationResult,
    Preferences,
    RequiredGroup,
    ScoreBreakdown,
    Section,
    Session,
    SolverStatus,
)
from .reference import BacktrackingOptimizer

__all__ = [
    "BacktrackingOptimizer",
    "Candidate",
    "CpSatOptimizer",
    "ObjectiveWeights",
    "OptimizationRequest",
    "OptimizationResult",
    "Preferences",
    "RequiredGroup",
    "ScoreBreakdown",
    "Section",
    "Session",
    "SolverStatus",
]
