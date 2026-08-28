"""Evaluate a trained YOLO detector on the held-out MobilTelesco test split."""

from __future__ import annotations

import argparse
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lib.io_utils import configure_utf8_console, read_json, write_csv, write_json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = PROJECT_ROOT / "data" / "processed" / "yolo_mobiltelesco_8" / "dataset.yaml"
DEFAULT_WEIGHTS = (
    PROJECT_ROOT
    / "data"
    / "results"
    / "yolo_training"
    / "mobiltelesco8_yolo11n"
    / "weights"
    / "best.pt"
)
DEFAULT_PROJECT = PROJECT_ROOT / "data" / "results" / "yolo_evaluation"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weights", type=Path, default=DEFAULT_WEIGHTS)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--split", choices=("val", "test"), default="test")
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=2)
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--device", default="auto", help="auto, cpu, or CUDA index such as 0")
    parser.add_argument("--conf", type=float, default=0.001, help="Confidence used for metric calculation")
    parser.add_argument("--iou", type=float, default=0.60, help="NMS IoU threshold")
    parser.add_argument("--project", type=Path, default=DEFAULT_PROJECT)
    parser.add_argument("--name", default="mobiltelesco8_yolo11n_test")
    return parser.parse_args()


def as_list(value: Any) -> list[float]:
    if value is None:
        return []
    if hasattr(value, "tolist"):
        value = value.tolist()
    if isinstance(value, (int, float)):
        return [float(value)]
    return [float(item) for item in value]


def value_at(values: list[float], index: int) -> float | None:
    return values[index] if index < len(values) else None


def rounded(value: float | None) -> float | str:
    return "" if value is None else round(float(value), 6)


def class_names(model: Any) -> dict[int, str]:
    names = getattr(model, "names", {})
    if isinstance(names, list):
        return {index: name for index, name in enumerate(names)}
    return {int(index): str(name) for index, name in names.items()}


def count_test_labels(data_path: Path, names: dict[int, str], split: str) -> dict[int, dict[str, int]]:
    # The prepared dataset has a stable path layout next to dataset.yaml.
    label_dir = data_path.parent / "labels" / ("validation" if split == "val" else split)
    counts = {index: {"objects": 0, "images": 0} for index in names}
    if not label_dir.is_dir():
        return counts
    for label_path in label_dir.glob("*.txt"):
        present: set[int] = set()
        for raw in label_path.read_text(encoding="utf-8-sig").splitlines():
            fields = raw.split()
            if not fields:
                continue
            class_id = int(fields[0])
            if class_id in counts:
                counts[class_id]["objects"] += 1
                present.add(class_id)
        for class_id in present:
            counts[class_id]["images"] += 1
    return counts


def recommendation(
    map50_95: float | None,
    recall: float | None,
    images: int,
    reliable_model: bool,
) -> str:
    if not reliable_model:
        return "not_assessable_smoke_model"
    if images < 50:
        return "insufficient_test_images"
    if map50_95 is None:
        return "metric_unavailable"
    if map50_95 < 0.20 or (recall is not None and recall < 0.40):
        return "priority_more_data_and_label_review"
    if map50_95 < 0.50 or (recall is not None and recall < 0.65):
        return "more_hard_examples_recommended"
    return "currently_adequate"


