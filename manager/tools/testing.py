# import os
# import io
# import re
# import tempfile
# import time
# import requests
# import yt_dlp
# import google.generativeai as genai
# from dotenv import load_dotenv
#
# load_dotenv()
# GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
#
#
# def summ_down(video_urls: list[str]) -> dict:
#     """
#     Download videos to RAM and generate AI summaries using Gemini 2.5 Pro
#
#     Args:
#         video_urls (List[str]): List of video URLs to process
#
#     Returns:
#         Dict: {"videos": [{"url": "", "file": "", "summary": ""}, ...]}
#     """
#
#     if not GEMINI_API_KEY:
#         raise ValueError("Please set your Gemini API key")
#
#     genai.configure(api_key=GEMINI_API_KEY)
#     model = genai.GenerativeModel('gemini-2.5-pro')
#
#     def detect_platform(url: str) -> str:
#         tiktok_patterns = [r'tiktok\.com', r'vm\.tiktok\.com', r'vt\.tiktok\.com']
#         youtube_patterns = [r'youtube\.com', r'youtu\.be']
#
#         if any(re.search(pattern, url) for pattern in tiktok_patterns):
#             return 'tiktok'
#         elif any(re.search(pattern, url) for pattern in youtube_patterns):
#             return 'youtube'
#         return 'unknown'
#
#     def download_to_memory(url: str) -> tuple[bytes, str]:
#         """Download video to memory using yt-dlp's URL extraction + requests"""
#         try:
#             # Get direct video URL using yt-dlp
#             ydl_opts = {
#                 'format': 'best[ext=mp4]/best',
#                 'quiet': True,
#                 'no_warnings': True,
#             }
#
#             with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#                 info = ydl.extract_info(url, download=False)
#                 video_url = info['url']
#                 title = info.get('title', 'video')
#
#             # Download video content to memory
#             response = requests.get(video_url, stream=True)
#             response.raise_for_status()
#
#             video_data = io.BytesIO()
#             for chunk in response.iter_content(chunk_size=8192):
#                 video_data.write(chunk)
#
#             return video_data.getvalue(), f"{title}.mp4"
#
#         except Exception as e:
#             return None, str(e)
#
#     def upload_bytes_to_gemini(video_bytes: bytes, filename: str) -> object:
#         """Upload video bytes to Gemini using temporary file approach"""
#         try:
#             # Create temporary file in memory-based tmpfs if available, otherwise regular temp
#             with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_file:
#                 tmp_file.write(video_bytes)
#                 tmp_path = tmp_file.name
#
#             # Upload to Gemini
#             video_file = genai.upload_file(path=tmp_path)
#
#             # Clean up temp file immediately
#             os.unlink(tmp_path)
#
#             # Wait for processing
#             while video_file.state.name == "PROCESSING":
#                 time.sleep(2)
#                 video_file = genai.get_file(video_file.name)
#
#             if video_file.state.name == "FAILED":
#                 raise ValueError("Video processing failed")
#
#             return video_file
#
#         except Exception as e:
#             # Clean up temp file if it exists
#             if 'tmp_path' in locals() and os.path.exists(tmp_path):
#                 os.unlink(tmp_path)
#             raise e
#
#     def generate_summary(video_file: object) -> str:
#         """Generate video summary using Gemini"""
#         try:
#             prompt = """Analyze this video and provide a comprehensive summary including:
# 1. Main content/topic
# 2. Key actions or events
# 3. Notable objects, people, or scenes
# 4. Overall mood or theme
# Keep it concise (2-3 paragraphs maximum)."""
#
#             response = model.generate_content([video_file, prompt])
#             return response.text.strip()
#
#         except Exception as e:
#             return f"Error generating summary: {str(e)}"
#         finally:
#             # Clean up uploaded file
#             try:
#                 genai.delete_file(video_file.name)
#             except:
#                 pass
#
#     # Process all videos
#     videos = []
#
#     for url in video_urls:
#         try:
#             # Download to memory
#             video_bytes, filename = download_to_memory(url)
#
#             if video_bytes is None:
#                 videos.append({
#                     'url': url,
#                     'file': 'N/A',
#                     'summary': f'Download failed: {filename}'
#                 })
#                 continue
#
#             # Upload to Gemini and summarize
#             video_file = upload_bytes_to_gemini(video_bytes, filename)
#             summary = generate_summary(video_file)
#
#             videos.append({
#                 'url': url,
#                 'file': filename,
#                 'summary': summary
#             })
#
#         except Exception as e:
#             videos.append({
#                 'url': url,
#                 'file': 'N/A',
#                 'summary': f'Processing failed: {str(e)}'
#             })
#
#     return {"videos": videos}
#
# # Example usage:
# results = summ_down([
#     "https://www.youtube.com/shorts/rqLEUxeOQWo",
#     "https://www.youtube.com/shorts/QsQYW-oN1Ik"
# ])


import os
import io
import re
import tempfile
import time
import requests
import yt_dlp
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


