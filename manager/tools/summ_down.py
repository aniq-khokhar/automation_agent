# #!/usr/bin/env python3
# """
# Multi-Video Downloader with AI Summarization
# Downloads videos from TikTok/YouTube and generates summaries using Gemini 2.0 Flash
# Silent version - returns JSON structure instead of console output
# """
#
# import os
# import re
# import tempfile
# import shutil
# import time
# from pathlib import Path
# import yt_dlp
# import google.generativeai as genai
# from dotenv import load_dotenv
#
# # Configuration - Set your API key here
# load_dotenv()
#
# GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  # Replace with your actual API key
#
#
# def summ_down(video_urls: list[str]) -> dict:
#     """
#     Download videos from TikTok/YouTube and generate AI summaries
#
#     Args:
#         video_urls (List[str]): List of video URLs to process
#
#     Returns:
#         Dict: JSON structure with format:
#         {
#             "videos": [
#                 {
#                     "url": "",
#                     "file": "",
#                     "summary": ""
#                 },
#                 ...
#             ]
#         }
#     """
#
#     class VideoProcessor:
#         def __init__(self):
#             # Validate API key
#             if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
#                 raise ValueError("Please set your Gemini API key in the GEMINI_API_KEY variable")
#
#             # Setup temporary directory
#             self.temp_dir = Path(tempfile.mkdtemp(prefix="video_summarizer_"))
#
#             # Configure Gemini AI
#             genai.configure(api_key=GEMINI_API_KEY)
#             self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
#
#             # Download configurations
#             self.tiktok_opts = {
#                 'outtmpl': str(self.temp_dir / 'TikTok_%(title)s_%(id)s.%(ext)s'),
#                 'format': 'best[ext=mp4]/best',
#                 'writeinfojson': False,
#                 'writesubtitles': False,
#                 'quiet': True,
#             }
#
#             self.youtube_opts = {
#                 'outtmpl': str(self.temp_dir / 'YouTube_%(title)s_%(id)s.%(ext)s'),
#                 'format': 'best[height<=1080][ext=mp4]/best[ext=mp4]',
#                 'writeinfojson': False,
#                 'writesubtitles': False,
#                 'quiet': True,
#             }
#
#         def detect_platform(self, url: str) -> str:
#             """Detect video platform"""
#             tiktok_patterns = [
#                 r'https?://(?:www\.)?tiktok\.com/@[\w.-]+/video/\d+',
#                 r'https?://(?:vm|vt)\.tiktok\.com/[\w.-]+',
#                 r'https?://(?:www\.)?tiktok\.com/t/[\w.-]+',
#             ]
#
#             youtube_patterns = [
#                 r'https?://(?:www\.)?youtube\.com/shorts/[\w-]+',
#                 r'https?://youtu\.be/[\w-]+',
#                 r'https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+',
#             ]
#
#             if any(re.match(pattern, url) for pattern in tiktok_patterns):
#                 return 'tiktok'
#             elif any(re.match(pattern, url) for pattern in youtube_patterns):
#                 return 'youtube'
#             return 'unknown'
#
#         def download_single_video(self, url: str) -> str:
#             """Download a single video and return the file path"""
#             platform = self.detect_platform(url)
#
#             if platform not in ['tiktok', 'youtube']:
#                 return None
#
#             # Choose appropriate options
#             opts = self.tiktok_opts if platform == 'tiktok' else self.youtube_opts
#
#             try:
#                 with yt_dlp.YoutubeDL(opts) as ydl:
#                     # Get info first
#                     info = ydl.extract_info(url, download=False)
#
#                     # Download
#                     ydl.download([url])
#
#                     # Find the downloaded file
#                     prefix = 'TikTok_' if platform == 'tiktok' else 'YouTube_'
#                     downloaded_files = list(self.temp_dir.glob(f"{prefix}*"))
#
#                     if downloaded_files:
#                         # Get the most recently created file
#                         latest_file = max(downloaded_files, key=lambda p: p.stat().st_mtime)
#                         return str(latest_file)
#                     else:
#                         return None
#
#             except Exception as e:
#                 return None
#
#         def summarize_video(self, video_path: str, url: str) -> dict[str, str]:
#             """Generate video summary using Gemini 2.0 Flash"""
#             try:
#                 # Upload video to Gemini
#                 video_file = genai.upload_file(path=video_path)
#
#                 # Wait for processing
#                 while video_file.state.name == "PROCESSING":
#                     time.sleep(2)
#                     video_file = genai.get_file(video_file.name)
#
#                 if video_file.state.name == "FAILED":
#                     raise ValueError("Video processing failed")
#
#                 # Generate summary
#                 prompt = """
#                 Analyze this video and provide a comprehensive summary including:
#                 1. Main content/topic
#                 2. Key actions or events
#                 3. Notable objects, people, or scenes
#                 4. Overall mood or theme
#                 5. Duration and pacing
#
#                 Keep the summary concise but informative (2-3 paragraphs maximum).
#                 """
#
#                 response = self.model.generate_content([video_file, prompt])
#
#                 # Clean up uploaded file
#                 genai.delete_file(video_file.name)
#
#                 return {
#                     'url': url,
#                     'file': Path(video_path).name,
#                     'summary': response.text.strip()
#                 }
#
#             except Exception as e:
#                 return {
#                     'url': url,
#                     'file': Path(video_path).name if video_path else 'N/A',
#                     'summary': f"Error generating summary: {str(e)}"
#                 }
#
#         def cleanup_all_files(self):
#             """Clean up all temporary files"""
#             try:
#                 if self.temp_dir.exists():
#                     shutil.rmtree(self.temp_dir)
#             except Exception as e:
#                 pass
#
#         def process(self, video_urls: list[str]) -> dict:
#             """Main processing function"""
#             if not video_urls:
#                 return {"videos": []}
#
#             videos = []
#             downloaded_files = []
#
#             try:
#                 # Phase 1: Download all videos
#                 for url in video_urls:
#                     video_path = self.download_single_video(url)
#                     if video_path:
#                         downloaded_files.append((url, video_path))
#                     else:
#                         videos.append({
#                             'url': url,
#                             'file': 'N/A',
#                             'summary': 'Download failed'
#                         })
#
#                 # Phase 2: Generate summaries
#                 for url, video_path in downloaded_files:
#                     summary_data = self.summarize_video(video_path, url)
#                     videos.append(summary_data)
#
#             except Exception as e:
#                 # Add any remaining videos as failed
#                 pass
#             finally:
#                 # Phase 3: Cleanup
#                 self.cleanup_all_files()
#
#             return {"videos": videos}
#
#     # Execute the processing
#     processor = VideoProcessor()
#     return processor.process(video_urls)
#
#
# # Example usage
# if __name__ == "__main__":
#     # Example video URLs - replace with your actual URLs
#     example_urls = [
#         "https://www.youtube.com/shorts/rqLEUxeOQWo",
#         "https://www.youtube.com/shorts/QsQYW-oN1Ik",
#     ]
#
#     # Process videos with a single function call
#     results = summ_down(example_urls)
#
#     # Print the JSON result
#     import json
#
#     print(json.dumps(results, indent=2))

