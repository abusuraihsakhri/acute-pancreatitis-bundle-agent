"""
Root Test Runner for Acute Pancreatitis Severity & Bundle Care Engine.
"""

import sys
import unittest
from pathlib import Path

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).parent))

from tests.test_pancreas_guard import (
    TestBISAPCalculator,
    TestModifiedMarshallCalculator,
    TestRevisedAtlantaClassification,
    TestRansonAndCTSICalculators,
    TestFluidAndBundleGuidelines,
    TestCLIAndBatchExecution,
)

if __name__ == "__main__":
    unittest.main()
