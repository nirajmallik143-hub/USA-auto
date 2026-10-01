import os
import json
import time
import random
import logging
from datetime import datetime, timedelta
import schedule
from typing import List, Dict, Any

from src.ai_generation import generate_kids_script
from src.video_renderer import render_video_pipeline
from src.youtube_uploader import YouTubeUploader

logger = logging.getLogger(__name__)

QUEUE_FILE_PATH = "output/schedule_queue.json"

# Peak viewership times for US Kids Content (EST/EDT)
# 5 Shorts, 2 Long-form videos
DAILY_SLOTS = [
    {"time": "07:30", "type": "short", "category": "stories"},      # Short 1: Early morning wake up
    {"time": "10:00", "type": "short", "category": "learning"},     # Short 2: Late morning / Toddler play time
    {"time": "12:00", "type": "long", "category": "learning"},      # Long 1:  Lunchtime education
    {"time": "14:30", "type": "short", "category": "trivia"},       # Short 3: Early afternoon / After-nap
    {"time": "16:30", "type": "short", "category": "stories"},      # Short 4: Late afternoon / Quiet play
    {"time": "18:00", "type": "long", "category": "stories"},       # Long 2:  Bedtime / Evening wind down
    {"time": "20:00", "type": "short", "category": "learning"}      # Short 5: Late evening
]

# Random kid-friendly topics to populate the queue
KIDS_TOPICS_POOL = {
    "stories": [
        "The Little Bunny's Balloon", "The Magic Treehouse Library", "The Moon Who Wanted a Hug",
        "The Dragon Who Loved Flowers", "The Caterpillar's Rainbow Wings", "The Elephant's Lost Shoe"
    ],
    "trivia": [
        "Fascinating Baby Animal Names", "Amazing Honeybee Superpowers", "Why is the Sky Blue?",
        "Mindblowing Penguin Facts", "How Do Plants Drink Water?", "The Mystery of Bird Migrations"
    ],
    "learning": [
        "Counting Colorful Candy 1 to 10", "Learn Geometric Shapes Around the House",
        "Exploring Sea Creature Sounds", "Opposites: Big and Small, Hot and Cold",
        "Months of the Year Song & Fun", "The Magic Rainbow Color Mix"
    ]
}