def summ_down(video_urls: list[str]) -> dict:
    """
    Download videos to RAM and generate AI summaries using Gemini 2.5 Pro

    Args:
        video_urls (List[str]): List of video URLs to process

    Returns:
        Dict: {"videos": [{"url": "", "file": "", "summary": ""}, ...]}
    """

    if not GEMINI_API_KEY:
        raise ValueError("Please set your Gemini API key")

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.5-pro')

    def detect_platform(url: str) -> str:
        tiktok_patterns = [r'tiktok\.com', r'vm\.tiktok\.com', r'vt\.tiktok\.com']
        youtube_patterns = [r'youtube\.com', r'youtu\.be']

        if any(re.search(pattern, url) for pattern in tiktok_patterns):
            return 'tiktok'
        elif any(re.search(pattern, url) for pattern in youtube_patterns):
            return 'youtube'
        return 'unknown'

    def download_to_memory(url: str) -> tuple[bytes, str]:
        """Download video to memory using yt-dlp's URL extraction + requests"""
        try:
            print(f"🔍 Extracting video info from: {url}")

            # Get direct video URL using yt-dlp
            ydl_opts = {
                'format': 'best[ext=mp4]/best',
                'quiet': True,
                'no_warnings': True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                video_url = info['url']
                title = info.get('title', 'video')
                print(f"✅ Found video: {title}")

            # Download video content to memory
            print(f"⬇️ Downloading video to memory...")
            response = requests.get(video_url, stream=True)
            response.raise_for_status()

            video_data = io.BytesIO()
            total_size = 0
            for chunk in response.iter_content(chunk_size=8192):
                video_data.write(chunk)
                total_size += len(chunk)

            print(f"✅ Downloaded {total_size / 1024 / 1024:.2f} MB to RAM")
            return video_data.getvalue(), f"{title}.mp4"

        except Exception as e:
            print(f"❌ Download failed: {str(e)}")
            return None, str(e)

    def upload_bytes_to_gemini(video_bytes: bytes, filename: str) -> object:
        """Upload video bytes to Gemini using temporary file approach"""
        try:
            print(f"📤 Creating temporary file for Gemini upload...")
            # Create temporary file in memory-based tmpfs if available, otherwise regular temp
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_file:
                tmp_file.write(video_bytes)
                tmp_path = tmp_file.name
            print(f"📂 Temp file created: {tmp_path}")

            # Upload to Gemini
            print(f"☁️ Uploading to Gemini...")
            video_file = genai.upload_file(path=tmp_path)
            print(f"✅ Upload successful, file ID: {video_file.name}")

            # Clean up temp file immediately
            os.unlink(tmp_path)
            print(f"🗑️ Temp file deleted")

            # Wait for processing
            print(f"⏳ Waiting for Gemini processing...")
            processing_time = 0
            while video_file.state.name == "PROCESSING":
                time.sleep(2)
                processing_time += 2
                video_file = genai.get_file(video_file.name)
                print(f"   Processing... ({processing_time}s elapsed)")

            if video_file.state.name == "FAILED":
                raise ValueError("Video processing failed")

            print(f"✅ Gemini processing complete!")
            return video_file

        except Exception as e:
            print(f"❌ Gemini upload failed: {str(e)}")
            # Clean up temp file if it exists
            if 'tmp_path' in locals() and os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise e

    def generate_summary(video_file: object) -> str:
        """Generate video summary using Gemini"""
        try:
            print(f"🤖 Generating AI summary...")
            prompt = """Analyze this video and provide a comprehensive summary including:
1. Main content/topic
2. Key actions or events  
3. Notable objects, people, or scenes
4. Overall mood or theme
Keep it concise (2-3 paragraphs maximum)."""

            response = model.generate_content([video_file, prompt])
            print(f"✅ Summary generated successfully!")
            return response.text.strip()

        except Exception as e:
            print(f"❌ Summary generation failed: {str(e)}")
            return f"Error generating summary: {str(e)}"
        finally:
            # Clean up uploaded file
            try:
                print(f"🗑️ Cleaning up Gemini file...")
                genai.delete_file(video_file.name)
                print(f"✅ Gemini file deleted")
            except:
                print(f"⚠️ Failed to delete Gemini file")
                pass

    # Process all videos
    videos = []

    print(f"🚀 Starting processing of {len(video_urls)} videos...")

    for i, url in enumerate(video_urls, 1):
        try:
            print(f"\n📹 Processing video {i}/{len(video_urls)}")
            print(f"🌐 Platform: {detect_platform(url)}")

            # Download to memory
            video_bytes, filename = download_to_memory(url)

            if video_bytes is None:
                print(f"❌ Skipping due to download failure")
                videos.append({
                    'url': url,
                    'file': 'N/A',
                    'summary': f'Download failed: {filename}'
                })
                continue

            # Upload to Gemini and summarize
            video_file = upload_bytes_to_gemini(video_bytes, filename)
            summary = generate_summary(video_file)

            print(f"✅ Video {i} completed successfully!")
            videos.append({
                'url': url,
                'file': filename,
                'summary': summary
            })

        except Exception as e:
            print(f"❌ Video {i} failed with error: {str(e)}")
            videos.append({
                'url': url,
                'file': 'N/A',
                'summary': f'Processing failed: {str(e)}'
            })

    print(
        f"\n🎉 All videos processed! Results: {len([v for v in videos if 'failed' not in v['summary'].lower()])} successful, {len([v for v in videos if 'failed' in v['summary'].lower()])} failed")
    return {"videos": videos}

# Example usage:
results = summ_down([
    "https://www.youtube.com/shorts/rqLEUxeOQWo",
    "https://www.youtube.com/shorts/QsQYW-oN1Ik"
])
