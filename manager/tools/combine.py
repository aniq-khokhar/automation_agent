#!/usr/bin/env python3
"""
Unified Video Downloader
A Python script to download TikTok videos and YouTube Shorts using yt-dlp
"""

import os
import sys
import re
import tempfile
import shutil
import threading
import time
from pathlib import Path
import yt_dlp
from urllib.parse import urlparse, parse_qs


class UnifiedVideoDownloader:
    def __init__(self, temp_cleanup_minutes=1):
        """
        Initialize the unified video downloader with temporary storage

        Args:
            temp_cleanup_minutes (float): Minutes after which to delete downloaded files
        """
        # Create a single temporary directory for all downloads
        self.temp_dir = Path(tempfile.mkdtemp(prefix="video_downloader_"))
        self.cleanup_minutes = temp_cleanup_minutes
        self.cleanup_seconds = temp_cleanup_minutes * 60

        print(f"📁 Temporary download directory: {self.temp_dir}")
        print(f"🗑️ Files will be automatically deleted after {temp_cleanup_minutes} minute(s)")

        # Track downloaded files for cleanup
        self.downloaded_files = []
        self.cleanup_timers = []

        # Configuration for both platforms (using temp directory)
        self.tiktok_opts = {
            'outtmpl': str(self.temp_dir / 'TikTok_%(title)s.%(ext)s'),
            'format': 'best/mp4/best[ext=mp4]/best',
            'writeinfojson': False,
            'writesubtitles': False,
            'writeautomaticsub': False,
            'ignoreerrors': False,
        }

        self.youtube_opts = {
            'outtmpl': str(self.temp_dir / 'YouTube_%(title)s_%(uploader)s.%(ext)s'),
            'format': 'best[height<=1080]/best',
            'writeinfojson': False,
            'writesubtitles': False,
            'writeautomaticsub': False,
            'ignoreerrors': False,
        }

    # ==================== CLEANUP FUNCTIONS ====================

    def schedule_file_deletion(self, file_path):
        """
        Schedule a file for deletion after the specified time

        Args:
            file_path (str or Path): Path to file to delete
        """

        def delete_file():
            try:
                file_path_obj = Path(file_path)
                if file_path_obj.exists():
                    file_path_obj.unlink()
                    print(f"🗑️ Deleted: {file_path_obj.name}")
                else:
                    print(f"⚠️ File already removed: {file_path_obj.name}")
            except Exception as e:
                print(f"❌ Error deleting file {file_path}: {e}")

        # Schedule deletion
        timer = threading.Timer(self.cleanup_seconds, delete_file)
        timer.daemon = True  # Dies when main thread dies
        timer.start()
        self.cleanup_timers.append(timer)

        print(f"⏰ Scheduled deletion of '{Path(file_path).name}' in {self.cleanup_minutes} minute(s)")

    def cleanup_all_files(self):
        """Manually clean up all downloaded files immediately"""
        try:
            if self.temp_dir.exists():
                for file_path in self.temp_dir.iterdir():
                    if file_path.is_file():
                        file_path.unlink()
                        print(f"🗑️ Deleted: {file_path.name}")
                print("✅ All temporary files cleaned up")
        except Exception as e:
            print(f"❌ Error during cleanup: {e}")

    def cleanup_temp_directory(self):
        """Clean up the entire temporary directory"""
        try:
            # Cancel any pending timers
            for timer in self.cleanup_timers:
                timer.cancel()

            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
                print(f"🗑️ Removed temporary directory: {self.temp_dir}")
        except Exception as e:
            print(f"❌ Error removing temp directory: {e}")

    def list_current_files(self):
        """List currently downloaded files in temp directory"""
        try:
            files = list(self.temp_dir.glob("*"))
            if files:
                print(f"\n📄 Currently downloaded files ({len(files)}):")
                for i, file_path in enumerate(files, 1):
                    if file_path.is_file():
                        size = file_path.stat().st_size / (1024 * 1024)  # MB
                        print(f"{i}. {file_path.name} ({size:.1f}MB)")
            else:
                print("📄 No files currently downloaded")
        except Exception as e:
            print(f"❌ Error listing files: {e}")

    # ==================== URL DETECTION ====================

    def detect_platform(self, url):
        """
        Detect which platform the URL belongs to

        Args:
            url (str): Video URL

        Returns:
            str: 'tiktok', 'youtube', or 'unknown'
        """
        # TikTok patterns
        tiktok_patterns = [
            r'https?://(?:www\.)?tiktok\.com/@[\w.-]+/video/\d+',
            r'https?://(?:vm|vt)\.tiktok\.com/[\w.-]+',
            r'https?://(?:www\.)?tiktok\.com/t/[\w.-]+',
        ]

        # YouTube patterns
        youtube_patterns = [
            r'https?://(?:www\.)?youtube\.com/shorts/[\w-]+',
            r'https?://youtu\.be/[\w-]+',
            r'https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+',
            r'https?://(?:m\.)?youtube\.com/watch\?v=[\w-]+',
        ]

        if any(re.match(pattern, url) for pattern in tiktok_patterns):
            return 'tiktok'
        elif any(re.match(pattern, url) for pattern in youtube_patterns):
            return 'youtube'
        else:
            return 'unknown'

    def is_valid_tiktok_url(self, url):
        """Validate TikTok URL"""
        return self.detect_platform(url) == 'tiktok'

    def is_valid_youtube_url(self, url):
        """Validate YouTube URL"""
        return self.detect_platform(url) == 'youtube'

    # ==================== TIKTOK FUNCTIONS ====================

    def download_tiktok_video(self, url):
        """
        Download a single TikTok video

        Args:
            url (str): TikTok video URL

        Returns:
            bool: True if download successful, False otherwise
        """
        if not self.is_valid_tiktok_url(url):
            print(f"❌ Invalid TikTok URL: {url}")
            return False

        try:
            with yt_dlp.YoutubeDL(self.tiktok_opts) as ydl:
                print(f"🔍 Fetching TikTok video info for: {url}")

                # Get video info first
                info = ydl.extract_info(url, download=False)
                title = info.get('title', 'Unknown')
                duration = info.get('duration', 0)
                uploader = info.get('uploader', 'Unknown')

                print(f"📹 Title: {title}")
                print(f"👤 Creator: {uploader}")
                print(f"⏱️ Duration: {duration}s")

                # Download the video
                print("⬇️ Starting TikTok download...")
                ydl.download([url])

                # Find the downloaded file and schedule deletion
                downloaded_files = list(self.temp_dir.glob("TikTok_*"))
                if downloaded_files:
                    latest_file = max(downloaded_files, key=lambda p: p.stat().st_mtime)
                    self.schedule_file_deletion(latest_file)

                print("✅ TikTok download completed successfully!")
                return True

        except yt_dlp.utils.DownloadError as e:
            if "Requested format is not available" in str(e):
                print("⚠️ Specific format not available, trying with fallback...")
                return self._tiktok_fallback_download(url)
            else:
                print(f"❌ TikTok download error: {str(e)}")
                return False
        except Exception as e:
            print(f"❌ Error downloading TikTok video: {str(e)}")
            return False

    def _tiktok_fallback_download(self, url):
        """Fallback download for TikTok"""
        fallback_opts = {
            'outtmpl': str(self.temp_dir / 'TikTok_%(title)s.%(ext)s'),
            'format': 'best',
            'writeinfojson': False,
        }

        try:
            with yt_dlp.YoutubeDL(fallback_opts) as ydl:
                print("🔄 Attempting TikTok download with fallback settings...")
                ydl.download([url])

                # Schedule deletion for fallback download
                downloaded_files = list(self.temp_dir.glob("TikTok_*"))
                if downloaded_files:
                    latest_file = max(downloaded_files, key=lambda p: p.stat().st_mtime)
                    self.schedule_file_deletion(latest_file)

                print("✅ TikTok fallback download successful!")
                return True
        except Exception as e:
            print(f"❌ TikTok fallback download failed: {str(e)}")
            return False

    def get_tiktok_info(self, url):
        """Get TikTok video information"""
        if not self.is_valid_tiktok_url(url):
            return None

        try:
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    'title': info.get('title', 'Unknown'),
                    'uploader': info.get('uploader', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'view_count': info.get('view_count', 0),
                    'like_count': info.get('like_count', 0),
                    'description': info.get('description', ''),
                    'platform': 'TikTok'
                }
        except Exception as e:
            print(f"Error getting TikTok video info: {e}")
            return None

    # ==================== YOUTUBE FUNCTIONS ====================

    def is_video_a_short(self, info):
        """Check if YouTube video is actually a Short"""
        duration = info.get('duration', 0)

        # YouTube Shorts are typically under 60 seconds
        if duration and duration <= 60:
            return True

        # Check if title or description mentions "Shorts"
        title = info.get('title', '').lower()
        description = info.get('description', '').lower()

        if 'shorts' in title or 'shorts' in description:
            return True

        # Check video dimensions (Shorts are usually vertical)
        width = info.get('width', 0)
        height = info.get('height', 0)

        if height > width:  # Vertical video
            return True

        return False

    def convert_to_shorts_url(self, url):
        """Convert regular YouTube URL to Shorts URL format"""
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/)([\w-]+)',
            r'youtube\.com/shorts/([\w-]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                video_id = match.group(1)
                return f"https://www.youtube.com/shorts/{video_id}"

        return url

    def download_youtube_short(self, url):
        """
        Download a single YouTube Short

        Args:
            url (str): YouTube video URL

        Returns:
            bool: True if download successful, False otherwise
        """
        if not self.is_valid_youtube_url(url):
            print(f"❌ Invalid YouTube URL: {url}")
            return False

        # Convert to Shorts URL format
        shorts_url = self.convert_to_shorts_url(url)
        if shorts_url != url:
            print(f"🔄 Converted to Shorts URL: {shorts_url}")
            url = shorts_url

        try:
            with yt_dlp.YoutubeDL(self.youtube_opts) as ydl:
                print(f"🔍 Fetching YouTube video info for: {url}")

                # Get video info first
                info = ydl.extract_info(url, download=False)

                # Check if it's actually a Short
                if not self.is_video_a_short(info):
                    print("⚠️ Warning: This video might not be a YouTube Short (duration > 60s or landscape)")
                    choice = input("Continue downloading anyway? (y/n): ").lower().strip()
                    if choice != 'y':
                        return False

                title = info.get('title', 'Unknown')
                uploader = info.get('uploader', 'Unknown')
                duration = info.get('duration', 0)
                view_count = info.get('view_count', 0)

                print(f"🎬 Title: {title}")
                print(f"👤 Channel: {uploader}")
                print(f"⏱️ Duration: {duration}s")
                print(f"👀 Views: {view_count:,}")

                # Download the video
                print("⬇️ Starting YouTube download...")
                ydl.download([url])

                # Find the downloaded file and schedule deletion
                downloaded_files = list(self.temp_dir.glob("YouTube_*"))
                if downloaded_files:
                    latest_file = max(downloaded_files, key=lambda p: p.stat().st_mtime)
                    self.schedule_file_deletion(latest_file)

                print("✅ YouTube download completed successfully!")
                return True

        except yt_dlp.utils.DownloadError as e:
            if "Requested format is not available" in str(e):
                print("⚠️ Specific format not available, trying with fallback...")
                return self._youtube_fallback_download(url)
            else:
                print(f"❌ YouTube download error: {str(e)}")
                return False
        except Exception as e:
            print(f"❌ Error downloading YouTube video: {str(e)}")
            return False

    def _youtube_fallback_download(self, url):
        """Fallback download for YouTube"""
        fallback_opts = {
            'outtmpl': str(self.temp_dir / 'YouTube_%(title)s_%(uploader)s.%(ext)s'),
            'format': 'best',
            'writeinfojson': False,
        }

        try:
            with yt_dlp.YoutubeDL(fallback_opts) as ydl:
                print("🔄 Attempting YouTube download with fallback settings...")
                ydl.download([url])

                # Schedule deletion for fallback download
                downloaded_files = list(self.temp_dir.glob("YouTube_*"))
                if downloaded_files:
                    latest_file = max(downloaded_files, key=lambda p: p.stat().st_mtime)
                    self.schedule_file_deletion(latest_file)

                print("✅ YouTube fallback download successful!")
                return True
        except Exception as e:
            print(f"❌ YouTube fallback download failed: {str(e)}")
            return False

    def get_youtube_info(self, url):
        """Get YouTube video information"""
        if not self.is_valid_youtube_url(url):
            return None

        try:
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    'title': info.get('title', 'Unknown'),
                    'uploader': info.get('uploader', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'view_count': info.get('view_count', 0),
                    'like_count': info.get('like_count', 0),
                    'description': info.get('description', ''),
                    'upload_date': info.get('upload_date', ''),
                    'is_short': self.is_video_a_short(info),
                    'width': info.get('width', 0),
                    'height': info.get('height', 0),
                    'platform': 'YouTube'
                }
        except Exception as e:
            print(f"Error getting YouTube video info: {e}")
            return None

    # ==================== UNIFIED FUNCTIONS ====================

    def download_video(self, url):
        """
        Universal video download function - auto-detects platform

        Args:
            url (str): Video URL (TikTok or YouTube)

        Returns:
            bool: True if download successful, False otherwise
        """
        platform = self.detect_platform(url)

        if platform == 'tiktok':
            print("🎵 Detected TikTok video")
            return self.download_tiktok_video(url)
        elif platform == 'youtube':
            print("🎬 Detected YouTube video")
            return self.download_youtube_short(url)
        else:
            print(f"❌ Unsupported platform or invalid URL: {url}")
            print("💡 Supported platforms: TikTok, YouTube")
            return False

    def download_multiple_videos(self, urls):
        """
        Download multiple videos from mixed platforms

        Args:
            urls (list): List of video URLs
        """
        successful = 0
        failed = 0
        tiktok_count = 0
        youtube_count = 0

        for i, url in enumerate(urls, 1):
            print(f"\n{'=' * 60}")
            print(f"Processing video {i}/{len(urls)}")
            print(f"{'=' * 60}")

            platform = self.detect_platform(url)
            if platform == 'tiktok':
                tiktok_count += 1
            elif platform == 'youtube':
                youtube_count += 1

            if self.download_video(url):
                successful += 1
            else:
                failed += 1

        print(f"\n{'=' * 60}")
        print(f"📊 Download Summary:")
        print(f"✅ Successful: {successful}")
        print(f"❌ Failed: {failed}")
        print(f"🎵 TikTok videos: {tiktok_count}")
        print(f"🎬 YouTube videos: {youtube_count}")
        print(f"📁 All files temporarily saved in: {self.temp_dir}")
        print(f"⏰ Files will be deleted automatically in {self.cleanup_minutes} minute(s)")
        print(f"{'=' * 60}")

    def get_video_info(self, url):
        """
        Universal video info function - auto-detects platform

        Args:
            url (str): Video URL

        Returns:
            dict: Video information
        """
        platform = self.detect_platform(url)

        if platform == 'tiktok':
            return self.get_tiktok_info(url)
        elif platform == 'youtube':
            return self.get_youtube_info(url)
        else:
            print(f"❌ Unsupported platform: {url}")
            return None

    def list_formats(self, url):
        """
        List available formats for any supported video

        Args:
            url (str): Video URL
        """
        platform = self.detect_platform(url)

        if platform not in ['tiktok', 'youtube']:
            print(f"❌ Unsupported platform: {url}")
            return

        try:
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                print(f"🔍 Checking available formats for {platform.upper()} video: {url}")
                info = ydl.extract_info(url, download=False)

                formats = info.get('formats', [])
                if not formats:
                    print("❌ No formats found for this video")
                    return

                print(f"\n📋 Available formats ({len(formats)} total) - {platform.upper()}:")
                print("-" * 90)
                print(f"{'ID':<12} {'Extension':<10} {'Quality':<12} {'FPS':<6} {'Size':<12} {'Note'}")
                print("-" * 90)

                for fmt in formats:
                    format_id = fmt.get('format_id', 'N/A')
                    ext = fmt.get('ext', 'N/A')
                    height = fmt.get('height')
                    fps = fmt.get('fps', 'N/A')
                    quality = f"{height}p" if height else 'Audio'
                    filesize = fmt.get('filesize_approx') or fmt.get('filesize')
                    size_str = f"{filesize / 1024 / 1024:.1f}MB" if filesize else 'Unknown'
                    note = fmt.get('format_note', '')

                    print(f"{format_id:<12} {ext:<10} {quality:<12} {fps:<6} {size_str:<12} {note}")

                print("-" * 90)

                # Platform-specific info
                if platform == 'youtube':
                    if self.is_video_a_short(info):
                        print("✅ This appears to be a YouTube Short")
                    else:
                        print("⚠️ This might not be a YouTube Short")

        except Exception as e:
            print(f"❌ Error checking formats: {str(e)}")


