"""
CLI Script to evaluate pretrained detector and generate docs/ml/BASELINE_EVALUATION.md.
"""
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ml.evaluation.baseline_evaluator import BaselineEvaluator


def main():
    print("Evaluating pretrained baseline detector...")
    evaluator = BaselineEvaluator(
        model_path="yolov8n.pt",
        dataset_yaml=os.path.join(PROJECT_ROOT, "dataset", "dataset.yaml"),
        device="cpu",
    )
    metrics = evaluator.evaluate()
    report_md = evaluator.generate_markdown(metrics)

    out_file = os.path.join(PROJECT_ROOT, "docs", "ml", "BASELINE_EVALUATION.md")
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(report_md)

    print(f"Report written to: {out_file}")
    print(f"Latency: {metrics.get('inference_latency_ms')} ms ({metrics.get('fps')} FPS)")
    print(f"mAP50: {metrics.get('mAP50')}")
    print("Baseline evaluation complete.")


if __name__ == "__main__":
    main()
