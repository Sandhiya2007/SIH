"""Model Service for XGBoost Conveyor Fault & Damage Detection.
Loads model artifacts once at startup, performs strict feature validation,
and generates condition predictions and probability distributions.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder

from .config import MODEL_PATH, LABEL_ENCODER_PATH, TARGET_COLUMN, ID_COLUMN

logger = logging.getLogger("conveyor_ai.model_service")


class ModelService:
    def __init__(self, model_path: Path = MODEL_PATH, encoder_path: Path = LABEL_ENCODER_PATH):
        self.model_path = model_path
        self.encoder_path = encoder_path
        self.model: Optional[Any] = None
        self.label_encoder: Optional[LabelEncoder] = None
        self.feature_columns: List[str] = []
        self.classes: List[str] = []
        self.is_loaded: bool = False
        self.load_error: Optional[str] = None

        self.load_artifacts()

    def load_artifacts(self) -> bool:
        """Load trained XGBoost model and LabelEncoder from disk once.
        DOES NOT retrain or modify the trained model.
        """
        try:
            if not self.model_path.exists():
                raise FileNotFoundError(f"Model file not found at: {self.model_path}")
            if not self.encoder_path.exists():
                raise FileNotFoundError(f"Label encoder not found at: {self.encoder_path}")

            logger.info(f"Loading model artifact from: {self.model_path}")
            raw_model_artifact = joblib.load(self.model_path)

            if isinstance(raw_model_artifact, dict) and "model" in raw_model_artifact:
                self.model = raw_model_artifact["model"]
                self.feature_columns = list(raw_model_artifact.get("feature_columns", []))
                if "classes" in raw_model_artifact:
                    self.classes = list(raw_model_artifact["classes"])
            else:
                self.model = raw_model_artifact
                if hasattr(self.model, "feature_names_in_"):
                    self.feature_columns = list(self.model.feature_names_in_)

            logger.info(f"Loading label encoder from: {self.encoder_path}")
            self.label_encoder = joblib.load(self.encoder_path)
            if hasattr(self.label_encoder, "classes_"):
                self.classes = [str(c).strip() for c in self.label_encoder.classes_]

            if not self.feature_columns and hasattr(self.model, "feature_names_in_"):
                self.feature_columns = list(self.model.feature_names_in_)

            self.is_loaded = True
            self.load_error = None
            logger.info(
                f"Successfully loaded XGBoost model: {len(self.feature_columns)} features, "
                f"classes: {self.classes}"
            )
            return True

        except Exception as e:
            self.is_loaded = False
            self.load_error = str(e)
            logger.error(f"Failed to load model artifacts: {e}", exc_info=True)
            return False

    def validate_features(self, input_data: Union[Dict[str, Any], pd.DataFrame, pd.Series]) -> pd.DataFrame:
        """Validate input features against exact trained feature set.
        Requirements (from Section 21):
        1. Load the model's expected features.
        2. Check incoming columns.
        3. Remove target column (Belt_Condition).
        4. Remove ID if it was not used during training.
        5. Check missing features. If missing: Return 'FEATURE ERROR: Missing feature: <feature name>'.
           Do not silently invent values.
        6. Check unexpected features.
        7. Reorder features exactly.
        8. Pass the correct feature order to XGBoost as numeric float64.
        """
        if not self.is_loaded or self.model is None:
            raise RuntimeError(f"FEATURE ERROR: Model is not loaded ({self.load_error})")

        if not self.feature_columns:
            raise RuntimeError("FEATURE ERROR: Model feature columns metadata is empty.")

        # Convert to DataFrame
        if isinstance(input_data, dict):
            df = pd.DataFrame([input_data])
        elif isinstance(input_data, pd.Series):
            df = input_data.to_frame().T
        elif isinstance(input_data, pd.DataFrame):
            df = input_data.copy()
        else:
            raise TypeError(f"FEATURE ERROR: Expected dict, Series, or DataFrame, got {type(input_data).__name__}")

        # 3. Remove target column (Belt_Condition)
        columns_to_drop = [
            c for c in [TARGET_COLUMN, TARGET_COLUMN.lower(), "Label", "label"]
            if c in df.columns
        ]
        # 4. Remove ID if not used during training
        if ID_COLUMN in df.columns and ID_COLUMN not in self.feature_columns:
            columns_to_drop.append(ID_COLUMN)
        if "id" in df.columns and "id" not in self.feature_columns:
            columns_to_drop.append("id")
        if "Timestamp" in df.columns and "Timestamp" not in self.feature_columns:
            columns_to_drop.append("Timestamp")
        if "timestamp" in df.columns and "timestamp" not in self.feature_columns:
            columns_to_drop.append("timestamp")

        if columns_to_drop:
            df = df.drop(columns=columns_to_drop)

        # 5. Check missing features
        missing_features = [col for col in self.feature_columns if col not in df.columns]
        if missing_features:
            err_msg = f"FEATURE ERROR: Missing feature: {missing_features[0]}"
            logger.error(err_msg)
            raise ValueError(err_msg)

        # 6 & 7. Reorder features exactly to match training order
        ordered_df = df[self.feature_columns].copy()

        # 8. Enforce numeric float64
        try:
            ordered_df = ordered_df.astype(np.float64)
        except Exception as e:
            err_msg = f"FEATURE ERROR: Non-numeric feature values present: {e}"
            logger.error(err_msg)
            raise ValueError(err_msg)

        if ordered_df.isna().any().any():
            nan_cols = ordered_df.columns[ordered_df.isna().any()].tolist()
            err_msg = f"FEATURE ERROR: Features contain NaN values: {nan_cols}"
            logger.error(err_msg)
            raise ValueError(err_msg)

        return ordered_df

    def predict(self, input_data: Union[Dict[str, Any], pd.DataFrame, pd.Series]) -> Dict[str, Any]:
        """Perform inference using the loaded XGBoost model.
        Returns prediction label, index, confidence, and full probability distribution.
        """
        valid_df = self.validate_features(input_data)

        try:
            pred_indices = self.model.predict(valid_df)
            pred_idx = int(pred_indices[0])

            # Get class probabilities from predict_proba
            if hasattr(self.model, "predict_proba"):
                probs = self.model.predict_proba(valid_df)[0]
                confidence = float(probs[pred_idx])
            else:
                probs = np.zeros(len(self.classes))
                probs[pred_idx] = 1.0
                confidence = 1.0

            # Decode class label
            if self.label_encoder and hasattr(self.label_encoder, "inverse_transform"):
                label_name = str(self.label_encoder.inverse_transform([pred_idx])[0]).strip()
            elif 0 <= pred_idx < len(self.classes):
                label_name = self.classes[pred_idx].strip()
            else:
                label_name = f"Class_{pred_idx}"

            # Format probability distribution
            probabilities = {}
            for i, class_name in enumerate(self.classes):
                if i < len(probs):
                    probabilities[class_name] = float(probs[i])
                else:
                    probabilities[class_name] = 0.0

            return {
                "prediction": label_name,
                "prediction_index": pred_idx,
                "confidence": confidence,
                "probabilities": probabilities
            }

        except Exception as e:
            logger.error(f"Inference error during model prediction: {e}", exc_info=True)
            raise RuntimeError(f"Prediction failed: {e}")


# Singleton instance
model_service = ModelService()
