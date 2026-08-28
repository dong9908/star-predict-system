"""Analyze YOLO test errors per image and class, with ranked visual examples."""

from __future__ import annotations

import argparse
import platform
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lib.io_utils import configure_utf8_console, read_csv, read_json, write_csv, write_json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = PROJECT_ROOT / "data" / "processed" / "yolo_mobiltelesco_8"
DEFAULT_WEIGHTS = (
    PROJECT_ROOT / "data" / "results" / "yolo_training"
    / "mobiltelesco8_yolo11n" / "weights" / "best.pt"
)
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "results" / "yolo_error_analysis" / "mobiltelesco8_yolo11n_test"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weights", type=Path, default=DEFAULT_WEIGHTS)
    parser.add_argument("--dataset-dir", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--split", choices=("validation", "test"), default="test")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=2)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--match-iou", type=float, default=0.50)
    parser.add_argument("--localization-iou", type=float, default=0.10)
    parser.add_argument("--max-visualizations", type=int, default=30)
    return parser.parse_args()


def box_iou(left: list[float], right: list[float]) -> float:
    x1 = max(left[0], right[0])
    y1 = max(left[1], right[1])
    x2 = min(left[2], right[2])
    y2 = min(left[3], right[3])
    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    left_area = max(0.0, left[2] - left[0]) * max(0.0, left[3] - left[1])
    right_area = max(0.0, right[2] - right[0]) * max(0.0, right[3] - right[1])
    union = left_area + right_area - intersection
    return intersection / union if union > 0 else 0.0


def read_ground_truth(path: Path, width: int, height: int) -> list[dict[str, Any]]:
    boxes: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        fields = raw.split()
        if len(fields) != 5:
            continue
        class_id = int(fields[0])
        cx, cy, bw, bh = (float(value) for value in fields[1:])
        boxes.append({
            "class_id": class_id,
            "xyxy": [
                (cx - bw / 2) * width,
                (cy - bh / 2) * height,
                (cx + bw / 2) * width,
                (cy + bh / 2) * height,
            ],
        })
    return boxes


def greedy_pairs(
    ground_truth: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
    gt_available: set[int],
    pred_available: set[int],
    minimum_iou: float,
    class_mode: str,
) -> list[tuple[int, int, float]]:
    candidates: list[tuple[float, int, int]] = []
    for gt_index in gt_available:
        for pred_index in pred_available:
            same_class = ground_truth[gt_index]["class_id"] == predictions[pred_index]["class_id"]
            if class_mode == "same" and not same_class:
                continue
            if class_mode == "different" and same_class:
                continue
            iou = box_iou(ground_truth[gt_index]["xyxy"], predictions[pred_index]["xyxy"])
            if iou >= minimum_iou:
                candidates.append((iou, gt_index, pred_index))
    matches: list[tuple[int, int, float]] = []
    used_gt: set[int] = set()
    used_pred: set[int] = set()
    for iou, gt_index, pred_index in sorted(candidates, reverse=True):
        if gt_index in used_gt or pred_index in used_pred:
            continue
        used_gt.add(gt_index)
        used_pred.add(pred_index)
        matches.append((gt_index, pred_index, iou))
    return matches


