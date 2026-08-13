# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.156.0 | Date: 2026-08-09

import os
import tempfile
from pathlib import Path

from agentiot.app import DEFAULT_DB_PATH


def test_default_development_database_uses_process_local_temp_storage() -> None:
    path = Path(DEFAULT_DB_PATH)

    assert path.parent == Path(tempfile.gettempdir())
    assert path.name.startswith("agentiot-greenovax-development-")
    assert path.name.endswith(f"-{os.getpid()}.db")
    assert os.access(path.parent, os.W_OK)
