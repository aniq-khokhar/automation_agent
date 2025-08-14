#!/usr/bin/env python3
"""
Multi-Video Downloader with AI Summarization
Downloads videos from TikTok/YouTube and generates summaries using Gemini 2.0 Flash
Silent version - returns JSON structure instead of console output
"""

import os
import sys
import re
import tempfile
import shutil
import time
from pathlib import Path
import yt_dlp
import google.generativeai as genai
from typing import List, Dict
from dotenv import load_dotenv

# Configuration - Set your API key here
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  # Replace with your actual API key


def summarize_videos(video_urls: List[str]) -> Dict:
    """
    Download videos from TikTok/YouTube and generate AI summaries

    Args:
        video_urls (List[str]): List of video URLs to process

    Returns:
        Dict: JSON structure with format:
        {
            "videos": [
                {
                    "url": "",
                    "file": "",
                    "summary": ""
                },
                ...
            ]
        }
    """

    class VideoProcessor:
        def __init__(self):
            # Validate API key
            if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
                raise ValueError("Please set your Gemini API key in the GEMINI_API_KEY variable")

            # Setup temporary directory
            self.temp_dir = Path(tempfile.mkdtemp(prefix="video_summarizer_"))

            # Configure Gemini AI
            genai.configure(api_key=GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-2.0-flash-exp')

            # Download configurations
            self.tiktok_opts = {
                'outtmpl': str(self.temp_dir / 'TikTok_%(title)s_%(id)s.%(ext)s'),
                'format': 'best[ext=mp4]/best',
                'writeinfojson': False,
                'writesubtitles': False,
                'quiet': True,
            }

            self.youtube_opts = {
                'outtmpl': str(self.temp_dir / 'YouTube_%(title)s_%(id)s.%(ext)s'),
                'format': 'best[height<=1080][ext=mp4]/best[ext=mp4]',
                'writeinfojson': False,
                'writesubtitles': False,
                'quiet': True,
            }

        def detect_platform(self, url: str) -> str:
            """Detect video platform"""
            tiktok_patterns = [
                r'https?://(?:www\.)?tiktok\.com/@[\w.-]+/video/\d+',
                r'https?://(?:vm|vt)\.tiktok\.com/[\w.-]+',
                r'https?://(?:www\.)?tiktok\.com/t/[\w.-]+',
            ]

            youtube_patterns = [
                r'https?://(?:www\.)?youtube\.com/shorts/[\w-]+',
                r'https?://youtu\.be/[\w-]+',
                r'https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+',
            ]

            if any(re.match(pattern, url) for pattern in tiktok_patterns):
                return 'tiktok'
            elif any(re.match(pattern, url) for pattern in youtube_patterns):
                return 'youtube'
            return 'unknown'

        def download_single_video(self, url: str) -> str:
            """Download a single video and return the file path"""
            platform = self.detect_platform(url)

            if platform not in ['tiktok', 'youtube']:
                return None

            # Choose appropriate options
            opts = self.tiktok_opts if platform == 'tiktok' else self.youtube_opts

            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    # Get info first
                    info = ydl.extract_info(url, download=False)

                    # Download
                    ydl.download([url])

                    # Find the downloaded file
                    prefix = 'TikTok_' if platform == 'tiktok' else 'YouTube_'
                    downloaded_files = list(self.temp_dir.glob(f"{prefix}*"))

                    if downloaded_files:
                        # Get the most recently created file
                        latest_file = max(downloaded_files, key=lambda p: p.stat().st_mtime)
                        return str(latest_file)
                    else:
                        return None

            except Exception as e:
                return None

        def summarize_video(self, video_path: str, url: str) -> Dict[str, str]:
            """Generate video summary using Gemini 2.0 Flash"""
            try:
                # Upload video to Gemini
                video_file = genai.upload_file(path=video_path)

                # Wait for processing
                while video_file.state.name == "PROCESSING":
                    time.sleep(2)
                    video_file = genai.get_file(video_file.name)

                if video_file.state.name == "FAILED":
                    raise ValueError("Video processing failed")

                # Generate summary
                prompt = """
                Analyze this video and provide a comprehensive summary including:
                1. Main content/topic
                2. Key actions or events
                3. Notable objects, people, or scenes
                4. Overall mood or theme
                5. Duration and pacing

                Keep the summary concise but informative (2-3 paragraphs maximum).
                """

                response = self.model.generate_content([video_file, prompt])

                # Clean up uploaded file
                genai.delete_file(video_file.name)

                return {
                    'url': url,
                    'file': Path(video_path).name,
                    'summary': response.text.strip()
                }

            except Exception as e:
                return {
                    'url': url,
                    'file': Path(video_path).name if video_path else 'N/A',
                    'summary': f"Error generating summary: {str(e)}"
                }

        def cleanup_all_files(self):
            """Clean up all temporary files"""
            try:
                if self.temp_dir.exists():
                    shutil.rmtree(self.temp_dir)
            except Exception as e:
                pass

        def process(self, video_urls: List[str]) -> Dict:
            """Main processing function"""
            if not video_urls:
                return {"videos": []}

            videos = []
            downloaded_files = []

            try:
                # Phase 1: Download all videos
                for url in video_urls:
                    video_path = self.download_single_video(url)
                    if video_path:
                        downloaded_files.append((url, video_path))
                    else:
                        videos.append({
                            'url': url,
                            'file': 'N/A',
                            'summary': 'Download failed'
                        })

                # Phase 2: Generate summaries
                for url, video_path in downloaded_files:
                    summary_data = self.summarize_video(video_path, url)
                    videos.append(summary_data)

            except Exception as e:
                # Add any remaining videos as failed
                pass
            finally:
                # Phase 3: Cleanup
                self.cleanup_all_files()

            return {"videos": videos}

    # Execute the processing
    processor = VideoProcessor()
    return processor.process(video_urls)


# Example usage
if __name__ == "__main__":
    # Example video URLs - replace with your actual URLs
    example_urls = [
        "https://www.tiktok.com/@example/video/1234567890",
        "https://www.youtube.com/shorts/example123",
        "https://youtu.be/example123"
    ]

    # Process videos with a single function call
    results = summarize_videos(example_urls)

    # Print the JSON result
    import json

    print(json.dumps(results, indent=2))