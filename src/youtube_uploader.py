import os
import logging
from typing import List, Optional, Dict, Any
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

logger = logging.getLogger(__name__)

class YouTubeUploader:
    """
    Handles authentication and uploading of videos to YouTube using the YouTube Data API v3,
    complete with child-friendly SEO optimization and the critical COPPA ('Made for Kids') flag.
    """
    
    # SCOPES required to upload videos to YouTube
    SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

    def __init__(
        self,
        client_secrets_file: Optional[str] = None,
        credentials_file: Optional[str] = None
    ):
        self.client_secrets_file = client_secrets_file or os.getenv("YOUTUBE_CLIENT_SECRETS_FILE", "client_secrets.json")
        self.credentials_file = credentials_file or os.getenv("YOUTUBE_CREDENTIALS_FILE", "credentials.json")
        self.youtube = None

    def authenticate(self) -> bool:
        """
        Authenticates with YouTube using stored credentials or executing a new OAuth2 flow.
        If files are missing, logs warning and falls back to mock/dry-run mode.
        """
        creds = None
        
        # 1. Attempt to load stored credentials
        if os.path.exists(self.credentials_file):
            try:
                creds = Credentials.from_authorized_user_file(self.credentials_file, self.SCOPES)
                logger.info("Loaded YouTube credentials from storage.")
            except Exception as e:
                logger.warning(f"Failed to load credentials from file: {e}")

        # 2. If credentials don't exist or are invalid, refresh/acquire them
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    logger.info("Refreshing expired YouTube OAuth2 credentials...")
                    creds.refresh(Request())
                except Exception as e:
                    logger.error(f"Failed to refresh credentials: {e}")
                    creds = None
            
            if not creds:
                # Need a new authorization flow
                if not os.path.exists(self.client_secrets_file):
                    logger.warning(
                        f"YouTube OAuth client secrets file '{self.client_secrets_file}' not found. "
                        "Uploader will run in DRY-RUN/MOCK mode."
                    )
                    return False
                
                try:
                    logger.info("Starting YouTube OAuth client authorization flow...")
                    # Local server auth flow
                    flow = InstalledAppFlow.from_client_secrets_file(self.client_secrets_file, self.SCOPES)
                    creds = flow.run_local_server(port=0, authorization_prompt_message="Please visit this URL to authorize the app:")
                except Exception as e:
                    logger.error(f"OAuth authorization flow failed: {e}")
                    return False

            # Save the credentials for next runs
            try:
                with open(self.credentials_file, "w") as f:
                    f.write(creds.to_json())
                logger.info(f"Saved authorized YouTube credentials to {self.credentials_file}")
            except Exception as e:
                logger.warning(f"Failed to save credentials to file: {e}")

        try:
            self.youtube = build("youtube", "v3", credentials=creds)
            logger.info("YouTube API client initialized successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to build YouTube service: {e}")
            return False

    def optimize_seo(self, title: str, category: str, is_short: bool) -> Dict[str, Any]:
        """
        Optimizes video metadata for search, high click-through-rates, and child-safe discoverability.
        """
        seo = {}
        
        # 1. Kids titles are simple, enthusiastic, and descriptive. Shorts require #Shorts
        clean_title = title.strip()
        if is_short:
            # YouTube Shorts SEO optimization
            if "#shorts" not in clean_title.lower():
                # Limit length to fit mobile screen and include hashtag
                seo["title"] = f"{clean_title[:80]} #shorts #kids #learning"
            else:
                seo["title"] = clean_title[:100]
        else:
            # Long form video optimization: emotional hook and bracketed details
            if not any(bracket in clean_title for bracket in ["[", "(", "{"]):
                seo["title"] = f"{clean_title[:75]} | Fun Learning for Kids!"
            else:
                seo["title"] = clean_title[:100]

        # 2. Kid-friendly Description with learning context, hashtags, and safety message
        hashtags = "#kids #learning #fun #animation #educational" if not is_short else "#shorts #kids #educational #toddlers"
        seo["description"] = (
            f"🎈 Welcome to our magical children's world! Today we are exploring: {title}. 🎈\n\n"
            f"This video is designed specifically for toddlers and young learners to boost creativity, "
            f"language acquisition, and critical cognitive skills through positive and colorful visuals!\n\n"
            f"If you enjoyed this safe, fun educational content, please like and subscribe for daily videos! 🌟\n\n"
            f"{hashtags}\n\n"
            f"--- Safe Kids Content Disclaimer ---\n"
            f"This content is compliant with the Children's Online Privacy Protection Act (COPPA). "
            f"The video features high-contrast colors, friendly speech, and educational topics ideal for early childhood."
        )

        # 3. Optimized kid-friendly tags
        base_tags = ["kids", "children", "learning", "toddlers", "nursery rhymes", "stories for kids", "education"]
        if category == "stories":
            base_tags += ["bedtime stories", "fairy tales", "animated stories", "cute cartoon story"]
        elif category == "trivia":
            base_tags += ["fun facts", "animal trivia", "space facts", "kids quiz", "brain teasers"]
        elif category == "learning":
            base_tags += ["learn colors", "numbers for kids", "count to 10", "alphabet song", "phonics"]
            
        if is_short:
            base_tags += ["shorts", "youtube shorts", "viral shorts"]
            
        seo["tags"] = list(set(base_tags))[:20] # Limit tags count
        return seo

    def upload_video(
        self,
        video_path: str,
        script: Dict[str, Any],
        is_short: bool = True,
        privacy_status: str = "private"
    ) -> Optional[str]:
        """
        Uploads a video to YouTube with optimized metadata and 'Made for Kids' status.
        Args:
            video_path (str): Path to local MP4 video file.
            script (dict): The generation script data used for SEO context.
            is_short (bool): Whether this is a Short (9:16) or Long (16:9) video.
            privacy_status (str): "public", "private", or "unlisted".
        Returns:
            str: YouTube video ID on success, or None on failure/dry-run.
        """
        if not os.path.exists(video_path):
            logger.error(f"Cannot upload video: File '{video_path}' does not exist.")
            return None

        # Try to authenticate. If failed/no credentials, run as dry-run
        if not self.youtube and not self.authenticate():
            logger.warning(
                f"[DRY-RUN / MOCK UPLOAD] Successfully processed '{video_path}' metadata.\n"
                f"Title: {script['title']}\n"
                f"Is Short: {is_short}\n"
                f"COPPA Status: selfDeclaredMadeForKids=True\n"
                "To perform actual YouTube uploads, please configure 'client_secrets.json'."
            )
            # Return a mock video ID for queue and task logging
            return f"MOCK_YT_ID_{random.randint(100000, 999999)}"

        # Perform SEO optimization
        seo = self.optimize_seo(script["title"], script.get("category", "learning"), is_short)
        
        # Build API payload
        # Category 27 = Education, 1 = Film & Animation
        category_id = "27" if script.get("category") == "learning" else "1"
        
        body = {
            "snippet": {
                "title": seo["title"],
                "description": seo["description"],
                "tags": seo["tags"],
                "categoryId": category_id,
                "defaultLanguage": "en",
                "defaultAudioLanguage": "en"
            },
            "status": {
                "privacyStatus": privacy_status,
                # CRITICAL: This declares the content is compliant with COPPA (USA Kids Protection)
                "selfDeclaredMadeForKids": True
            }
        }

        # Media upload
        media = MediaFileUpload(
            video_path,
            chunksize=1024 * 1024,
            mimetype="video/mp4",
            resumable=True
        )

        try:
            logger.info(f"Uploading '{video_path}' to YouTube ({privacy_status})...")
            request = self.youtube.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media
            )
            
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    logger.info(f"Upload progress: {int(status.progress() * 100)}%")
                    
            video_id = response.get("id")
            logger.info(f"Successfully uploaded! Video ID: {video_id}")
            logger.info(f"Video URL: https://www.youtube.com/watch?v={video_id}")
            return video_id
            
        except Exception as e:
            logger.error(f"YouTube upload failed: {e}")
            return None
