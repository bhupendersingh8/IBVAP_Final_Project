"""
IBVAP Continuous Learning and Automated Self-Training Subsystem.
Provides Auto-Curator, Continuous Training Engine, and Validation Gates.
"""
from .auto_curator import AutoCurator
from .auto_trainer import AutoTrainer, ContinuousLearningConfig

__all__ = ["AutoCurator", "AutoTrainer", "ContinuousLearningConfig"]
