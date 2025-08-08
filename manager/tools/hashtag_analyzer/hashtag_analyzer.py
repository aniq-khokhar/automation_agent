import os
import time
import logging
from dotenv import load_dotenv
from scrapper import ContentAnalyzer
from video_analyzer import analyze_video_with_gemini

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv()

def process_hashtags(hashtags, platforms=['youtube', 'tiktok']):
    """
    Processes a list of hashtags to find related videos, downloads them,
    and generates a visual summary using the Gemini API.

    Args:
        hashtags (list): A list of hashtags to process (e.g., ['#nature', '#tech']).
        platforms (list, optional): The platforms to search on. Defaults to ['youtube', 'tiktok'].

    Returns:
        dict: A dictionary where keys are hashtags and values are lists of video summaries.
    """
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY environment variable not set.")

    content_analyzer = ContentAnalyzer()
    results = {}

    for hashtag in hashtags:
        logging.info(f"Processing hashtag: {hashtag}")
        results[hashtag] = []
        try:
            video_contents = content_analyzer.analyze_hashtag_content([hashtag], platform='both', limit_per_hashtag=1)

            summaries = []
            for content_item in video_contents.get(hashtag, []):
                video_url = content_item.video_url
                if video_url:
                    logging.info(f"Downloading video: {video_url}")
                    video_path = content_analyzer.download_video(video_url)
                    if video_path:
                        logging.info(f"Analyzing video with Gemini: {video_path}")
                        try:
                            summary = analyze_video_with_gemini(video_path, GEMINI_API_KEY)
                            summaries.append(summary)
                            logging.info("Analysis complete. Waiting 60 seconds before next request.")
                            time.sleep(60)
                        except Exception as e:
                            logging.error(f"API limit reached or error analyzing video: {e}")
                            break  # Stop processing this hashtag if API fails
            results[hashtag] = summaries

        except Exception as e:
            logging.error(f"An unexpected error occurred while processing {hashtag}: {e}")

    content_analyzer.close()
    return results
