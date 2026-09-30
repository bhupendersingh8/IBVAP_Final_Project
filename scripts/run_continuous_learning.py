"""
IBVAP Continuous Self-Training Runner.
CLI and Automation entrypoint for Auto-Curation, GPU Fine-Tuning, and Model Promotion.

Usage:
  # Check status
  python scripts/run_continuous_learning.py --status

  # Curate all pending camera evidence
  python scripts/run_continuous_learning.py --curate

  # Auto-curate and run GPU fine-tuning cycle
  python scripts/run_continuous_learning.py --auto --force --epochs 15

  # Run as background daemon watcher
  python scripts/run_continuous_learning.py --daemon --interval 300
"""
from __future__ import annotations

import os
import sys
import time
import argparse

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ml.continuous_learning.auto_trainer import AutoTrainer, ContinuousLearningConfig


def main():
    parser = argparse.ArgumentParser(description="IBVAP Continuous Self-Training Runner")
    parser.add_argument("--curate", action="store_true", help="Curate pending evidence images into labeled dataset")
    parser.add_argument("--train", action="store_true", help="Run fine-tuning training cycle on GPU")
    parser.add_argument("--auto", action="store_true", help="Auto-curate and train in one pass")
    parser.add_argument("--force", action="store_true", help="Force training even if under min samples threshold")
    parser.add_argument("--status", action="store_true", help="Display current continuous learning status")
    parser.add_argument("--epochs", type=int, default=15, help="Number of training epochs (default: 15)")
    parser.add_argument("--batch", type=int, default=8, help="Batch size (default: 8)")
    parser.add_argument("--device", type=str, default=None, help="Target device: cuda:0 or cpu")
    parser.add_argument("--daemon", action="store_true", help="Run in continuous daemon mode")
    parser.add_argument("--interval", type=int, default=300, help="Daemon check interval in seconds (default: 300)")

    args = parser.parse_args()

    cfg = ContinuousLearningConfig(
        epochs=args.epochs,
        batch=args.batch,
        device=args.device
    )
    trainer = AutoTrainer(project_root=PROJECT_ROOT, config=cfg)

    if args.status:
        stat = trainer.get_status()
        print("============================================================")
        print("  IBVAP Continuous Self-Training System Status")
        print("============================================================")
        print(f"  State                      : {stat['state'].upper()}")
        print(f"  Active Device              : {stat['device']}")
        print(f"  Curated Samples Available  : {stat['curated_samples_available']}")
        print(f"  Min Samples to Train       : {stat['min_samples_required']}")
        print(f"  Ready to Train             : {stat['ready_to_train']}")
        print(f"  Active Production Model    : {stat['active_production_model']}")
        print(f"  Last Run Time              : {stat['last_run_time'] or 'Never'}")
        print("============================================================")
        return

    if args.curate:
        print("[+] Running auto-curation on evidence captures...")
        res = trainer.curate_and_check()
        print(f"[OK] Curated new samples: {res['curation_result']['curated']}")
        print(f"[OK] Total curated samples available: {res['curated_total']}")
        print(f"[OK] Ready for automated training: {res['ready_to_train']}")
        return

    if args.auto or args.train:
        print("[+] Initiating automated self-training cycle on GPU...")
        res = trainer.run_self_training_cycle(force=args.force)
        print(f"Result Status: {res.get('status')}")
        if res.get("production_deployed"):
            print(f"[SUCCESS] Candidate model promoted to PRODUCTION: {res.get('production_weights')}")
        else:
            print(f"[INFO] {res.get('message') or res.get('error') or 'Cycle completed'}")
        return

    if args.daemon:
        print(f"[+] Starting Continuous Learning Daemon (Checking every {args.interval}s)...")
        try:
            while True:
                cur_stat = trainer.curate_and_check()
                if cur_stat["ready_to_train"]:
                    print(f"[+] Threshold met ({cur_stat['curated_total']} samples). Triggering training cycle...")
                    trainer.run_self_training_cycle(force=False)
                else:
                    print(f"[-] Daemon check: {cur_stat['curated_total']}/{cfg.min_samples_to_train} samples. Sleeping {args.interval}s...")
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n[+] Daemon stopped gracefully.")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