# !/usr/bin/env python3
"""
Multi-Video Downloader with AI Summarization
Downloads videos from TikTok/YouTube and generates summaries using Gemini 2.0 Flash
Silent version - returns JSON structure instead of console output
"""




# import os
# import re
# import tempfile
# import shutil
# import time
# from pathlib import Path
# import yt_dlp
# import google.generativeai as genai
# from dotenv import load_dotenv
#
# # Configuration - Set your API key here
# load_dotenv()
#
# GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  # Replace with your actual API key
#
#
# def summ_down(video_urls: list[str]) -> dict:
#     """
#     Download videos from TikTok/YouTube and generate AI summaries
#
#     Args:
#         video_urls (List[str]): List of video URLs to process
#
#     Returns:
#         Dict: JSON structure with format:
#         {
#             "videos": [
#                 {
#                     "url": "",
#                     "file": "",
#                     "summary": ""
#                 },
#                 ...
#             ]
#         }
#     """
#
#     class VideoProcessor:
#         def __init__(self):
#             print("🚀 Initializing Video Processor...")
#
#             # Validate API key
#             if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
#                 raise ValueError("Please set your Gemini API key in the GEMINI_API_KEY variable")
#             print("✅ Gemini API key validated")
#
#             # Setup temporary directory
#             self.temp_dir = Path(tempfile.mkdtemp(prefix="video_summarizer_"))
#             print(f"📂 Temporary directory created: {self.temp_dir}")
#
#             # Configure Gemini AI
#             genai.configure(api_key=GEMINI_API_KEY)
#             self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
#             print("🤖 Gemini AI model configured")
#
#             # Download configurations
#             self.tiktok_opts = {
#                 'outtmpl': str(self.temp_dir / 'TikTok_%(title)s_%(id)s.%(ext)s'),
#                 'format': 'best[ext=mp4]/best',
#                 'writeinfojson': False,
#                 'writesubtitles': False,
#                 'quiet': True,
#             }
#
#             self.youtube_opts = {
#                 'outtmpl': str(self.temp_dir / 'YouTube_%(title)s_%(id)s.%(ext)s'),
#                 'format': 'best[height<=1080][ext=mp4]/best[ext=mp4]',
#                 'writeinfojson': False,
#                 'writesubtitles': False,
#                 'quiet': True,
#             }
#             print("⚙️ Download configurations set up")
#
#         def detect_platform(self, url: str) -> str:
#             """Detect video platform"""
#             print(f"🔍 Detecting platform for: {url}")
#
#             tiktok_patterns = [
#                 r'https?://(?:www\.)?tiktok\.com/@[\w.-]+/video/\d+',
#                 r'https?://(?:vm|vt)\.tiktok\.com/[\w.-]+',
#                 r'https?://(?:www\.)?tiktok\.com/t/[\w.-]+',
#             ]
#
#             youtube_patterns = [
#                 r'https?://(?:www\.)?youtube\.com/shorts/[\w-]+',
#                 r'https?://youtu\.be/[\w-]+',
#                 r'https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+',
#             ]
#
#             if any(re.match(pattern, url) for pattern in tiktok_patterns):
#                 platform = 'tiktok'
#             elif any(re.match(pattern, url) for pattern in youtube_patterns):
#                 platform = 'youtube'
#             else:
#                 platform = 'unknown'
#
#             print(f"🌐 Platform detected: {platform}")
#             return platform
#
#         def download_single_video(self, url: str) -> str:
#             """Download a single video and return the file path"""
#             print(f"⬇️ Starting download for: {url}")
#
#             platform = self.detect_platform(url)
#
#             if platform not in ['tiktok', 'youtube']:
#                 print(f"❌ Unsupported platform: {platform}")
#                 return None
#
#             # Choose appropriate options
#             opts = self.tiktok_opts if platform == 'tiktok' else self.youtube_opts
#             print(f"⚙️ Using {platform} download options")
#
#             try:
#                 with yt_dlp.YoutubeDL(opts) as ydl:
#                     print("📊 Extracting video info...")
#                     # Get info first
#                     info = ydl.extract_info(url, download=False)
#                     title = info.get('title', 'Unknown')
#                     duration = info.get('duration', 0)
#                     print(f"📹 Video info - Title: {title}, Duration: {duration}s")
#
#                     print("⬇️ Starting actual download...")
#                     # Download
#                     ydl.download([url])
#                     print("✅ Download completed")
#
#                     # Find the downloaded file
#                     prefix = 'TikTok_' if platform == 'tiktok' else 'YouTube_'
#                     downloaded_files = list(self.temp_dir.glob(f"{prefix}*"))
#                     print(f"🔍 Looking for files with prefix: {prefix}")
#                     print(f"📁 Found {len(downloaded_files)} files")
#
#                     if downloaded_files:
#                         # Get the most recently created file
#                         latest_file = max(downloaded_files, key=lambda p: p.stat().st_mtime)
#                         file_size = latest_file.stat().st_size / 1024 / 1024  # MB
#                         print(f"✅ Downloaded file: {latest_file.name} ({file_size:.2f} MB)")
#                         return str(latest_file)
#                     else:
#                         print("❌ No downloaded files found")
#                         return None
#
#             except Exception as e:
#                 print(f"❌ Download failed with error: {str(e)}")
#                 return None
#
#         def summarize_video(self, video_path: str, url: str) -> dict[str, str]:
#             """Generate video summary using Gemini 2.0 Flash"""
#             print(f"🤖 Starting AI summarization for: {Path(video_path).name}")
#
#             try:
#                 # Upload video to Gemini
#                 print("☁️ Uploading video to Gemini...")
#                 video_file = genai.upload_file(path=video_path)
#                 print(f"✅ Upload successful, file ID: {video_file.name}")
#
#                 # Wait for processing
#                 print("⏳ Waiting for Gemini processing...")
#                 processing_time = 0
#                 while video_file.state.name == "PROCESSING":
#                     time.sleep(2)
#                     processing_time += 2
#                     video_file = genai.get_file(video_file.name)
#                     print(f"   Processing... ({processing_time}s elapsed)")
#
#                 if video_file.state.name == "FAILED":
#                     print("❌ Gemini video processing failed")
#                     raise ValueError("Video processing failed")
#
#                 print("✅ Gemini processing complete!")
#
#                 # Generate summary
#                 print("📝 Generating AI summary...")
#                 prompt = """
#                 You are a Video Analysis & Viral Pattern Extraction Agent.
#
#                 INSTRUCTIONS:
#                 - Analyze the uploaded video directly (not summaries, not transcripts).
#                 - Identify viral ingredients, storytelling DNA, emotional triggers, pacing, editing style, and hooks.
#                 - Capture the genre, theme, target emotions, POV, setting, characters, conflict, stakes, and payoff.
#                 - Output ONLY a single JSON object. Do not add any extra text, explanations, or formatting.
#                 - All array fields must contain at least one value.
#                 - If a field cannot be determined, fill it with "unknown" (never leave fields empty).
#                 - Follow the schema exactly.
#
#                 OUTPUT SCHEMA:
#
#                 {
#                   "viral_ingredients": ["<ingredient_1>", "<ingredient_2>", "..."],
#                   "video_hooks": ["<hook_1>", "<hook_2>", "..."],
#                   "hook_pattern": "<concise_description>",
#                   "storytelling_blueprint": {
#                     "genre": "<genre>",
#                     "theme": "<theme>",
#                     "target_emotion": "<emotion>",
#                     "pov": "<point_of_view>",
#                     "setting": "<setting>",
#                     "characters": ["<char_1>", "<char_2>", "..."],
#                     "conflict": "<conflict>",
#                     "escalating_stakes": "<description>",
#                     "payoff": "<resolution_or_twist>"
#                   }
#                 }
#
#                 """
#
#                 response = self.model.generate_content([video_file, prompt])
#                 print("✅ Summary generated successfully!")
#
#                 # Clean up uploaded file
#                 print("🗑️ Cleaning up Gemini file...")
#                 genai.delete_file(video_file.name)
#                 print("✅ Gemini file deleted")
#
#                 return {
#                     'url': url,
#                     'file': Path(video_path).name,
#                     'summary': response.text.strip()
#                 }
#
#             except Exception as e:
#                 print(f"❌ Summarization failed with error: {str(e)}")
#                 return {
#                     'url': url,
#                     'file': Path(video_path).name if video_path else 'N/A',
#                     'summary': f"Error generating summary: {str(e)}"
#                 }
#
#         def cleanup_all_files(self):
#             """Clean up all temporary files"""
#             print("🧹 Starting cleanup of temporary files...")
#             try:
#                 if self.temp_dir.exists():
#                     file_count = len(list(self.temp_dir.glob("*")))
#                     print(f"🗑️ Deleting {file_count} temporary files...")
#                     shutil.rmtree(self.temp_dir)
#                     print("✅ Temporary directory cleaned up")
#                 else:
#                     print("ℹ️ Temporary directory already cleaned")
#             except Exception as e:
#                 print(f"⚠️ Cleanup failed: {str(e)}")
#
#         def process(self, video_urls: list[str]) -> dict:
#             """Main processing function"""
#             print(f"🎬 Starting processing of {len(video_urls)} videos...")
#
#             if not video_urls:
#                 print("⚠️ No video URLs provided")
#                 return {"videos": []}
#
#             videos = []
#             downloaded_files = []
#
#             try:
#                 # Phase 1: Download all videos
#                 print("\n📥 PHASE 1: Downloading videos...")
#                 for i, url in enumerate(video_urls, 1):
#                     print(f"\n--- Video {i}/{len(video_urls)} ---")
#                     video_path = self.download_single_video(url)
#                     if video_path:
#                         downloaded_files.append((url, video_path))
#                         print(f"✅ Video {i} download successful")
#                     else:
#                         print(f"❌ Video {i} download failed")
#                         videos.append({
#                             'url': url,
#                             'file': 'N/A',
#                             'summary': 'Download failed'
#                         })
#
#                 print(f"\n📊 Download phase complete: {len(downloaded_files)} successful, {len(videos)} failed")
#
#                 # Phase 2: Generate summaries
#                 print(f"\n🤖 PHASE 2: Generating AI summaries...")
#                 for i, (url, video_path) in enumerate(downloaded_files, 1):
#                     print(f"\n--- Summarizing {i}/{len(downloaded_files)} ---")
#                     summary_data = self.summarize_video(video_path, url)
#                     videos.append(summary_data)
#                     print(f"✅ Video {i} summarization complete")
#
#                 print(f"\n📊 Summary phase complete!")
#
#             except Exception as e:
#                 print(f"❌ Processing failed with error: {str(e)}")
#             finally:
#                 # Phase 3: Cleanup
#                 print(f"\n🧹 PHASE 3: Cleanup...")
#                 self.cleanup_all_files()
#
#             successful = len([v for v in videos if 'Error' not in v.get('summary', '')])
#             failed = len(videos) - successful
#             print(f"\n🎉 Processing complete! Results: {successful} successful, {failed} failed")
#
#             return {"videos": videos}
#
#     # Execute the processing
#     processor = VideoProcessor()
#     return processor.process(video_urls)
#
#
# # Example usage
# if __name__ == "__main__":
#     print("🎬 Multi-Video Downloader with AI Summarization")
#     print("=" * 50)
#
#     # Example video URLs - replace with your actual URLs
#     example_urls = [
#         "https://www.youtube.com/shorts/rqLEUxeOQWo",
#         "https://www.youtube.com/shorts/QsQYW-oN1Ik",
#     ]
#
#     # Process videos with a single function call
#     results = summ_down(example_urls)
#
#     # Print the JSON result
#     import json
#
#     print("\n📋 FINAL RESULTS:")
#     print("=" * 50)
#     print(json.dumps(results, indent=2))