def main():
    """
    Main function to run the unified video downloader
    """
    print("🎥 Unified Video Downloader (Temporary Mode) 🎥")
    print("🎵 TikTok + 🎬 YouTube Shorts")
    print("⚠️ All files are downloaded temporarily and auto-deleted!")
    print("=" * 60)

    # Ask user for cleanup time
    cleanup_input = input("Enter auto-delete time in minutes (default 1): ").strip()
    try:
        cleanup_minutes = float(cleanup_input) if cleanup_input else 1.0
        if cleanup_minutes <= 0:
            cleanup_minutes = 1.0
    except ValueError:
        cleanup_minutes = 1.0

    # Initialize downloader
    downloader = UnifiedVideoDownloader(cleanup_minutes)

    try:
        while True:
            print("\n🎯 Main Options:")
            print("1. Download single video (Auto-detect platform)")
            print("2. Download multiple videos (Mixed platforms)")
            print("3. Get video info only")
            print("4. List available formats")
            print("5. TikTok-specific options")
            print("6. YouTube-specific options")
            print("7. List current downloaded files")
            print("8. Clean up all files now")
            print("9. Exit")

            choice = input("\nEnter your choice (1-9): ").strip()

            if choice == '1':
                url = input("Enter video URL (TikTok or YouTube): ").strip()
                if url:
                    downloader.download_video(url)
                else:
                    print("❌ Please enter a valid URL")

            elif choice == '2':
                print("Enter video URLs (TikTok/YouTube mixed, one per line, empty line to finish):")
                urls = []
                while True:
                    url = input().strip()
                    if not url:
                        break
                    urls.append(url)

                if urls:
                    downloader.download_multiple_videos(urls)
                else:
                    print("❌ No URLs provided")

            elif choice == '3':
                url = input("Enter video URL: ").strip()
                if url:
                    info = downloader.get_video_info(url)
                    if info:
                        print(f"\n📱 Video Information ({info['platform']}):")
                        print(f"Title: {info['title']}")
                        print(f"Creator/Channel: {info['uploader']}")
                        print(f"Duration: {info['duration']}s")
                        print(f"Views: {info['view_count']:,}")
                        print(f"Likes: {info['like_count']:,}")
                        if 'is_short' in info:
                            print(f"Is YouTube Short: {'Yes' if info['is_short'] else 'Probably No'}")
                            print(f"Dimensions: {info['width']}x{info['height']}")
                        print(f"Description: {info['description'][:200]}...")
                else:
                    print("❌ Please enter a valid URL")

            elif choice == '4':
                url = input("Enter video URL to check formats: ").strip()
                if url:
                    downloader.list_formats(url)
                else:
                    print("❌ Please enter a valid URL")

            elif choice == '5':
                print("\n🎵 TikTok-Specific Options:")
                print("1. Download TikTok video")
                print("2. Get TikTok video info")
                print("3. Back to main menu")

                tiktok_choice = input("Enter choice: ").strip()
                if tiktok_choice == '1':
                    url = input("Enter TikTok URL: ").strip()
                    if url:
                        downloader.download_tiktok_video(url)
                elif tiktok_choice == '2':
                    url = input("Enter TikTok URL: ").strip()
                    if url:
                        info = downloader.get_tiktok_info(url)
                        if info:
                            print(f"\n🎵 TikTok Video Info:")
                            for key, value in info.items():
                                if key != 'description':
                                    print(f"{key.title()}: {value}")

            elif choice == '6':
                print("\n🎬 YouTube-Specific Options:")
                print("1. Download YouTube Short")
                print("2. Get YouTube video info")
                print("3. Back to main menu")

                youtube_choice = input("Enter choice: ").strip()
                if youtube_choice == '1':
                    url = input("Enter YouTube URL: ").strip()
                    if url:
                        downloader.download_youtube_short(url)
                elif youtube_choice == '2':
                    url = input("Enter YouTube URL: ").strip()
                    if url:
                        info = downloader.get_youtube_info(url)
                        if info:
                            print(f"\n🎬 YouTube Video Info:")
                            for key, value in info.items():
                                if key != 'description':
                                    print(f"{key.title()}: {value}")

            elif choice == '7':
                downloader.list_current_files()

            elif choice == '8':
                downloader.cleanup_all_files()

            elif choice == '9':
                print("🧹 Cleaning up temporary files before exit...")
                downloader.cleanup_temp_directory()
                print("👋 Goodbye!")
                break

            else:
                print("❌ Invalid choice. Please enter 1-9")

    except KeyboardInterrupt:
        print("\n\n🧹 Cleaning up temporary files...")
        downloader.cleanup_temp_directory()
        print("👋 Download interrupted by user. Goodbye!")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        print("🧹 Cleaning up temporary files...")
        downloader.cleanup_temp_directory()


if __name__ == "__main__":
    main()