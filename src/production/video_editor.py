"""
Video editing engine leveraging MoviePy and FFmpeg.
Assembles visual clips, voiceover tracks, background music, and auto-captions
into YouTube-compliant 9:16 Shorts or 16:9 Long-form videos.
"""

from pathlib import Path
from typing import List, Optional, Tuple
from moviepy import (
    AudioFileClip,
    CompositeAudioClip,
    CompositeVideoClip,
    ImageClip,
    concatenate_videoclips,
)

from src.config import VideoFormat, settings
from src.content.script_generator import ScriptData
from src.logger import logger
from src.production.audio import bg_music_generator
from src.production.subtitles import subtitle_generator
from src.production.visuals import visual_manager
from src.production.voice import SceneAudio, voice_engine


class VideoEditor:
    """Assembles and exports final multi-track video productions."""

    def __init__(self):
        pass

    def get_resolution(self, video_format: str) -> Tuple[int, int]:
        if video_format == VideoFormat.SHORTS.value:
            return (1080, 1920)  # 9:16
        return (1920, 1080)      # 16:9

    def produce_video(
        self,
        script: ScriptData,
        job_id: str,
        output_dir: Optional[Path] = None,
        fps: int = 24,
        preview_mode: bool = False,
    ) -> Tuple[Path, float]:
        """
        End-to-end production of final video file:
        1. Synthesize voiceover per scene.
        2. Generate visual backgrounds per scene.
        3. Generate subtitle overlays per scene.
        4. Synthesize kid-friendly background music.
        5. Composite and export final MP4.
        """
        out_dir = output_dir or settings.output_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        job_temp = settings.temp_dir / job_id
        job_temp.mkdir(parents=True, exist_ok=True)

        logger.info(f"Starting video production for job {job_id} ({script.video_format}, {script.topic})")

        # 1. Generate Voiceovers
        scene_audios = voice_engine.generate_scenes_speech(script.scenes, job_temp)

        # 2. Generate Visuals
        visual_paths = visual_manager.generate_scene_visuals(
            video_format=script.video_format,
            topic=script.topic,
            scenes=script.scenes,
            job_temp_dir=job_temp,
        )

        # 3. Assemble Scene Clips
        width, height = self.get_resolution(script.video_format)
        scene_clips = []
        audio_clips_to_close = []

        for i, (scene, sc_audio, vis_path) in enumerate(zip(script.scenes, scene_audios, visual_paths)):
            # Scene duration matches voice narration + slight comfortable breathing room
            scene_duration = max(2.5, sc_audio.duration_seconds + 0.3)

            # Generate subtitle overlay image
            sub_path = job_temp / f"scene_{i:02d}_caption.png"
            subtitle_generator.create_caption_overlay(
                text=sc_audio.caption_text,
                video_format=script.video_format,
                output_path=sub_path,
            )

            # Create visual base clip
            base_clip = ImageClip(str(vis_path)).with_duration(scene_duration)

            # Create caption overlay clip
            caption_clip = ImageClip(str(sub_path)).with_duration(scene_duration)

            # Composite visual + caption
            composite_scene = CompositeVideoClip([base_clip, caption_clip], size=(width, height))

            # Attach spoken audio
            voice_clip = AudioFileClip(str(sc_audio.audio_path))
            audio_clips_to_close.append(voice_clip)
            composite_scene = composite_scene.with_audio(voice_clip)

            scene_clips.append(composite_scene)

        # 4. Concatenate all scenes
        concatenated_video = concatenate_videoclips(scene_clips, method="compose")
        total_duration = concatenated_video.duration

        # 5. Background Music Synthesis & Mixing
        bgm_path = job_temp / "background_music.wav"
        bg_music_generator.generate_kid_bg_track(total_duration, bgm_path)

        bgm_clip = AudioFileClip(str(bgm_path)).with_duration(total_duration).with_volume_scaled(0.12)
        audio_clips_to_close.append(bgm_clip)

        # Mix voiceover with ducked background music
        voice_audio = concatenated_video.audio
        final_audio = CompositeAudioClip([voice_audio, bgm_clip])
        final_video = concatenated_video.with_audio(final_audio)

        # 6. Render final video
        output_filename = f"{job_id}_{script.video_format}.mp4"
        output_file_path = out_dir / output_filename

        render_fps = 15 if preview_mode else fps
        logger.info(f"Rendering final MP4 to {output_file_path} (duration: {total_duration:.1f}s, fps: {render_fps})")

        try:
            final_video.write_videofile(
                str(output_file_path),
                fps=render_fps,
                codec="libx264",
                audio_codec="aac",
                preset="ultrafast" if preview_mode else "fast",
                ffmpeg_params=["-pix_fmt", "yuv420p"],
                logger=None,  # Suppress verbose ffmpeg terminal logs
            )
        finally:
            # Clean up open MoviePy clips to free file locks
            for clip in scene_clips:
                clip.close()
            for a_clip in audio_clips_to_close:
                a_clip.close()
            final_video.close()

        logger.info(f"Video production complete: {output_file_path} ({total_duration:.1f}s)")
        return output_file_path, total_duration


video_editor = VideoEditor()