import os
import re
import tempfile
import shutil
import time
import json
from pathlib import Path
import yt_dlp
import google.generativeai as genai
from dotenv import load_dotenv

# Configuration - Set your API key here
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  # Replace with your actual API key


def summ_down(video_urls: list[str]) -> list[dict]:
    """
    Download videos from TikTok/YouTube and generate AI viral analysis

    Args:
        video_urls (List[str]): List of video URLs to process

    Returns:
        List[Dict]: List of videos with format:
        [
            {
                "url": "",
                "analysis": {
                    "viral_ingredients": [...],
                    "video_hooks": [...],
                    "hook_pattern": "",
                    "storytelling_blueprint": {...}
                }
            },
            ...
        ]
    """

    class VideoProcessor:
        def __init__(self):
            print("🚀 Initializing Video Processor...")
            self.start_time = time.time()

            # Validate API key
            if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
                raise ValueError("Please set your Gemini API key in the GEMINI_API_KEY variable")
            print("✅ Gemini API key validated")

            # Setup temporary directory
            self.temp_dir = Path(tempfile.mkdtemp(prefix="video_summarizer_"))
            print(f"📂 Temporary directory created: {self.temp_dir}")

            # Configure Gemini AI
            genai.configure(api_key=GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
            print("🤖 Gemini AI model configured")

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
            print("⚙️ Download configurations set up")

        def detect_platform(self, url: str) -> str:
            """Detect video platform"""
            print(f"🔍 Detecting platform for: {url}")

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
                platform = 'tiktok'
            elif any(re.match(pattern, url) for pattern in youtube_patterns):
                platform = 'youtube'
            else:
                platform = 'unknown'

            print(f"🌐 Platform detected: {platform}")
            return platform

        def download_single_video(self, url: str) -> str:
            """Download a single video and return the file path"""
            print(f"⬇️ Starting download for: {url}")

            platform = self.detect_platform(url)

            if platform not in ['tiktok', 'youtube']:
                print(f"❌ Unsupported platform: {platform}")
                return None

            # Choose appropriate options
            opts = self.tiktok_opts if platform == 'tiktok' else self.youtube_opts
            print(f"⚙️ Using {platform} download options")

            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    print("📊 Extracting video info...")
                    # Get info first
                    info = ydl.extract_info(url, download=False)
                    title = info.get('title', 'Unknown')
                    duration = info.get('duration', 0)
                    print(f"📹 Video info - Title: {title}, Duration: {duration}s")

                    print("⬇️ Starting actual download...")
                    # Download
                    ydl.download([url])
                    print("✅ Download completed")

                    # Find the downloaded file
                    prefix = 'TikTok_' if platform == 'tiktok' else 'YouTube_'
                    downloaded_files = list(self.temp_dir.glob(f"{prefix}*"))
                    print(f"🔍 Looking for files with prefix: {prefix}")
                    print(f"📁 Found {len(downloaded_files)} files")

                    if downloaded_files:
                        # Get the most recently created file
                        latest_file = max(downloaded_files, key=lambda p: p.stat().st_mtime)
                        file_size = latest_file.stat().st_size / 1024 / 1024  # MB
                        print(f"✅ Downloaded file: {latest_file.name} ({file_size:.2f} MB)")
                        return str(latest_file)
                    else:
                        print("❌ No downloaded files found")
                        return None

            except Exception as e:
                print(f"❌ Download failed with error: {str(e)}")
                return None

        def parse_json_response(self, response_text: str) -> dict:
            """Parse and validate the JSON response from Gemini"""
            try:
                # Clean the response text - remove any markdown formatting or extra text
                cleaned_text = response_text.strip()

                # If response starts with ```json, extract just the JSON part
                if cleaned_text.startswith('```json'):
                    start_idx = cleaned_text.find('{')
                    end_idx = cleaned_text.rfind('}') + 1
                    if start_idx != -1 and end_idx != 0:
                        cleaned_text = cleaned_text[start_idx:end_idx]

                # Parse JSON
                analysis_data = json.loads(cleaned_text)

                # Validate required fields
                required_fields = ['viral_ingredients', 'video_hooks', 'hook_pattern', 'storytelling_blueprint']
                for field in required_fields:
                    if field not in analysis_data:
                        raise ValueError(f"Missing required field: {field}")

                # Validate storytelling_blueprint structure
                blueprint = analysis_data['storytelling_blueprint']
                blueprint_fields = ['genre', 'theme', 'target_emotion', 'pov', 'setting', 'characters', 'conflict',
                                    'escalating_stakes', 'payoff']
                for field in blueprint_fields:
                    if field not in blueprint:
                        raise ValueError(f"Missing storytelling_blueprint field: {field}")

                return analysis_data

            except json.JSONDecodeError as e:
                print(f"⚠️ JSON parsing error: {str(e)}")
                print(f"Raw response: {response_text[:200]}...")
                return self.create_error_analysis(f"Invalid JSON response: {str(e)}")
            except Exception as e:
                print(f"⚠️ Analysis validation error: {str(e)}")
                return self.create_error_analysis(f"Analysis validation failed: {str(e)}")

        def create_error_analysis(self, error_msg: str) -> dict:
            """Create a fallback analysis structure for errors"""
            return {
                "viral_ingredients": ["analysis_failed"],
                "video_hooks": ["unable_to_analyze"],
                "hook_pattern": f"Error: {error_msg}",
                "storytelling_blueprint": {
                    "genre": "unknown",
                    "theme": "unknown",
                    "target_emotion": "unknown",
                    "pov": "unknown",
                    "setting": "unknown",
                    "characters": ["unknown"],
                    "conflict": "unknown",
                    "escalating_stakes": "unknown",
                    "payoff": "unknown"
                }
            }

        def analyze_video(self, video_path: str, url: str) -> dict:
            """Generate video analysis using Gemini 2.0 Flash"""
            print(f"🤖 Starting AI analysis for: {Path(video_path).name}")

            try:
                # Upload video to Gemini
                print("☁️ Uploading video to Gemini...")
                video_file = genai.upload_file(path=video_path)
                print(f"✅ Upload successful, file ID: {video_file.name}")

                # Wait for processing
                print("⏳ Waiting for Gemini processing...")
                processing_time = 0
                while video_file.state.name == "PROCESSING":
                    time.sleep(2)
                    processing_time += 2
                    video_file = genai.get_file(video_file.name)
                    print(f"   Processing... ({processing_time}s elapsed)")

                if video_file.state.name == "FAILED":
                    print("❌ Gemini video processing failed")
                    raise ValueError("Video processing failed")

                print("✅ Gemini processing complete!")

                # Generate analysis
                print("📝 Generating AI analysis...")
                prompt = """
                You are a Video Analysis & Viral Pattern Extraction Agent.  

                INSTRUCTIONS:  
                - Analyze the uploaded video directly (not summaries, not transcripts).  
                - Identify viral ingredients, storytelling DNA, emotional triggers, pacing, editing style, and hooks.  
                - Capture the genre, theme, target emotions, POV, setting, characters, conflict, stakes, and payoff.  
                - Output ONLY a single JSON object. Do not add any extra text, explanations, or formatting.  
                - All array fields must contain at least one value.  
                - If a field cannot be determined, fill it with "unknown" (never leave fields empty).  
                - Follow the schema exactly.  

                OUTPUT SCHEMA:  

                {
                  "viral_ingredients": ["<ingredient_1>", "<ingredient_2>", "..."],
                  "video_hooks": ["<hook_1>", "<hook_2>", "..."],
                  "hook_pattern": "<concise_description>",
                  "storytelling_blueprint": {
                    "genre": "<genre>",
                    "theme": "<theme>",
                    "target_emotion": "<emotion>",
                    "pov": "<point_of_view>",
                    "setting": "<setting>",
                    "characters": ["<char_1>", "<char_2>", "..."],
                    "conflict": "<conflict>",
                    "escalating_stakes": "<description>",
                    "payoff": "<resolution_or_twist>"
                  }
                }

                """

                response = self.model.generate_content([video_file, prompt])
                print("✅ Analysis generated successfully!")

                # Clean up uploaded file
                print("🗑️ Cleaning up Gemini file...")
                genai.delete_file(video_file.name)
                print("✅ Gemini file deleted")

                # Parse the JSON response
                analysis_data = self.parse_json_response(response.text)

                return {
                    'url': url,
                    'analysis': analysis_data
                }

            except Exception as e:
                print(f"❌ Analysis failed with error: {str(e)}")
                return {
                    'url': url,
                    'analysis': self.create_error_analysis(str(e))
                }

        def format_processing_time(self, seconds: float) -> str:
            """Format processing time as HH:MM:SS"""
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"

        def cleanup_all_files(self):
            """Clean up all temporary files"""
            print("🧹 Starting cleanup of temporary files...")
            try:
                if self.temp_dir.exists():
                    file_count = len(list(self.temp_dir.glob("*")))
                    print(f"🗑️ Deleting {file_count} temporary files...")
                    shutil.rmtree(self.temp_dir)
                    print("✅ Temporary directory cleaned up")
                else:
                    print("ℹ️ Temporary directory already cleaned")
            except Exception as e:
                print(f"⚠️ Cleanup failed: {str(e)}")

        def process(self, video_urls: list[str]) -> list[dict]:
            """Main processing function"""
            print(f"🎬 Starting processing of {len(video_urls)} videos...")

            if not video_urls:
                print("⚠️ No video URLs provided")
                return []

            videos = []
            downloaded_files = []

            try:
                # Phase 1: Download all videos
                print("\n📥 PHASE 1: Downloading videos...")
                for i, url in enumerate(video_urls, 1):
                    print(f"\n--- Video {i}/{len(video_urls)} ---")
                    video_path = self.download_single_video(url)
                    if video_path:
                        downloaded_files.append((url, video_path))
                        print(f"✅ Video {i} download successful")
                    else:
                        print(f"❌ Video {i} download failed")
                        videos.append({
                            'url': url,
                            'analysis': self.create_error_analysis('Download failed')
                        })

                print(f"\n📊 Download phase complete: {len(downloaded_files)} successful, {len(videos)} failed")

                # Phase 2: Generate analyses
                print(f"\n🤖 PHASE 2: Generating AI analyses...")
                for i, (url, video_path) in enumerate(downloaded_files, 1):
                    print(f"\n--- Analyzing {i}/{len(downloaded_files)} ---")
                    analysis_data = self.analyze_video(video_path, url)
                    videos.append(analysis_data)
                    print(f"✅ Video {i} analysis complete")

                print(f"\n📊 Analysis phase complete!")

            except Exception as e:
                print(f"❌ Processing failed with error: {str(e)}")
            finally:
                # Phase 3: Cleanup
                print(f"\n🧹 PHASE 3: Cleanup...")
                self.cleanup_all_files()

            successful = len([v for v in videos if 'Error' not in str(v.get('analysis', {}).get('hook_pattern', ''))])
            failed = len(videos) - successful
            processing_time = self.format_processing_time(time.time() - self.start_time)

            print(f"\n🎉 Processing complete! Results: {successful} successful, {failed} failed")
            print(f"⏱️ Total processing time: {processing_time}")

            return videos

    # Execute the processing
    processor = VideoProcessor()
    return processor.process(video_urls)


def print_analysis_summary(results: list[dict]):
    """Print a formatted summary of the analysis results"""
    print("\n" + "=" * 80)
    print("🎬 VIDEO ANALYSIS SUMMARY")
    print("=" * 80)

    total_videos = len(results)
    successful = len([v for v in results if 'Error' not in str(v.get('analysis', {}).get('hook_pattern', ''))])
    failed = total_videos - successful

    print(f"📊 Total Videos: {total_videos}")
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")

    print("\n" + "-" * 80)

    for i, video in enumerate(results, 1):
        print(f"\n🎥 VIDEO {i}: {video['url']}")

        analysis = video['analysis']
        if 'Error' not in str(analysis.get('hook_pattern', '')):
            print(
                f"🔥 Viral Ingredients: {', '.join(analysis['viral_ingredients'][:3])}{'...' if len(analysis['viral_ingredients']) > 3 else ''}")
            print(
                f"🪝 Hook Pattern: {analysis['hook_pattern'][:50]}{'...' if len(analysis['hook_pattern']) > 50 else ''}")
            print(f"🎭 Genre: {analysis['storytelling_blueprint']['genre']}")
            print(f"🎯 Target Emotion: {analysis['storytelling_blueprint']['target_emotion']}")
        else:
            print(f"❌ Error: {analysis.get('hook_pattern', 'Unknown error')}")


# Example usage
if __name__ == "__main__":
    print("🎬 Multi-Video Downloader with AI Viral Analysis")
    print("=" * 50)

    # Example video URLs - replace with your actual URLs
    example_urls = [
        "https://www.youtube.com/shorts/rqLEUxeOQWo",
        "https://www.youtube.com/shorts/QsQYW-oN1Ik",
    ]

    # Process videos with a single function call
    results = summ_down(example_urls)

    # Print the structured summary
    print_analysis_summary(results)

    # Print the full JSON result
    print("\n" + "=" * 80)
    print("📋 FULL JSON RESULTS:")
    print("=" * 80)
    print(json.dumps(results, indent=2))