def main() -> None:
    configure_utf8_console()
    args = parse_args()
    weights = args.weights.resolve()
    data_path = args.data.resolve()
    project_dir = args.project.resolve()
    if not weights.is_file():
        raise FileNotFoundError(
            f"Trained weights not found: {weights}\n"
            "Run scripts/22_train_yolo.py first, or specify --weights explicitly."
        )
    if not data_path.is_file():
        raise FileNotFoundError(f"dataset.yaml not found: {data_path}")
    if args.imgsz < 128 or args.batch < 1 or not 0 <= args.conf <= 1 or not 0 < args.iou <= 1:
        raise ValueError("Invalid imgsz, batch, conf, or iou value.")

    try:
        import torch
        import ultralytics
        from ultralytics import YOLO
    except ImportError as error:
        raise RuntimeError("PyTorch and Ultralytics are required for evaluation.") from error

    device = args.device
    if device == "auto":
        device = "0" if torch.cuda.is_available() else "cpu"
    if device != "cpu" and not torch.cuda.is_available():
        raise RuntimeError("CUDA device requested but CUDA is unavailable.")

    print(f"weights: {weights}")
    print(f"data: {data_path}")
    print(f"split: {args.split}")
    print(f"device: {device} ({torch.cuda.get_device_name(0) if device != 'cpu' else 'CPU'})")
    model = YOLO(str(weights))
    training_summary_path = weights.parent.parent / "training_summary.json"
    training_summary = read_json(training_summary_path, {}) or {}
    smoke_model = bool(training_summary.get("smoke_test")) or "smoke" in str(weights).lower()
    if smoke_model:
        print("warning: smoke-test weights; metrics verify the pipeline only, not model quality")
    metrics = model.val(
        data=str(data_path),
        split=args.split,
        imgsz=args.imgsz,
        batch=args.batch,
        workers=args.workers,
        device=device,
        conf=args.conf,
        iou=args.iou,
        project=str(project_dir),
        name=args.name,
        exist_ok=True,
        plots=True,
        save_json=False,
        verbose=True,
    )

    save_dir = Path(getattr(metrics, "save_dir", project_dir / args.name)).resolve()
    names = class_names(model)
    box = getattr(metrics, "box", None)
    precision = as_list(getattr(box, "p", None))
    recall = as_list(getattr(box, "r", None))
    map50 = as_list(getattr(box, "ap50", None))
    map50_95 = as_list(getattr(box, "ap", None))
    counts = count_test_labels(data_path, names, args.split)
    class_rows: list[dict[str, Any]] = []
    priorities: list[dict[str, Any]] = []
    for class_id, name in sorted(names.items()):
        p = value_at(precision, class_id)
        r = value_at(recall, class_id)
        m50 = value_at(map50, class_id)
        m95 = value_at(map50_95, class_id)
        advice = recommendation(m95, r, counts[class_id]["images"], not smoke_model)
        row = {
            "class_id": class_id,
            "class_name": name,
            "test_images": counts[class_id]["images"],
            "test_objects": counts[class_id]["objects"],
            "precision": rounded(p),
            "recall": rounded(r),
            "map50": rounded(m50),
            "map50_95": rounded(m95),
            "recommendation": advice,
        }
        class_rows.append(row)
        if advice != "currently_adequate":
            priorities.append(row)

    write_csv(
        save_dir / "per_class_metrics.csv",
        class_rows,
        [
            "class_id", "class_name", "test_images", "test_objects", "precision", "recall",
            "map50", "map50_95", "recommendation",
        ],
    )
    results_dict = {
        str(key): round(float(value), 6)
        for key, value in getattr(metrics, "results_dict", {}).items()
        if isinstance(value, (int, float))
    }
    speed = {
        str(key): round(float(value), 4)
        for key, value in getattr(metrics, "speed", {}).items()
        if isinstance(value, (int, float))
    }
    summary = {
        "status": "completed",
        "evaluated_at_utc": datetime.now(timezone.utc).isoformat(),
        "weights": str(weights),
        "training_summary": str(training_summary_path) if training_summary_path.is_file() else "",
        "evaluation_kind": "pipeline_smoke_test" if smoke_model else "trained_model_test",
        "metrics_suitable_for_data_decisions": not smoke_model,
        "data": str(data_path),
        "split": args.split,
        "imgsz": args.imgsz,
        "batch": args.batch,
        "device": device,
        "save_dir": str(save_dir),
        "results": results_dict,
        "speed_ms_per_image": speed,
        "classes_requiring_attention": [row["class_name"] for row in priorities],
        "artifacts": {
            "per_class_metrics_csv": str(save_dir / "per_class_metrics.csv"),
            "confusion_matrix": str(save_dir / "confusion_matrix.png"),
            "confusion_matrix_normalized": str(save_dir / "confusion_matrix_normalized.png"),
        },
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "torch": torch.__version__,
            "ultralytics": ultralytics.__version__,
            "cuda_available": bool(torch.cuda.is_available()),
            "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "",
        },
    }
    write_json(save_dir / "evaluation_summary.json", summary)

    print("evaluation completed")
    print(f"save_dir: {save_dir}")
    print(f"per_class_metrics: {save_dir / 'per_class_metrics.csv'}")
    print(f"summary: {save_dir / 'evaluation_summary.json'}")
    print(
        "classes requiring attention: "
        + (", ".join(summary["classes_requiring_attention"]) or "none")
    )


if __name__ == "__main__":
    main()
