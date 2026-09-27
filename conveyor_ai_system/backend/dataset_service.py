"""Dataset Service for Conveyor Belt AI System.
Loads the final CSV dataset (synthetic_motor_fault_dataset.csv), extracts metadata,
dynamically identifies condition classes and counts, and provides clean row-by-row
data extraction with strict target/ID isolation.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

from .config import (
    DATASET_PATH,
    TARGET_COLUMN,
    ID_COLUMN,
    OPERATING_HOURS_COLUMN,
    CLASS_DISPLAY_NAMES
)

logger = logging.getLogger("conveyor_ai.dataset_service")


class DatasetService:
    def __init__(self, dataset_path: Path = DATASET_PATH):
        self.dataset_path = dataset_path
        self.df: Optional[pd.DataFrame] = None
        self.total_rows: int = 0
        self.columns: List[str] = []
        self.feature_columns: List[str] = []
        self.detected_classes: List[str] = []
        self.class_counts: Dict[str, int] = {}
        self.is_loaded: bool = False
        self.load_error: Optional[str] = None

        self.load_dataset()

    def load_dataset(self) -> bool:
        """Load CSV dataset from disk and compute dynamic metadata."""
        try:
            if not self.dataset_path.exists():
                raise FileNotFoundError(f"Dataset CSV not found at: {self.dataset_path}")

            logger.info(f"Loading dataset from: {self.dataset_path}")
            self.df = pd.read_csv(self.dataset_path)
            self.total_rows = len(self.df)
            self.columns = list(self.df.columns)

            if TARGET_COLUMN not in self.columns:
                raise ValueError(f"Target column '{TARGET_COLUMN}' not found in dataset columns: {self.columns}")

            # Identify model feature columns (exclude ID and Belt_Condition)
            self.feature_columns = [
                col for col in self.columns
                if col not in [ID_COLUMN, TARGET_COLUMN]
            ]

            # Dynamically extract classes from actual target column
            unique_classes = self.df[TARGET_COLUMN].dropna().unique().tolist()
            # Preserve deterministic sorted order
            self.detected_classes = sorted([str(c).strip() for c in unique_classes])

            # Dynamically count samples per class from the CSV
            raw_counts = self.df[TARGET_COLUMN].value_counts().to_dict()
            self.class_counts = {str(k).strip(): int(v) for k, v in raw_counts.items()}

            self.is_loaded = True
            self.load_error = None
            logger.info(
                f"Successfully loaded {self.dataset_path.name}: "
                f"{self.total_rows} rows, {len(self.columns)} columns, "
                f"classes detected: {self.detected_classes}, counts: {self.class_counts}"
            )
            return True

        except Exception as e:
            self.is_loaded = False
            self.load_error = str(e)
            logger.error(f"Failed to load dataset: {e}", exc_info=True)
            return False

    def get_row(self, row_idx: int) -> Tuple[Dict[str, Any], str, int, float]:
        """Extract a single row by 1-indexed row number.
        Returns:
            features_dict: Dict of sensor features (WITHOUT Belt_Condition or ID)
            actual_condition: Ground truth Belt_Condition string
            row_id: ID from row
            operating_hours: Operating_Hours value
        """
        if not self.is_loaded or self.df is None:
            raise RuntimeError(f"Dataset is not loaded. Error: {self.load_error}")

        if row_idx < 1 or row_idx > self.total_rows:
            raise IndexError(f"Row {row_idx} is out of bounds (1 to {self.total_rows}).")

        # 0-indexed row extraction
        row = self.df.iloc[row_idx - 1]

        # 1. Save actual condition (Belt_Condition)
        actual_condition = str(row[TARGET_COLUMN]).strip()

        # 2. Extract ID
        row_id = int(row.get(ID_COLUMN, row_idx))

        # 3. Extract Operating Hours
        operating_hours = float(row.get(OPERATING_HOURS_COLUMN, 0.0))

        # 4. Extract only model features (drop Belt_Condition and ID)
        features_dict = {}
        for col in self.feature_columns:
            if col in row:
                features_dict[col] = float(row[col])

        return features_dict, actual_condition, row_id, operating_hours

    def get_info(self) -> Dict[str, Any]:
        """Return dataset metadata, dynamically detected classes, and counts."""
        if not self.is_loaded or self.df is None:
            return {
                "loaded": False,
                "error": self.load_error or "Dataset not loaded",
                "filename": self.dataset_path.name if self.dataset_path else "unknown"
            }

        # Format condition display info
        condition_info = []
        for cls in self.detected_classes:
            display_title = CLASS_DISPLAY_NAMES.get(cls, cls.upper())
            count = self.class_counts.get(cls, 0)
            condition_info.append({
                "raw_label": cls,
                "display_name": display_title,
                "sample_count": count
            })

        return {
            "loaded": True,
            "filename": self.dataset_path.name,
            "filepath": str(self.dataset_path),
            "total_rows": self.total_rows,
            "total_columns": len(self.columns),
            "target_column": TARGET_COLUMN,
            "id_column": ID_COLUMN,
            "operating_hours_column": OPERATING_HOURS_COLUMN,
            "columns": self.columns,
            "feature_columns": self.feature_columns,
            "detected_classes": self.detected_classes,
            "class_counts": self.class_counts,
            "conditions": condition_info,
            "active_mode_label": "DATASET SIMULATION ACTIVE",
            "disclaimer": "DATASET SIMULATION ACTIVE: synthetic_motor_fault_dataset.csv (2000 Samples)"
        }


# Singleton instance
dataset_service = DatasetService()
