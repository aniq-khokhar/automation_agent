#!/usr/bin/env python3
"""
Multi-Video Downloader with AI Summarization
Downloads videos from TikTok/YouTube and generates summaries using Gemini 2.0 Flash
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

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def summ_down(video_urls: List[str]) -> List[Dict[str, str]]:
    """
    Download videos from TikTok/YouTube and generate AI summaries

    Args:
        video_urls (List[str]): List of video URLs to process

    Returns:
        List[Dict[str, str]]: List of summary dictionaries with keys:
            - 'url': Original video URL
            - 'video_file': Downloaded filename
            - 'summary': AI-generated summary text
            - 'status': 'success' or 'failed'
    """

    class VideoProcessor:
        def __init__(self):
            # Validate API key
            if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
                raise ValueError("Please set your Gemini API key in the GEMINI_API_KEY variable")

            # Setup temporary directory
            self.temp_dir = Path(tempfile.mkdtemp(prefix="video_summarizer_"))
            print(f"📁 Temporary directory: {self.temp_dir}")

            # Configure Gemini AI
            genai.configure(api_key=GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
            print("🤖 Gemini 2.0 Flash initialized successfully")

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
                print(f"❌ Unsupported platform: {url}")
                return None

            # Choose appropriate options
            opts = self.tiktok_opts if platform == 'tiktok' else self.youtube_opts

            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    print(f"⬇️ Downloading {platform.upper()} video...")

                    # Get info first
                    info = ydl.extract_info(url, download=False)
                    title = info.get('title', 'Unknown')[:50]  # Limit title length
                    print(f"📹 Title: {title}")

                    # Download
                    ydl.download([url])

                    # Find the downloaded file
                    prefix = 'TikTok_' if platform == 'tiktok' else 'YouTube_'
                    downloaded_files = list(self.temp_dir.glob(f"{prefix}*"))

                    if downloaded_files:
                        # Get the most recently created file
                        latest_file = max(downloaded_files, key=lambda p: p.stat().st_mtime)
                        print(f"✅ Downloaded: {latest_file.name}")
                        return str(latest_file)
                    else:
                        print("❌ Downloaded file not found")
                        return None

            except Exception as e:
                print(f"❌ Download failed: {str(e)}")
                return None

        def summarize_video(self, video_path: str, url: str) -> Dict[str, str]:
            """Generate video summary using Gemini 2.0 Flash"""
            try:
                print(f"🤖 Generating AI summary for: {Path(video_path).name}")

                # Upload video to Gemini
                video_file = genai.upload_file(path=video_path)
                print("📤 Video uploaded to Gemini")

                # Wait for processing
                while video_file.state.name == "PROCESSING":
                    print("⏳ Processing video...")
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
                print("🗑️ Cleaned up uploaded file from Gemini")

                return {
                    'url': url,
                    'video_file': Path(video_path).name,
                    'summary': response.text.strip(),
                    'status': 'success'
                }

            except Exception as e:
                print(f"❌ Summarization failed: {str(e)}")
                return {
                    'url': url,
                    'video_file': Path(video_path).name if video_path else 'N/A',
                    'summary': f"Error generating summary: {str(e)}",
                    'status': 'failed'
                }

        def cleanup_all_files(self):
            """Clean up all temporary files"""
            try:
                if self.temp_dir.exists():
                    file_count = len(list(self.temp_dir.iterdir()))
                    shutil.rmtree(self.temp_dir)
                    print(f"🗑️ Cleaned up {file_count} temporary files")
                    print(f"✅ Removed temporary directory: {self.temp_dir}")
            except Exception as e:
                print(f"❌ Cleanup error: {e}")

        def process(self, video_urls: List[str]) -> List[Dict[str, str]]:
            """Main processing function"""
            if not video_urls:
                print("❌ No URLs provided")
                return []

            print(f"🎯 Starting processing of {len(video_urls)} videos")
            print("=" * 60)

            summaries = []
            downloaded_files = []

            try:
                # Phase 1: Download all videos
                print("\n📥 PHASE 1: DOWNLOADING VIDEOS")
                print("-" * 40)

                for i, url in enumerate(video_urls, 1):
                    print(f"\n[{i}/{len(video_urls)}] Processing: {url}")

                    video_path = self.download_single_video(url)
                    if video_path:
                        downloaded_files.append((url, video_path))
                    else:
                        summaries.append({
                            'url': url,
                            'video_file': 'N/A',
                            'summary': 'Download failed',
                            'status': 'failed'
                        })

                print(f"\n✅ Downloaded {len(downloaded_files)} out of {len(video_urls)} videos")

                # Phase 2: Generate summaries
                print("\n🤖 PHASE 2: GENERATING AI SUMMARIES")
                print("-" * 40)

                for i, (url, video_path) in enumerate(downloaded_files, 1):
                    print(f"\n[{i}/{len(downloaded_files)}] Summarizing: {Path(video_path).name}")
                    summary_data = self.summarize_video(video_path, url)
                    summaries.append(summary_data)

            except KeyboardInterrupt:
                print("\n\n🛑 Process interrupted by user")
            except Exception as e:
                print(f"\n❌ Error during processing: {e}")
            finally:
                # Phase 3: Cleanup
                print("\n🗑️ PHASE 3: CLEANING UP")
                print("-" * 40)
                self.cleanup_all_files()

            # Print summary report
            self.print_summary_report(summaries)

            # Save to file
            self.save_summaries_to_file(summaries)

            return summaries

        def print_summary_report(self, summaries: List[Dict[str, str]]):
            """Print a formatted summary report"""
            print("\n" + "=" * 80)
            print("📊 VIDEO SUMMARY REPORT")
            print("=" * 80)

            successful = sum(1 for s in summaries if s['status'] == 'success')
            failed = len(summaries) - successful

            print(f"Total videos processed: {len(summaries)}")
            print(f"✅ Successful summaries: {successful}")
            print(f"❌ Failed summaries: {failed}")
            print("\n" + "-" * 80)

            for i, summary in enumerate(summaries, 1):
                print(f"\n🎬 VIDEO {i}")
                print(f"URL: {summary['url']}")
                print(f"File: {summary['video_file']}")
                print(f"Status: {summary['status'].upper()}")
                print(f"Summary:")
                print("-" * 40)
                print(summary['summary'])
                print("-" * 40)

            print("\n" + "=" * 80)

        def save_summaries_to_file(self, summaries: List[Dict[str, str]]):
            """Save summaries to a text file"""
            filename = f"video_summaries_{int(time.time())}.txt"
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write("VIDEO SUMMARIES REPORT\n")
                    f.write("=" * 50 + "\n\n")
                    for i, summary in enumerate(summaries, 1):
                        f.write(f"VIDEO {i}\n")
                        f.write(f"URL: {summary['url']}\n")
                        f.write(f"File: {summary['video_file']}\n")
                        f.write(f"Status: {summary['status']}\n")
                        f.write(f"Summary:\n{summary['summary']}\n")
                        f.write("-" * 50 + "\n\n")
                print(f"💾 Summaries saved to: {filename}")
            except Exception as e:
                print(f"❌ Failed to save summaries: {e}")

    # Execute the processing
    print("🎥 Multi-Video AI Summarizer 🤖")
    print("🎵 TikTok + 🎬 YouTube → 📝 AI Summaries")
    print("=" * 50)

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

    print(f"\n🎉 Completed! Processed {len(results)} videos")
    print("Check the generated text file for detailed summaries.")