def analyze_boxes(
    ground_truth: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
    match_iou: float,
    localization_iou: float,
) -> dict[str, Any]:
    gt_available = set(range(len(ground_truth)))
    pred_available = set(range(len(predictions)))

    correct = greedy_pairs(ground_truth, predictions, gt_available, pred_available, match_iou, "same")
    for gt_index, pred_index, _ in correct:
        gt_available.remove(gt_index)
        pred_available.remove(pred_index)

    confusion = greedy_pairs(ground_truth, predictions, gt_available, pred_available, match_iou, "different")
    for gt_index, pred_index, _ in confusion:
        gt_available.remove(gt_index)
        pred_available.remove(pred_index)

    localization = greedy_pairs(
        ground_truth, predictions, gt_available, pred_available, localization_iou, "same"
    )
    localization = [match for match in localization if match[2] < match_iou]
    for gt_index, pred_index, _ in localization:
        gt_available.remove(gt_index)
        pred_available.remove(pred_index)

    matched_ious = [match[2] for match in correct]
    false_negative_indices = sorted(gt_available)
    false_positive_indices = sorted(pred_available)
    tp = len(correct)
    fn = len(false_negative_indices) + len(confusion) + len(localization)
    fp = len(false_positive_indices) + len(confusion) + len(localization)
    precision = tp / (tp + fp) if tp + fp else (1.0 if not ground_truth else 0.0)
    recall = tp / (tp + fn) if tp + fn else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    error_score = fn * 3 + fp + len(confusion) * 2 + len(localization)
    return {
        "correct": correct,
        "confusion": confusion,
        "localization": localization,
        "false_negative_indices": false_negative_indices,
        "false_positive_indices": false_positive_indices,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "mean_matched_iou": sum(matched_ious) / len(matched_ious) if matched_ious else 0.0,
        "error_score": error_score,
    }