class VideoPipelineScheduler:
    """
    Manages and executes the daily queue of 7 automated YouTube video creation tasks.
    Maintains a persistent JSON queue so tasks can resume if interrupted.
    """
    
    def __init__(self):
        self.queue_path = QUEUE_FILE_PATH
        self.uploader = YouTubeUploader()
        os.makedirs("output", exist_ok=True)
        self.load_queue()

    def load_queue(self) -> List[Dict[str, Any]]:
        """Loads the video task queue from disk."""
        if os.path.exists(self.queue_path):
            try:
                with open(self.queue_path, "r") as f:
                    self.queue = json.load(f)
                logger.info(f"Loaded {len(self.queue)} tasks from persistent queue.")
                return self.queue
            except Exception as e:
                logger.error(f"Failed to load task queue from {self.queue_path}: {e}")
                
        self.queue = []
        return self.queue

    def save_queue(self):
        """Saves the current video task queue to disk."""
        try:
            with open(self.queue_path, "w") as f:
                json.dump(self.queue, f, indent=4)
            logger.info("Saved video task queue to disk.")
        except Exception as e:
            logger.error(f"Failed to save task queue: {e}")

    def generate_daily_schedule(self, target_date_str: str = None) -> List[Dict[str, Any]]:
        """
        Generates and appends a list of 7 scheduled tasks (5 Shorts, 2 Long) for the given date.
        """
        if not target_date_str:
            target_date_str = datetime.now().strftime("%Y-%m-%d")

        # Check if we already have tasks scheduled for this date
        existing_for_date = [t for t in self.queue if t["date"] == target_date_str]
        if existing_for_date:
            logger.info(f"Schedule for {target_date_str} already exists. Skipping generation.")
            return existing_for_date

        logger.info(f"Populating fresh automated daily schedule for {target_date_str}...")
        
        new_tasks = []
        for slot in DAILY_SLOTS:
            category = slot["category"]
            video_type = slot["type"]
            scheduled_time = slot["time"]
            
            # Select an engaging topic
            topic = random.choice(KIDS_TOPICS_POOL[category])
            
            task = {
                "id": f"task_{target_date_str.replace('-', '')}_{scheduled_time.replace(':', '')}",
                "date": target_date_str,
                "scheduled_time": scheduled_time,
                "type": video_type,
                "category": category,
                "topic": topic,
                "status": "pending",
                "attempts": 0,
                "video_path": None,
                "youtube_id": None,
                "completed_at": None,
                "error": None
            }
            new_tasks.append(task)
            self.queue.append(task)

        self.save_queue()
        return new_tasks

    def execute_task(self, task_id: str) -> bool:
        """Runs the entire video generation and upload pipeline for a single task."""
        # Find the task
        task = next((t for t in self.queue if t["id"] == task_id), None)
        if not task:
            logger.error(f"Task with ID {task_id} not found.")
            return False

        if task["status"] == "completed":
            logger.info(f"Task {task_id} is already completed. Skipping.")
            return True

        logger.info(f"🚀 Executing Task {task_id}: {task['type'].upper()} form video on '{task['topic']}'")
        task["status"] = "running"
        task["attempts"] += 1
        self.save_queue()

        try:
            # 1. AI Script Generation
            is_short = (task["type"] == "short")
            logger.info("Step 1: Generating script...")
            script = generate_kids_script(
                category=task["category"],
                is_short=is_short,
                topic_detail=task["topic"]
            )
            
            # 2. Render Video (MoviePy + TTS + Assets)
            logger.info("Step 2: Rendering video file...")
            output_filename = f"{task['id']}_{task['type']}.mp4"
            video_path = render_video_pipeline(
                script=script,
                is_short=is_short,
                output_filename=output_filename
            )
            task["video_path"] = video_path
            self.save_queue()
            
            # 3. YouTube Upload with optimized child-safe metadata
            logger.info("Step 3: Uploading video to YouTube...")
            youtube_id = self.uploader.upload_video(
                video_path=video_path,
                script=script,
                is_short=is_short,
                privacy_status="private" # Upload as private initially for safety/review
            )
            
            # 4. Finalize Task Status
            task["youtube_id"] = youtube_id
            task["status"] = "completed"
            task["completed_at"] = datetime.now().isoformat()
            task["error"] = None
            logger.info(f"✅ Successfully finished execution of Task {task_id}!")
            self.save_queue()
            return True

        except Exception as e:
            logger.error(f"❌ Execution failed for Task {task_id}: {e}", exc_info=True)
            task["status"] = "failed"
            task["error"] = str(e)
            self.save_queue()
            return False

    def check_and_run_scheduled(self):
        """
        Scans the queue for any pending tasks that are scheduled for today and are past their slot time,
        executing them sequentially.
        """
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        
        # Ensure we always have today's tasks populated
        self.generate_daily_schedule(today_str)
        
        # Find all pending/failed tasks for today that should be running
        due_tasks = []
        for task in self.queue:
            if task["date"] == today_str and task["status"] in ["pending", "failed"] and task["attempts"] < 3:
                # Compare scheduled time with current time
                try:
                    sched_time = datetime.strptime(f"{task['date']} {task['scheduled_time']}", "%Y-%m-%d %H:%M")
                    if now >= sched_time:
                        due_tasks.append(task)
                except ValueError as e:
                    logger.error(f"Invalid task scheduling format: {e}")

        if not due_tasks:
            return

        logger.info(f"Found {len(due_tasks)} scheduled video tasks currently due for execution.")
        for task in due_tasks:
            success = self.execute_task(task["id"])
            if not success:
                logger.warning(f"Task {task['id']} failed. Will retry up to 3 times.")

    def run_scheduler_daemon(self):
        """Starts a persistent daemon checking every 30 seconds for scheduled events."""
        logger.info("Starting Daily Automated YouTube Pipeline Scheduler Daemon.")
        logger.info("Press Ctrl+C to terminate.")
        
        # Generate initial schedule for today
        self.generate_daily_schedule()
        
        # Check immediately on launch
        self.check_and_run_scheduled()
        
        # Schedule check-and-run to execute every 30 seconds
        schedule.every(30).seconds.do(self.check_and_run_scheduled)
        
        # Schedule clean-up / next-day generation at midnight
        schedule.every().day.at("00:00").do(lambda: self.generate_daily_schedule())
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            logger.info("Scheduler Daemon stopped manually.")
