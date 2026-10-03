"""
Command-line interface for the automated video production and YouTube upload pipeline.
"""

import argparse
import sys
from datetime import datetime, timezone
from typing import Optional
import zoneinfo

from src.config import VideoFormat, VideoTopic, settings
from src.database.models import JobStatus
from src.database.state_manager import state_manager
from src.logger import logger
from src.pipeline import pipeline
from src.scheduler.cron_runner import StandaloneScheduler
from src.scheduler.daily_schedule import daily_schedule
from src.scheduler.queue_manager import queue_manager


def _today_in_configured_timezone() -> str:
    return datetime.now(zoneinfo.ZoneInfo(settings.timezone)).strftime("%Y-%m-%d")


def cmd_generate_one(args):
    """Generate and publish a single video on demand."""
    print(f"\n🎬 Starting single video generation: Format={args.format}, Topic={args.topic or 'Auto-Rotated'}")
    job = pipeline.run_job(
        video_format=args.format,
        topic=args.topic,
        slot_name=f"cli_{args.format}_{datetime.now(timezone.utc).strftime('%H%M%S')}",
        preview_mode=args.preview,
        enforce_quota=not args.force,
    )
    print(f"\nResult: Job ID={job.id}")
    print(f"Status: {job.status.value.upper()}")
    if job.status == JobStatus.COMPLETED:
        print(f"✅ Success! YouTube ID: {job.youtube_id} | URL: {job.youtube_url}")
        print(f"File: {job.video_path} (Duration: {job.duration_seconds:.1f}s)")
    else:
        print(f"❌ Failed: {job.error_message}")
        sys.exit(1)


def cmd_run_scheduler(args):
    """Start continuous standalone scheduler."""
    print(f"\n⏰ Starting Standalone Daily Video Scheduler (Timezone: {settings.timezone})...")
    print("Pre-scheduling 7 daily slots (5 Shorts + 2 Long). Press Ctrl+C to exit.")
    scheduler = StandaloneScheduler(blocking=True)
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("\nStopping scheduler...")
        scheduler.shutdown()


def cmd_run_daily_batch(args):
    """Execute all 7 scheduled slots for today sequentially."""
    today = _today_in_configured_timezone()
    print(f"\n📦 Running Daily Video Batch for {today} (5 Shorts + 2 Long videos)...")
    results = queue_manager.run_daily_batch(today, preview_mode=args.preview)
    completed = [r for r in results if r.status == JobStatus.COMPLETED]
    print(f"\nBatch Complete! {len(completed)}/{len(results)} videos successfully published.")


def cmd_status(args):
    """Display current daily quota status and recent job history."""
    today = _today_in_configured_timezone()
    quota = state_manager.get_daily_quota(today)
    print(f"\n=======================================================")
    print(f"📊 USA Kids Video Production Pipeline Status ({today})")
    print(f"=======================================================")
    print(f"• Shorts Target:    {quota.completed_shorts}/{quota.target_shorts} completed ({quota.failed_shorts} failed)")
    print(f"• Long Videos:      {quota.completed_long}/{quota.target_long} completed ({quota.failed_long} failed)")
    print(f"• Quota Met:        {'✅ YES' if quota.is_quota_met else '⏳ IN PROGRESS'}")
    print(f"-------------------------------------------------------")
    print("Recent Jobs:")
    jobs = state_manager.get_all_jobs(limit=10)
    if not jobs:
        print("  (No jobs recorded yet)")
    for j in jobs:
        status_icon = "✅" if j.status == JobStatus.COMPLETED else ("❌" if j.status == JobStatus.FAILED else "⏳")
        print(f"  {status_icon} [{j.id}] {j.video_format.upper():<6} | {j.topic:<22} | {j.status.value:<10} | {j.created_at[:19]}")
    print("=======================================================\n")


def cmd_retry_failed(args):
    """Manually trigger retry on any eligible failed jobs."""
    print("\n🔄 Scanning for retryable failed jobs...")
    recovered = queue_manager.monitor_and_retry(
        preview_mode=args.preview,
        backoff_seconds=0 if args.force else None,
    )
    print(f"Retry run complete. Successfully recovered: {recovered} jobs.")


def cmd_test_pipeline(args):
    """Quick end-to-end verification of both Shorts and Long generation."""
    print("\n🧪 Running Pipeline Health Check (Shorts & Long in Preview Mode)...")
    print("\n1. Testing 9:16 Shorts Pipeline...")
    job_short = pipeline.run_job(
        video_format=VideoFormat.SHORTS.value,
        topic=VideoTopic.ANIMAL_RIDDLES.value,
        slot_name="test_short_slot",
        preview_mode=True,
        enforce_quota=False,
    )
    if job_short.status != JobStatus.COMPLETED:
        print(f"❌ Shorts test failed: {job_short.error_message}")
        sys.exit(1)
    print(f"✅ Shorts test passed! Duration: {job_short.duration_seconds:.1f}s")

    print("\n2. Testing 16:9 Long-Form Pipeline...")
    job_long = pipeline.run_job(
        video_format=VideoFormat.LONG.value,
        topic=VideoTopic.SPACE_FACTS.value,
        slot_name="test_long_slot",
        preview_mode=True,
        enforce_quota=False,
    )
    if job_long.status != JobStatus.COMPLETED:
        print(f"❌ Long test failed: {job_long.error_message}")
        sys.exit(1)
    print(f"✅ Long-form test passed! Duration: {job_long.duration_seconds:.1f}s")
    print("\n🎉 All pipeline health checks PASSED successfully!")


def main():
    parser = argparse.ArgumentParser(
        description="Automated Video Production & YouTube Upload Pipeline for US Kids Content"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # generate-one / run-single
    gen_parser = subparsers.add_parser("generate-one", aliases=["run-single"], help="Generate and upload a single video")
    gen_parser.add_argument("--format", choices=["shorts", "long"], default="shorts", help="Video format")
    gen_parser.add_argument("--topic", choices=[t.value for t in VideoTopic], default=None, help="Video topic")
    gen_parser.add_argument("--preview", action="store_true", help="Fast preview rendering mode")
    gen_parser.add_argument("--force", action="store_true", help="Bypass daily quota limits")
    gen_parser.set_defaults(func=cmd_generate_one)

    # run-scheduler
    sched_parser = subparsers.add_parser("run-scheduler", help="Run continuous daily schedule")
    sched_parser.set_defaults(func=cmd_run_scheduler)

    # run-daily-batch / run-daily
    batch_parser = subparsers.add_parser("run-daily-batch", aliases=["run-daily"], help="Run all 7 daily videos sequentially")
    batch_parser.add_argument("--preview", action="store_true", help="Fast preview rendering mode")
    batch_parser.set_defaults(func=cmd_run_daily_batch)

    # status
    status_parser = subparsers.add_parser("status", help="Check daily quota and job states")
    status_parser.set_defaults(func=cmd_status)

    # retry-failed / retry
    retry_parser = subparsers.add_parser("retry-failed", aliases=["retry"], help="Retry any failed jobs")
    retry_parser.add_argument("--preview", action="store_true", help="Fast preview rendering mode")
    retry_parser.add_argument("--force", action="store_true", help="Bypass cooldown backoff and retry immediately")
    retry_parser.set_defaults(func=cmd_retry_failed)

    # test-pipeline / health
    test_parser = subparsers.add_parser("test-pipeline", aliases=["health"], help="Run quick end-to-end tests")
    test_parser.set_defaults(func=cmd_test_pipeline)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