def draw_error_image(
    image_path: Path,
    output_path: Path,
    ground_truth: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
    analysis: dict[str, Any],
    names: dict[int, str],
) -> None:
    import cv2

    image = cv2.imread(str(image_path))
    if image is None:
        return
    matched_gt = {item[0] for item in analysis["correct"]}
    matched_pred = {item[1] for item in analysis["correct"]}
    for index, box in enumerate(ground_truth):
        x1, y1, x2, y2 = (int(value) for value in box["xyxy"])
        color = (0, 210, 0) if index in matched_gt else (0, 215, 255)
        label = f"GT {names.get(box['class_id'], box['class_id'])}"
        cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
        cv2.putText(image, label, (x1, max(20, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)
    for index, box in enumerate(predictions):
        x1, y1, x2, y2 = (int(value) for value in box["xyxy"])
        color = (255, 200, 0) if index in matched_pred else (0, 0, 255)
        label = f"P {names.get(box['class_id'], box['class_id'])} {box['confidence']:.2f}"
        cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
        cv2.putText(image, label, (x1, min(image.shape[0] - 8, y2 + 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)
    title = f"TP {analysis['tp']}  FP {analysis['fp']}  FN {analysis['fn']}  F1 {analysis['f1']:.3f}"
    cv2.rectangle(image, (0, 0), (min(image.shape[1], 680), 42), (0, 0, 0), -1)
    cv2.putText(image, title, (12, 29), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    if max(image.shape[:2]) > 1800:
        scale = 1800 / max(image.shape[:2])
        image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), image, [cv2.IMWRITE_JPEG_QUALITY, 90])


def main() -> None:
    configure_utf8_console()
    args = parse_args()
    weights = args.weights.resolve()
    dataset_dir = args.dataset_dir.resolve()
    output_dir = args.output_dir.resolve()
    image_dir = dataset_dir / "images" / args.split
    label_dir = dataset_dir / "labels" / args.split
    index_path = dataset_dir / "dataset_index.csv"
    if not weights.is_file():
        raise FileNotFoundError(
            f"Trained weights not found: {weights}\nRun scripts/22_train_yolo.py or pass --weights."
        )
    if not image_dir.is_dir() or not label_dir.is_dir():
        raise FileNotFoundError(f"YOLO split not found: {image_dir}")
    if not 0 <= args.conf <= 1 or not 0 < args.match_iou <= 1:
        raise ValueError("Invalid confidence or IoU threshold.")
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        import torch
        import ultralytics
        from ultralytics import YOLO
    except ImportError as error:
        raise RuntimeError("PyTorch and Ultralytics are required.") from error

    device = args.device
    if device == "auto":
        device = "0" if torch.cuda.is_available() else "cpu"
    if device != "cpu" and not torch.cuda.is_available():
        raise RuntimeError("CUDA device requested but CUDA is unavailable.")

    training_summary_path = weights.parent.parent / "training_summary.json"
    training_summary = read_json(training_summary_path, {}) or {}
    smoke_model = bool(training_summary.get("smoke_test")) or "smoke" in str(weights).lower()
    if smoke_model:
        print("warning: smoke-test weights; errors verify the workflow only")

    index_rows = read_csv(index_path) if index_path.is_file() else []
    index_by_sample = {row["sample_id"]: row for row in index_rows}
    model = YOLO(str(weights))
    raw_names = model.names
    names = {index: name for index, name in enumerate(raw_names)} if isinstance(raw_names, list) else {
        int(index): str(name) for index, name in raw_names.items()
    }
    print(f"images: {image_dir}")
    print(f"weights: {weights}")
    print(f"device: {device}")

    results = model.predict(
        source=str(image_dir), imgsz=args.imgsz, batch=args.batch, device=device,
        conf=args.conf, stream=True, save=False, verbose=False,
    )
    image_rows: list[dict[str, Any]] = []
    detail_records: list[dict[str, Any]] = []
    class_stats: dict[int, Counter[str]] = defaultdict(Counter)
    stored_visual_data: list[tuple[Path, list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]] = []

    for number, result in enumerate(results, 1):
        image_path = Path(result.path).resolve()
        height, width = result.orig_shape
        label_path = label_dir / f"{image_path.stem}.txt"
        ground_truth = read_ground_truth(label_path, width, height)
        predictions: list[dict[str, Any]] = []
        if result.boxes is not None:
            xyxy = result.boxes.xyxy.detach().cpu().tolist()
            classes = result.boxes.cls.detach().cpu().tolist()
            confidences = result.boxes.conf.detach().cpu().tolist()
            predictions = [
                {"class_id": int(class_id), "confidence": float(confidence), "xyxy": box}
                for box, class_id, confidence in zip(xyxy, classes, confidences)
            ]
        analysis = analyze_boxes(ground_truth, predictions, args.match_iou, args.localization_iou)
        for gt_index, pred_index, _ in analysis["correct"]:
            class_stats[ground_truth[gt_index]["class_id"]]["tp"] += 1
        for gt_index, pred_index, _ in analysis["confusion"]:
            class_stats[ground_truth[gt_index]["class_id"]]["fn"] += 1
            class_stats[predictions[pred_index]["class_id"]]["fp"] += 1
            class_stats[ground_truth[gt_index]["class_id"]]["class_confusion"] += 1
        for gt_index, pred_index, _ in analysis["localization"]:
            class_id = ground_truth[gt_index]["class_id"]
            class_stats[class_id]["fn"] += 1
            class_stats[class_id]["fp"] += 1
            class_stats[class_id]["localization_error"] += 1
        for gt_index in analysis["false_negative_indices"]:
            class_stats[ground_truth[gt_index]["class_id"]]["fn"] += 1
        for pred_index in analysis["false_positive_indices"]:
            class_stats[predictions[pred_index]["class_id"]]["fp"] += 1

        source = index_by_sample.get(image_path.stem, {})
        error_types = []
        if analysis["false_negative_indices"]:
            error_types.append("missed_detection")
        if analysis["false_positive_indices"]:
            error_types.append("false_positive")
        if analysis["confusion"]:
            error_types.append("class_confusion")
        if analysis["localization"]:
            error_types.append("localization_error")
        image_row = {
            "sample_id": image_path.stem,
            "image_path": str(image_path),
            "source_image": source.get("source_image", ""),
            "capture_key": source.get("capture_key", ""),
            "session_id": source.get("session_id", ""),
            "ground_truth_objects": len(ground_truth),
            "predicted_objects": len(predictions),
            "tp": analysis["tp"], "fp": analysis["fp"], "fn": analysis["fn"],
            "precision": round(analysis["precision"], 6),
            "recall": round(analysis["recall"], 6),
            "f1": round(analysis["f1"], 6),
            "mean_matched_iou": round(analysis["mean_matched_iou"], 6),
            "class_confusions": len(analysis["confusion"]),
            "localization_errors": len(analysis["localization"]),
            "error_score": analysis["error_score"],
            "error_types": "|".join(error_types) or "none",
        }
        image_rows.append(image_row)
        detail_records.append({
            **image_row,
            "ground_truth": ground_truth,
            "predictions": predictions,
            "matches": {
                key: value for key, value in analysis.items()
                if key in {"correct", "confusion", "localization", "false_negative_indices", "false_positive_indices"}
            },
        })
        if analysis["error_score"] > 0:
            stored_visual_data.append((image_path, ground_truth, predictions, analysis))
        if number % 50 == 0:
            print(f"analyzed: {number}")

    image_rows.sort(key=lambda row: (-int(row["error_score"]), float(row["f1"]), row["sample_id"]))
    image_fields = [
        "sample_id", "image_path", "source_image", "capture_key", "session_id",
        "ground_truth_objects", "predicted_objects", "tp", "fp", "fn", "precision", "recall",
        "f1", "mean_matched_iou", "class_confusions", "localization_errors", "error_score", "error_types",
    ]
    write_csv(output_dir / "image_errors.csv", image_rows, image_fields)

    class_rows: list[dict[str, Any]] = []
    for class_id, name in sorted(names.items()):
        stats = class_stats[class_id]
        tp, fp, fn = stats["tp"], stats["fp"], stats["fn"]
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        class_rows.append({
            "class_id": class_id, "class_name": name, "tp": tp, "fp": fp, "fn": fn,
            "precision_at_conf": round(precision, 6), "recall_at_conf": round(recall, 6),
            "f1_at_conf": round(f1, 6), "class_confusions": stats["class_confusion"],
            "localization_errors": stats["localization_error"],
        })
    write_csv(
        output_dir / "class_errors.csv", class_rows,
        ["class_id", "class_name", "tp", "fp", "fn", "precision_at_conf", "recall_at_conf",
         "f1_at_conf", "class_confusions", "localization_errors"],
    )
    write_json(output_dir / "error_details.json", detail_records)

    visual_by_path = {item[0]: item for item in stored_visual_data}
    for rank, row in enumerate(image_rows[: args.max_visualizations], 1):
        image_path = Path(row["image_path"])
        if image_path not in visual_by_path:
            continue
        _, ground_truth, predictions, analysis = visual_by_path[image_path]
        draw_error_image(
            image_path, output_dir / "visualizations" / f"{rank:03d}_{image_path.stem}.jpg",
            ground_truth, predictions, analysis, names,
        )

    total_tp = sum(row["tp"] for row in image_rows)
    total_fp = sum(row["fp"] for row in image_rows)
    total_fn = sum(row["fn"] for row in image_rows)
    summary = {
        "status": "completed",
        "analyzed_at_utc": datetime.now(timezone.utc).isoformat(),
        "evaluation_kind": "pipeline_smoke_test" if smoke_model else "trained_model_error_analysis",
        "metrics_suitable_for_data_decisions": not smoke_model,
        "weights": str(weights), "dataset_dir": str(dataset_dir), "split": args.split,
        "confidence_threshold": args.conf, "match_iou": args.match_iou,
        "images": len(image_rows), "images_with_errors": sum(row["error_score"] > 0 for row in image_rows),
        "tp": total_tp, "fp": total_fp, "fn": total_fn,
        "visualizations": min(args.max_visualizations, len(stored_visual_data)),
        "output_dir": str(output_dir),
        "artifacts": {
            "image_errors_csv": str(output_dir / "image_errors.csv"),
            "class_errors_csv": str(output_dir / "class_errors.csv"),
            "error_details_json": str(output_dir / "error_details.json"),
            "visualizations_dir": str(output_dir / "visualizations"),
        },
        "environment": {
            "python": sys.version, "platform": platform.platform(), "torch": torch.__version__,
            "ultralytics": ultralytics.__version__, "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "",
        },
    }
    write_json(output_dir / "error_analysis_summary.json", summary)
    print("error analysis completed")
    print(f"images: {summary['images']}, with errors: {summary['images_with_errors']}")
    print(f"TP={total_tp}, FP={total_fp}, FN={total_fn}")
    print(f"image_errors: {output_dir / 'image_errors.csv'}")
    print(f"class_errors: {output_dir / 'class_errors.csv'}")
    print(f"summary: {output_dir / 'error_analysis_summary.json'}")


if __name__ == "__main__":
    main()
