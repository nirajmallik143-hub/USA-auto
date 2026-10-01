import os
import sys
import argparse
import logging
from datetime import datetime
from dotenv import load_dotenv

# Load Environment Variables from .env file if it exists
load_dotenv()

# Configure Global Logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("output/pipeline.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("pipeline_main")

from src.ai_generation import generate_kids_script
from src.video_renderer import render_video_pipeline
from src.youtube_uploader import YouTubeUploader
from src.scheduler import VideoPipelineScheduler


def main():
    parser = argparse.ArgumentParser(
        description="🎈 USA-auto: Python-based Automated YouTube Kids Video Generation & Upload Pipeline 🎈"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available Pipeline Commands")
    
    # 1. Daemon / Scheduler command
    subparsers.add_parser(
        "start-scheduler",
        help="Start the daily 7-video scheduler daemon (5 Shorts, 2 Long)"
    )
    
    # 2. Render Single Video command
    render_parser = subparsers.add_parser(
        "create-video",
        help="Instantly generate, render, and upload/dry-run a single custom video"
    )
    render_parser.add_argument(
        "--type",
        choices=["short", "long"],
        default="short",
        help="Video format: short (9:16 vertical) or long (16:9 horizontal)"
    )
    render_parser.add_argument(
        "--category",
        choices=["stories", "trivia", "learning"],
        default="learning",
        help="Topic category for child-friendly content"
    )
    render_parser.add_argument(
        "--topic",
        type=str,
        default=None,
        help="Specific custom topic/theme (e.g. 'Learn Counting with Trains')"
    )
    render_parser.add_argument(
        "--upload",
        action="store_true",
        help="Attempt to upload the final video to YouTube (requires OAuth configured)"
    )
    
    # 3. Setup YouTube OAuth command
    subparsers.add_parser(
        "auth-youtube",
        help="Perform one-time YouTube Data API v3 OAuth authentication setup"
    )
    
    # 4. View Queue command
    subparsers.add_parser(
        "view-queue",
        help="Display the persistent daily scheduling task queue status"
    )
    
    # 5. Populate Schedule command
    populate_parser = subparsers.add_parser(
        "populate-schedule",
        help="Pre-populate the daily queue for a specific date (defaults to today)"
    )
    populate_parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Target date in YYYY-MM-DD format"
    )

    args = parser.parse_args()
    
    # Ensure folders exist
    os.makedirs("output", exist_ok=True)
    os.makedirs("assets", exist_ok=True)
    
    if args.command == "start-scheduler":
        scheduler = VideoPipelineScheduler()
        scheduler.run_scheduler_daemon()
        
    elif args.command == "create-video":
        logger.info(f"Initiating single-video generation: {args.type.upper()} | Category: {args.category} | Topic: {args.topic or 'Auto'}")
        
        # 1. AI Script Generation
        is_short = (args.type == "short")
        script = generate_kids_script(category=args.category, is_short=is_short, topic_detail=args.topic)
        
        # 2. Render Video
        video_path = render_video_pipeline(script=script, is_short=is_short)
        logger.info(f"Video rendering complete! Output file path: {video_path}")
        
        # 3. Upload or Dry-run
        uploader = YouTubeUploader()
        if args.upload:
            logger.info("Proceeding to YouTube upload...")
            video_id = uploader.upload_video(video_path=video_path, script=script, is_short=is_short, privacy_status="private")
            if video_id:
                logger.info(f"Upload Succeeded! Video ID: {video_id}")
            else:
                logger.error("Upload failed or ran in Dry-run mode.")
        else:
            # Automatic Dry-run output demonstration
            uploader.upload_video(video_path=video_path, script=script, is_short=is_short)
            
    elif args.command == "auth-youtube":
        logger.info("Initializing YouTube OAuth setup...")
        uploader = YouTubeUploader()
        success = uploader.authenticate()
        if success:
            logger.info("YouTube Authentication verified and credentials cached successfully!")
        else:
            logger.error("YouTube Authentication failed or cancelled. Running in Dry-run/Mock mode.")
            
    elif args.command == "view-queue":
        scheduler = VideoPipelineScheduler()
        queue = scheduler.queue
        if not queue:
            logger.info("The schedule queue is currently empty. Run 'populate-schedule' to initialize tasks.")
            return
            
        print("\n=== USA-AUTO AUTOMATED YOUTUBE PIPELINE SCHEDULE QUEUE ===")
        print(f"{'TASK ID':<20} | {'DATE':<10} | {'TIME':<6} | {'FORMAT':<6} | {'CATEGORY':<8} | {'STATUS':<10} | {'YT ID':<15}")
        print("-" * 90)
        for task in queue:
            print(
                f"{task['id']:<20} | "
                f"{task['date']:<10} | "
                f"{task['scheduled_time']:<6} | "
                f"{task['type']:<6} | "
                f"{task['category']:<8} | "
                f"{task['status']:<10} | "
                f"{(task['youtube_id'] or 'None'):<15}"
            )
        print("==========================================================")
        
    elif args.command == "populate-schedule":
        scheduler = VideoPipelineScheduler()
        target_date = args.date or datetime.now().strftime("%Y-%m-%d")
        new_tasks = scheduler.generate_daily_schedule(target_date)
        logger.info(f"Generated {len(new_tasks)} new tasks for {target_date}.")
        
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
