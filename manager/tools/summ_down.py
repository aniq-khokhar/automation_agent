#!/usr/bin/env python3
"""
Multi-Video Downloader with AI Summarization
Downloads videos from TikTok/YouTube and generates summaries using Gemini 2.5 Pro
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


class VideoDownloaderSummarizer:
    def __init__(self, gemini_api_key: str):
        """
        Initialize the video downloader with AI summarization

        Args:
            gemini_api_key (str): Google Gemini API key
        """
        # Setup temporary directory
        self.temp_dir = Path(tempfile.mkdtemp(prefix="video_summarizer_"))
        print(f"📁 Temporary directory: {self.temp_dir}")

        # Configure Gemini AI
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        print("🤖 Gemini 2.5 Pro initialized successfully")

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
        """
        Download a single video and return the file path

        Args:
            url (str): Video URL

        Returns:
            str: Path to downloaded video file, or None if failed
        """
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
        """
        Generate video summary using Gemini 2.5 Pro

        Args:
            video_path (str): Path to video file
            url (str): Original video URL

        Returns:
            dict: Summary information
        """
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

    def download_and_summarize_videos(self, video_urls: List[str]) -> List[Dict[str, str]]:
        """
        Main function: Download videos and generate summaries

        Args:
            video_urls (list): List of video URLs

        Returns:
            list: List of summary dictionaries
        """
        if not video_urls:
            print("❌ No URLs provided")
            return []

        print(f"🎯 Starting processing of {len(video_urls)} videos")
        print("=" * 60)

        summaries = []
        downloaded_files = []

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

        # Phase 3: Cleanup
        print("\n🗑️ PHASE 3: CLEANING UP")
        print("-" * 40)
        self.cleanup_all_files()

        return summaries

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


def main():
    """Main function"""
    print("🎥 Multi-Video AI Summarizer 🤖")
    print("🎵 TikTok + 🎬 YouTube → 📝 AI Summaries")
    print("=" * 50)

    # Get Gemini API key
    api_key = input("Enter your Google Gemini API key: ").strip()
    if not api_key:
        print("❌ API key is required")
        return

    try:
        # Initialize downloader
        downloader = VideoDownloaderSummarizer(api_key)

        # Get video URLs
        print("\nEnter video URLs (one per line, empty line to finish):")
        video_urls = []
        while True:
            url = input().strip()
            if not url:
                break
            video_urls.append(url)

        if not video_urls:
            print("❌ No URLs provided")
            return

        # Process videos
        summaries = downloader.download_and_summarize_videos(video_urls)

        # Display results
        downloader.print_summary_report(summaries)

        # Ask if user wants to save results
        save_choice = input("\nSave summaries to file? (y/n): ").lower().strip()
        if save_choice == 'y':
            filename = f"video_summaries_{int(time.time())}.txt"
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

    except KeyboardInterrupt:
        print("\n\n🛑 Process interrupted by user")
        try:
            downloader.cleanup_all_files()
        except:
            pass
    except Exception as e:
        print(f"\n❌ Error: {e}")
        try:
            downloader.cleanup_all_files()
        except:
            pass


if __name__ == "__main__":
    main()