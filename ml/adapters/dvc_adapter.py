"""
DVC (Data Version Control) Adapter Stub — PHASE 11.

Status: PLANNED
Install: pip install dvc

This module provides an abstraction over DVC CLI/API for tracking large video clips,
raw frames, and model weight artifacts without committing them directly into Git.
"""

from __future__ import annotations

import logging
import subprocess
from typing import List, Optional

logger = logging.getLogger(__name__)


class DVCAdapter:
    """
    Thin adapter for DVC integration in IBVAP.
    Allows versioning datasets and model files independently of Git history.
    """

    def __init__(self, repo_dir: str = "."):
        self.repo_dir = repo_dir
        self._available = self._check_dvc_installed()

    def _check_dvc_installed(self) -> bool:
        try:
            res = subprocess.run(
                ["dvc", "--version"],
                capture_output=True,
                text=True,
                check=False,
            )
            return res.returncode == 0
        except FileNotFoundError:
            logger.info("DVC command not found on PATH. Data versioning remains in stub mode.")
            return False

    @property
    def is_available(self) -> bool:
        return self._available

    def track_file(self, target_path: str) -> bool:
        """Runs `dvc add <target_path>`."""
        if not self._available:
            logger.warning("DVC not available: skipping tracking for %s", target_path)
            return False
        try:
            res = subprocess.run(
                ["dvc", "add", target_path],
                cwd=self.repo_dir,
                capture_output=True,
                text=True,
                check=False,
            )
            return res.returncode == 0
        except Exception as e:
            logger.error("Failed to execute dvc add: %s", e)
            return False

    def push(self, remote: Optional[str] = None) -> bool:
        """Runs `dvc push`."""
        if not self._available:
            return False
        cmd = ["dvc", "push"]
        if remote:
            cmd.extend(["-r", remote])
        try:
            res = subprocess.run(
                cmd,
                cwd=self.repo_dir,
                capture_output=True,
                text=True,
                check=False,
            )
            return res.returncode == 0
        except Exception as e:
            logger.error("Failed to execute dvc push: %s", e)
            return False
