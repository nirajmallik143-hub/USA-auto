"""
Command-line interface for the automated video production and YouTube upload pipeline.
"""

import argparse
import sys
import zoneinfo
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

from src.config import VideoFormat, VideoTopic, settings
from src.database.models import JobStatus
from src.database.state_manager import state_manager
from src.logger import logger
from src.pipeline import pipeline
from src.scheduler.cron_runner import StandaloneScheduler
from src.scheduler.daily_schedule import daily_schedule
from src.scheduler.queue_manager import queue_manager


def _today() -> str:
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


def evaluate_day(date_str: str) -> Tuple[bool, List[str], List[str]]:
    """
    Inspect persisted state for a date.
    Returns (ok, problems, notes). Not ok when any job ended FAILED or nothing was uploaded.
    """
    jobs = state_manager.get_jobs_by_date(date_str)
    quota = state_manager.get_daily_quota(date_str)
    completed = quota.completed_shorts + quota.completed_long
    failed = [j for j in jobs if j.status == JobStatus.FAILED]
    pending = [j for j in jobs if j.status != JobStatus.COMPLETED and j.status != JobStatus.FAILED]

    problems = [f"{j.id} [{j.video_format}/{j.topic}]: {j.error_message}" for j in failed]
    notes = []
    if not jobs:
        problems.append("No jobs were scheduled for this date.")
    elif completed == 0:
        problems.append("No videos were uploaded although jobs were scheduled.")
    elif pending:
        notes.append(f"{len(pending)} job(s) still pending (e.g. YouTube quota reached); the next run will continue.")
    return not problems, problems, notes


def report_day(date_str: str, summary_file: Optional[str] = None) -> bool:
    ok, problems, notes = evaluate_day(date_str)
    for note in notes:
        print(f"⚠️  {note}")
    if ok:
        print(f"✅ {date_str}: no failed jobs.")
    else:
        print(f"❌ {date_str}: problems detected:")
        for p in problems:
            print(f"  - {p}")
    if summary_file:
        lines = [f"Date: {date_str}", ""] + [f"- {p}" for p in problems] + [f"- (note) {n}" for n in notes]
        Path(summary_file).parent.mkdir(parents=True, exist_ok=True)
        Path(summary_file).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return ok


def cmd_run_daily_batch(args):
    """Execute all 7 scheduled slots for today sequentially."""
    today = _today()
    print(f"\n📦 Running Daily Video Batch for {today} (5 Shorts + 2 Long videos)...")
    results = queue_manager.run_daily_batch(today, preview_mode=args.preview, max_videos=getattr(args, "count", None))
    # Retries inside the batch may have changed statuses; report the persisted state.
    completed = [r for r in results if (state_manager.get_job(r.id) or r).status == JobStatus.COMPLETED]
    print(f"\nBatch Complete! {len(completed)}/{len(results)} videos successfully published.")
    if not report_day(today):
        sys.exit(1)


def cmd_auth(args):
    """Interactive OAuth flow that creates the YouTube token."""
    from src.youtube.client import YouTubeAuthError, run_auth_flow

    try:
        path = run_auth_flow(
            client_secrets_file=args.client_secrets,
            output_file=args.output,
            open_browser=not args.no_browser,
        )
    except YouTubeAuthError as e:
        print(f"❌ {e}")
        sys.exit(1)
    print(f"\n✅ Token saved to {path}")
    print("Copy the ENTIRE contents of that file into the GitHub secret YOUTUBE_TOKEN_JSON")
    print("(and the client secrets file into YOUTUBE_CLIENT_SECRETS_JSON). Never commit either file.")


def cmd_doctor(args):
    """Preflight checks; exits non-zero if any required check fails."""
    from src.preflight import run_doctor

    print("\n🩺 Running preflight checks...")
    failed = False
    for r in run_doctor():
        icon = "✅" if r.ok else ("⚠️ " if r.warning else "❌")
        print(f"{icon} {r.name}: {r.message}")
        if not r.ok and not r.warning:
            failed = True
    if failed:
        print("\nPreflight FAILED. Fix the items marked ❌ above.")
        sys.exit(1)
    print("\nPreflight passed.")


def cmd_status(args):
    """Display current daily quota status and recent job history."""
    today = _today()
    if getattr(args, "check", False):
        if not report_day(today, getattr(args, "summary_file", None)):
            sys.exit(1)
        return
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
    batch_parser.add_argument("--count", type=int, default=None, help="Attempt at most N not-yet-completed videos")
    batch_parser.set_defaults(func=cmd_run_daily_batch)

    # status
    status_parser = subparsers.add_parser("status", help="Check daily quota and job states")
    status_parser.add_argument("--check", action="store_true", help="Exit non-zero if today has failed jobs or no uploads")
    status_parser.add_argument("--summary-file", default=None, help="With --check, write a markdown problem summary here")
    status_parser.set_defaults(func=cmd_status)

    # auth
    auth_parser = subparsers.add_parser("auth", help="Create the YouTube OAuth token (run locally)")
    auth_parser.add_argument("--client-secrets", default=None, help="Path to OAuth client secrets JSON")
    auth_parser.add_argument("--output", default=None, help="Where to write the token JSON")
    auth_parser.add_argument("--no-browser", action="store_true", help="Print the URL instead of opening a browser")
    auth_parser.set_defaults(func=cmd_auth)

    # doctor
    doctor_parser = subparsers.add_parser("doctor", help="Preflight checks (ffmpeg, env, token, channel, output dir)")
    doctor_parser.set_defaults(func=cmd_doctor)

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
