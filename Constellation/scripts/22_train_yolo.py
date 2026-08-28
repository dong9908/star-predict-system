"""Train a small YOLO detector on the prepared MobilTelesco 8-class dataset."""

from __future__ import annotations

import argparse
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lib.io_utils import configure_utf8_console, write_json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = PROJECT_ROOT / "data" / "processed" / "yolo_mobiltelesco_8" / "dataset.yaml"
DEFAULT_PROJECT = PROJECT_ROOT / "data" / "results" / "yolo_training"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--model", default="yolo11n.pt", help="Pretrained model name or .pt path")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=2)
    parser.add_argument("--workers", type=int, default=0, help="Windows default 0 for stability")
    parser.add_argument("--device", default="auto", help="auto, cpu, or CUDA index such as 0")
    parser.add_argument("--project", type=Path, default=DEFAULT_PROJECT)
    parser.add_argument("--name", default="mobiltelesco8_yolo11n")
    parser.add_argument("--seed", type=int, default=20260828)
    parser.add_argument("--patience", type=int, default=12)
    parser.add_argument("--fraction", type=float, default=1.0)
    parser.add_argument("--resume", type=Path, help="Resume from a last.pt checkpoint")
    parser.add_argument("--smoke-test", action="store_true", help="Run 1 epoch at 320px on 5%% of train data")
    return parser.parse_args()


def environment_info(torch: Any, ultralytics: Any, device: str) -> dict[str, Any]:
    cuda = bool(torch.cuda.is_available())
    return {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "platform": platform.platform(),
        "torch": torch.__version__,
        "ultralytics": ultralytics.__version__,
        "cuda_available": cuda,
        "cuda_runtime": torch.version.cuda,
        "selected_device": device,
        "gpu_name": torch.cuda.get_device_name(0) if cuda else "",
        "gpu_vram_gb": round(torch.cuda.get_device_properties(0).total_memory / 1024**3, 3) if cuda else 0,
    }


def main() -> None:
    configure_utf8_console()
    args = parse_args()
    if args.epochs < 1 or args.imgsz < 128 or args.batch < 1:
        raise ValueError("epochs, imgsz and batch values are invalid.")
    if not 0 < args.fraction <= 1:
        raise ValueError("fraction must be in (0, 1].")
    data_path = args.data.resolve()
    project_dir = args.project.resolve()
    if not data_path.is_file():
        raise FileNotFoundError(f"YOLO dataset.yaml not found: {data_path}")

    try:
        import torch
        import ultralytics
        from ultralytics import YOLO
    except ImportError as error:
        raise RuntimeError(
            "PyTorch/Ultralytics is not installed. Install CUDA PyTorch first, then ultralytics-opencv-headless."
        ) from error

    device = args.device
    if device == "auto":
        device = "0" if torch.cuda.is_available() else "cpu"
    if device != "cpu" and not torch.cuda.is_available():
        raise RuntimeError("CUDA device requested but torch.cuda.is_available() is False.")

    epochs = 1 if args.smoke_test else args.epochs
    imgsz = min(args.imgsz, 320) if args.smoke_test else args.imgsz
    fraction = min(args.fraction, 0.05) if args.smoke_test else args.fraction
    run_name = f"{args.name}_smoke" if args.smoke_test else args.name
    run_dir = project_dir / run_name
    run_dir.mkdir(parents=True, exist_ok=True)
    environment = environment_info(torch, ultralytics, device)
    write_json(run_dir / "environment.json", environment)

    print(f"device: {device} ({environment['gpu_name'] or 'CPU'})")
    print(f"data: {data_path}")
    print(f"model: {args.resume.resolve() if args.resume else args.model}")
    print(f"epochs={epochs}, imgsz={imgsz}, batch={args.batch}, fraction={fraction}")
    if args.smoke_test:
        print("mode: smoke test (full training is not being performed)")

    model_source = str(args.resume.resolve()) if args.resume else args.model
    model = YOLO(model_source)
    train_kwargs = {
        "data": str(data_path),
        "epochs": epochs,
        "imgsz": imgsz,
        "batch": args.batch,
        "workers": args.workers,
        "device": device,
        "project": str(project_dir),
        "name": run_name,
        "exist_ok": True,
        "seed": args.seed,
        "deterministic": True,
        "patience": args.patience,
        "fraction": fraction,
        "cache": False,
        "amp": device != "cpu",
        "plots": True,
        "verbose": True,
    }
    if args.resume:
        train_kwargs["resume"] = str(args.resume.resolve())
    results = model.train(**train_kwargs)

    trainer = getattr(model, "trainer", None)
    save_dir = Path(getattr(trainer, "save_dir", run_dir)).resolve()
    best = save_dir / "weights" / "best.pt"
    last = save_dir / "weights" / "last.pt"
    summary = {
        "status": "completed",
        "smoke_test": args.smoke_test,
        "data": str(data_path),
        "model_source": model_source,
        "epochs": epochs,
        "imgsz": imgsz,
        "batch": args.batch,
        "fraction": fraction,
        "device": device,
        "save_dir": str(save_dir),
        "best_weights": str(best) if best.is_file() else "",
        "last_weights": str(last) if last.is_file() else "",
        "results_csv": str(save_dir / "results.csv") if (save_dir / "results.csv").is_file() else "",
        "environment": environment,
        "result_type": type(results).__name__,
    }
    write_json(save_dir / "training_summary.json", summary)
    print("training completed")
    print(f"save_dir: {save_dir}")
    print(f"best: {summary['best_weights'] or 'not created'}")
    print(f"last: {summary['last_weights'] or 'not created'}")
    print(f"summary: {save_dir / 'training_summary.json'}")


if __name__ == "__main__":
    main()
