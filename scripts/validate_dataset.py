"""
CLI Utility to Audit and Validate YOLO Datasets for IBVAP.
Generates docs/ml/DATASET_AUDIT.md with measured statistics.
"""
import os
import sys
import argparse

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ml.dataset.validator import DatasetValidator


def main():
    parser = argparse.ArgumentParser(description="Audit and validate IBVAP YOLO dataset.")
    parser.add_argument(
        "--dataset",
        type=str,
        default=os.path.join(PROJECT_ROOT, "dataset"),
        help="Path to dataset root folder containing images/ and labels/",
    )
    parser.add_argument(
        "--classes",
        type=str,
        default=os.path.join(PROJECT_ROOT, "dataset", "metadata", "classes.yaml"),
        help="Path to classes.yaml file",
    )
    parser.add_argument(
        "--output-doc",
        type=str,
        default=os.path.join(PROJECT_ROOT, "docs", "ml", "DATASET_AUDIT.md"),
        help="Path to output markdown report",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with non-zero code if any errors are found",
    )
    args = parser.parse_args()

    print(f"Auditing dataset at: {args.dataset}")
    print(f"Using class mapping: {args.classes}")

    validator = DatasetValidator(
        dataset_root=args.dataset,
        classes_config_path=args.classes,
    )
    report = validator.validate()

    # Generate Markdown documentation
    os.makedirs(os.path.dirname(args.output_doc), exist_ok=True)
    markdown_content = report.generate_markdown()
    with open(args.output_doc, "w", encoding="utf-8") as f:
        f.write(markdown_content)

    print(f"Report written to: {args.output_doc}")
    print(f"Summary: Images={report.total_images}, Labels={report.total_labels}, Annotations={report.total_annotations}")
    print(f"Errors={report.error_count}, Warnings={report.warning_count}, Leakages={report.leakage_count}")

    if args.strict and not report.is_valid:
        print("FAIL: Dataset validation encountered errors.")
        sys.exit(1)
    else:
        print("SUCCESS: Dataset audit execution complete.")


if __name__ == "__main__":
    main()
