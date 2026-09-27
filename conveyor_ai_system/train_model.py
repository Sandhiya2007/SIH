"""
train_model.py
---------------
Trains an XGBoost multi-class classifier on the motor fault dataset
(synthetic_motor_fault_dataset.csv) and saves everything needed for
later inference on the Raspberry Pi 5:

    model_output/
        xgb_motor_fault_model.json   <- trained XGBoost model
        label_encoder.pkl            <- maps class index <-> fault name
        feature_columns.pkl          <- exact feature order the model expects
        confusion_matrix.png         <- evaluation plot
        feature_importance.png       <- evaluation plot
        classification_report.txt    <- precision/recall/F1 per class

Run:
    python3 train_model.py --data synthetic_motor_fault_dataset.csv
"""

import argparse
import os
import pickle

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # no display needed on a headless Pi
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    ConfusionMatrixDisplay,
)
import xgboost as xgb


# Columns that are identifiers/labels, not model inputs
NON_FEATURE_COLS = ["ID", "Belt_Condition"]


def load_data(csv_path: str):
    df = pd.read_csv(csv_path)
    missing = [c for c in ["Belt_Condition"] if c not in df.columns]
    if missing:
        raise ValueError(f"Dataset is missing required column(s): {missing}")

    feature_cols = [c for c in df.columns if c not in NON_FEATURE_COLS]
    X = df[feature_cols].copy()
    y_raw = df["Belt_Condition"].copy()

    if X.isna().any().any():
        n_bad = X.isna().any(axis=1).sum()
        print(f"[warn] Dropping {n_bad} rows with missing values")
        keep = ~X.isna().any(axis=1)
        X, y_raw = X[keep], y_raw[keep]

    return X, y_raw, feature_cols


def train(args):
    os.makedirs(args.out_dir, exist_ok=True)

    print(f"[1/6] Loading dataset from {args.data} ...")
    X, y_raw, feature_cols = load_data(args.data)
    print(f"      {X.shape[0]} rows, {X.shape[1]} features, "
          f"{y_raw.nunique()} classes: {sorted(y_raw.unique())}")

    print("[2/6] Encoding labels ...")
    le = LabelEncoder()
    y = le.fit_transform(y_raw)

    print("[3/6] Splitting train/test (stratified, "
          f"{int(args.test_size * 100)}% held out) ...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=args.test_size, random_state=args.seed, stratify=y
    )

    print("[4/6] Training XGBoost classifier ...")
    model = xgb.XGBClassifier(
        n_estimators=args.n_estimators,
        max_depth=args.max_depth,
        learning_rate=args.learning_rate,
        subsample=0.9,
        colsample_bytree=0.9,
        objective="multi:softprob",
        num_class=len(le.classes_),
        eval_metric="mlogloss",
        random_state=args.seed,
        n_jobs=-1,
    )
    model.fit(
        X_train,
        y_train,
        eval_set=[(X_train, y_train), (X_test, y_test)],
        verbose=False,
    )

    print("[5/6] Evaluating on held-out test set ...")
    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    report = classification_report(y_test, y_pred, target_names=le.classes_)
    print(f"      Test accuracy: {acc * 100:.2f}%\n")
    print(report)

    report_path = os.path.join(args.out_dir, "classification_report.txt")
    with open(report_path, "w") as f:
        f.write(f"Test accuracy: {acc * 100:.2f}%\n\n")
        f.write(report)

    # Confusion matrix plot
    cm = confusion_matrix(y_test, y_pred)
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=le.classes_)
    fig, ax = plt.subplots(figsize=(6, 6))
    disp.plot(ax=ax, cmap="Blues", colorbar=False, xticks_rotation=30)
    ax.set_title("Confusion Matrix - Motor Fault Classification")
    fig.tight_layout()
    fig.savefig(os.path.join(args.out_dir, "confusion_matrix.png"), dpi=150)
    plt.close(fig)

    # Feature importance plot
    importances = model.feature_importances_
    order = np.argsort(importances)[::-1]
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.barh(
        [feature_cols[i] for i in order][::-1],
        [importances[i] for i in order][::-1],
        color="#3b6fa0",
    )
    ax.set_xlabel("Importance")
    ax.set_title("XGBoost Feature Importance")
    fig.tight_layout()
    fig.savefig(os.path.join(args.out_dir, "feature_importance.png"), dpi=150)
    plt.close(fig)

    print("[6/6] Saving model artifacts ...")
    model.save_model(os.path.join(args.out_dir, "xgb_motor_fault_model.json"))

    with open(os.path.join(args.out_dir, "label_encoder.pkl"), "wb") as f:
        pickle.dump(le, f)

    with open(os.path.join(args.out_dir, "feature_columns.pkl"), "wb") as f:
        pickle.dump(feature_cols, f)

    print(f"\nDone. All artifacts saved in: {os.path.abspath(args.out_dir)}")
    print("Files written:")
    for fname in sorted(os.listdir(args.out_dir)):
        print(f"  - {fname}")


def parse_args():
    p = argparse.ArgumentParser(description="Train XGBoost motor fault classifier")
    p.add_argument("--data", default="synthetic_motor_fault_dataset.csv",
                    help="Path to the training CSV")
    p.add_argument("--out-dir", default="model_output",
                    help="Directory to save the trained model and reports")
    p.add_argument("--test-size", type=float, default=0.2,
                    help="Fraction of data held out for testing")
    p.add_argument("--n-estimators", type=int, default=300)
    p.add_argument("--max-depth", type=int, default=6)
    p.add_argument("--learning-rate", type=float, default=0.1)
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


if __name__ == "__main__":
    train(parse_args())
