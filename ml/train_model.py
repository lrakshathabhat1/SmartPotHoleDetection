"""
Machine Learning Training Pipeline for Road Quality Monitor
Trains a Random Forest Classifier on preprocessed sensor features to identify:
- Class 0: Normal Road
- Class 1: Speed Breaker
- Class 2: Pothole

Outputs:
- ml/model/road_classifier.joblib
- ml/model/scaler.joblib
- ml/model/model_metadata.json
"""

import sys
import json
import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix
)

import config
from backend.preprocessing import FEATURE_COLUMNS


def train():
    print("=" * 65)
    print("Road Quality Monitor - Machine Learning Model Training")
    print("=" * 65)

    csv_path = Path(config.SAMPLE_DATASET_PATH)
    if not csv_path.exists():
        print(f"[ERROR] Sample dataset not found at {csv_path}. Generating it first...")
        from ml.generate_dataset import generate_synthetic_dataset
        generate_synthetic_dataset()

    print(f"[INFO] Loading dataset from: {csv_path}")
    df = pd.read_csv(csv_path)
    print(f"[INFO] Total dataset records: {len(df)}")
    print(f"[INFO] Class distribution:\n{df['label'].value_counts().to_string()}\n")

    # Features and Targets
    X = df[FEATURE_COLUMNS].values
    y = df["class_id"].values

    # Train / Test Split (80% train, 20% test, stratified)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )
    print(f"[INFO] Training samples: {len(X_train)} | Testing samples: {len(X_test)}")

    # Feature Scaling
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Random Forest Classifier
    rf = RandomForestClassifier(
        n_estimators=100,
        max_depth=8,
        min_samples_split=4,
        min_samples_leaf=2,
        random_state=42,
        class_weight="balanced"
    )

    print("[INFO] Training Random Forest model...")
    rf.fit(X_train_scaled, y_train)

    # Evaluate
    y_pred = rf.predict(X_test_scaled)
    acc = accuracy_score(y_test, y_pred)
    prec_macro = precision_score(y_test, y_pred, average="macro", zero_division=0)
    rec_macro = recall_score(y_test, y_pred, average="macro", zero_division=0)
    f1_macro = f1_score(y_test, y_pred, average="macro", zero_division=0)
    cm = confusion_matrix(y_test, y_pred).tolist()
    report = classification_report(
        y_test,
        y_pred,
        target_names=["Normal Road", "Speed Breaker", "Pothole"],
        digits=4
    )

    print("\n" + "=" * 65)
    print("MODEL EVALUATION RESULTS (Test Set)")
    print("=" * 65)
    print(f"Accuracy:  {acc * 100:.2f}%")
    print(f"Precision: {prec_macro * 100:.2f}%")
    print(f"Recall:    {rec_macro * 100:.2f}%")
    print(f"F1 Score:  {f1_macro * 100:.2f}%")
    print("\nClassification Report:\n" + report)
    print("Confusion Matrix:\n" + str(np.array(cm)))
    print("=" * 65)

    # Feature Importances
    importances = {col: round(float(imp), 4) for col, imp in zip(FEATURE_COLUMNS, rf.feature_importances_)}
    print(f"[INFO] Feature Importances: {importances}")

    # Save artifacts
    model_dir = Path(config.MODEL_PATH).parent
    model_dir.mkdir(parents=True, exist_ok=True)

    joblib.dump(rf, config.MODEL_PATH)
    joblib.dump(scaler, config.SCALER_PATH)

    metadata = {
        "model_type": "RandomForestClassifier",
        "n_estimators": 100,
        "features": FEATURE_COLUMNS,
        "classes": config.LABEL_MAPPING,
        "metrics": {
            "test_accuracy": round(float(acc), 4),
            "test_precision_macro": round(float(prec_macro), 4),
            "test_recall_macro": round(float(rec_macro), 4),
            "test_f1_macro": round(float(f1_macro), 4),
            "confusion_matrix": cm
        },
        "feature_importances": importances,
        "trained_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "disclaimer": "Trained on synthetic demonstration data representing simulated physical kinematics. Not calibrated for official municipal paving standards."
    }

    with open(config.METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4)

    print(f"\n[SUCCESS] Model saved to: {config.MODEL_PATH}")
    print(f"[SUCCESS] Scaler saved to: {config.SCALER_PATH}")
    print(f"[SUCCESS] Metadata saved to: {config.METADATA_PATH}")
    print("=" * 65)
    return metadata


if __name__ == "__main__":
    train()
