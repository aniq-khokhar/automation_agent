import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
import json
import re
from typing import List, Dict, Optional
from dataclasses import dataclass
import base64
from io import BytesIO
from PIL import Image
import logging
import os
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class HashtagData:
    """Data class to store hashtag information"""
    hashtag: str
    platform: str
    trend_score: Optional[int] = None
    category: Optional[str] = None


@dataclass
class ContentData:
    """Data class to store content information"""
    platform: str
    hashtag: str
    title: str
    thumbnail_url: str
    video_url: Optional[str] = None
    view_count: Optional[str] = None
    creator: Optional[str] = None
    description: Optional[str] = None
    thumbnail_base64: Optional[str] = None


class TrendingHashtagScraper:
    """Main class for scraping trending hashtags from various platforms"""

    def __init__(self):
        self.setup_selenium()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def setup_selenium(self):
        """Setup Selenium WebDriver with Chrome options"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument(
            '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')

        try:
            self.driver = webdriver.Chrome(options=chrome_options)
        except Exception as e:
            logger.error(f"Failed to initialize Chrome driver: {e}")
            self.driver = None

    def get_google_trends_hashtags(self, geo_location: str = 'US') -> List[HashtagData]:
        """Scrape trending topics from Google Trends"""
        hashtags = []
        try:
            url = f"https://trends.google.com/trends/trendingsearches/daily?geo={geo_location}"

            if self.driver:
                self.driver.get(url)
                time.sleep(3)

                # Wait for trends to load
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "summary-text"))
                )

                trend_elements = self.driver.find_elements(By.CLASS_NAME, "summary-text")

                for i, element in enumerate(trend_elements[:20]):  # Get top 20
                    trend_text = element.text.strip()
                    if trend_text:
                        # Convert to hashtag format
                        hashtag = '#' + re.sub(r'[^\w\s]', '', trend_text).replace(' ', '').lower()
                        hashtags.append(HashtagData(
                            hashtag=hashtag,
                            platform='google_trends',
                            trend_score=20 - i,
                            category='trending'
                        ))

        except Exception as e:
            logger.error(f"Error scraping Google Trends: {e}")

        return hashtags

    def get_tiktok_hashtags(self) -> List[HashtagData]:
        """Scrape trending hashtags from TikTok's trending page"""
        hashtags = []
        try:
            if not self.driver:
                return hashtags

            self.driver.get("https://www.tiktok.com/discover")
            time.sleep(5)

            # Look for trending hashtags in various selectors
            hashtag_selectors = [
                '[data-e2e="discover-hashtag"]',
                '.css-1g95xhm-StyledLink',
                '[href*="/tag/"]',
                '.discover-hashtag'
            ]

            for selector in hashtag_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for i, element in enumerate(elements[:15]):
                        text = element.text.strip()
                        if text and text.startswith('#'):
                            hashtags.append(HashtagData(
                                hashtag=text,
                                platform='tiktok',
                                trend_score=15 - i,
                                category='discover'
                            ))
                    if hashtags:
                        break
                except Exception as e:
                    continue

            # Alternative method: look for hashtag patterns in page source
            if not hashtags:
                page_source = self.driver.page_source
                hashtag_pattern = r'#[a-zA-Z0-9_]+(?:[a-zA-Z0-9_]*[a-zA-Z0-9])?'
                found_hashtags = re.findall(hashtag_pattern, page_source)

                for i, hashtag in enumerate(list(set(found_hashtags))[:10]):
                    if len(hashtag) > 2:  # Filter out very short hashtags
                        hashtags.append(HashtagData(
                            hashtag=hashtag,
                            platform='tiktok',
                            trend_score=10 - i,
                            category='extracted'
                        ))

        except Exception as e:
            logger.error(f"Error scraping TikTok hashtags: {e}")

        return hashtags

    def get_youtube_hashtags(self) -> List[HashtagData]:
        """Scrape trending hashtags from YouTube trending videos"""
        hashtags = []
        try:
            if not self.driver:
                return hashtags

            self.driver.get("https://www.youtube.com/feed/trending")
            time.sleep(5)

            # Get video titles and descriptions to extract hashtags
            video_elements = self.driver.find_elements(By.CSS_SELECTOR, '#video-title')

            hashtag_counts = {}
            for element in video_elements[:20]:
                try:
                    # Click on video to get to its page
                    video_link = element.get_attribute('href')
                    if video_link:
                        self.driver.execute_script("window.open('');")
                        self.driver.switch_to.window(self.driver.window_handles[1])
                        self.driver.get(video_link)
                        time.sleep(3)

                        # Look for hashtags in description
                        try:
                            description_element = self.driver.find_element(
                                By.CSS_SELECTOR,
                                '[data-e2e="video-description"] span, #description-text, .description'
                            )
                            description = description_element.text

                            # Extract hashtags
                            found_hashtags = re.findall(r'#[a-zA-Z0-9_]+', description)
                            for hashtag in found_hashtags:
                                hashtag_counts[hashtag] = hashtag_counts.get(hashtag, 0) + 1
                        except:
                            pass

                        self.driver.close()
                        self.driver.switch_to.window(self.driver.window_handles[0])
                except Exception as e:
                    continue

            # Convert to HashtagData objects
            sorted_hashtags = sorted(hashtag_counts.items(), key=lambda x: x[1], reverse=True)
            for i, (hashtag, count) in enumerate(sorted_hashtags[:10]):
                hashtags.append(HashtagData(
                    hashtag=hashtag,
                    platform='youtube',
                    trend_score=count,
                    category='trending_videos'
                ))

        except Exception as e:
            logger.error(f"Error scraping YouTube hashtags: {e}")

        return hashtags

    def get_all_trending_hashtags(self) -> List[HashtagData]:
        """Get trending hashtags from all platforms"""
        all_hashtags = []

        logger.info("Fetching Google Trends hashtags...")
        all_hashtags.extend(self.get_google_trends_hashtags())

        logger.info("Fetching TikTok hashtags...")
        all_hashtags.extend(self.get_tiktok_hashtags())

        logger.info("Fetching YouTube hashtags...")
        all_hashtags.extend(self.get_youtube_hashtags())

        # Remove duplicates and sort by trend score
        unique_hashtags = {}
        for hashtag in all_hashtags:
            key = hashtag.hashtag.lower()
            if key not in unique_hashtags or (hashtag.trend_score or 0) > (unique_hashtags[key].trend_score or 0):
                unique_hashtags[key] = hashtag

        return sorted(unique_hashtags.values(), key=lambda x: x.trend_score or 0, reverse=True)


class ContentAnalyzer:
    """Class for analyzing content from trending hashtags"""

    def __init__(self):
        self.setup_selenium()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def setup_selenium(self):
        """Setup Selenium WebDriver"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')

        try:
            self.driver = webdriver.Chrome(options=chrome_options)
        except Exception as e:
            logger.error(f"Failed to initialize Chrome driver: {e}")
            self.driver = None

    def download_and_encode_image(self, url: str) -> Optional[str]:
        """Download image and encode to base64"""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            # Convert to base64
            image_base64 = base64.b64encode(response.content).decode('utf-8')
            return image_base64
        except Exception as e:
            logger.error(f"Error downloading image {url}: {e}")
            return None

    def download_video(self, url: str, output_dir: str = 'output') -> Optional[str]:
        """Download video from a given URL."""
        if not url:
            return None
        try:
            video_id = os.path.basename(urlparse(url).path)
            output_path = os.path.join(output_dir, f"{video_id}.mp4")
            if os.path.exists(output_path):
                logger.info(f"Video already downloaded: {output_path}")
                return output_path

            response = self.session.get(url, stream=True, timeout=30)
            response.raise_for_status()
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            logger.info(f"Video downloaded successfully: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Error downloading video {url}: {e}")
            return None

    def search_tiktok_hashtag(self, hashtag: str, limit: int = 10) -> List[ContentData]:
        """Search TikTok for specific hashtag content"""
        content_list = []
        try:
            if not self.driver:
                return content_list

            # Remove # from hashtag for URL
            clean_hashtag = hashtag.replace('#', '')
            url = f"https://www.tiktok.com/tag/{clean_hashtag}"

            self.driver.get(url)
            time.sleep(5)

            # Scroll to load more content
            for _ in range(3):
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)

            # Find video elements
            video_selectors = [
                '[data-e2e="user-post-item"]',
                '.css-1as491j-DivItemContainer',
                '[data-e2e="recommend-list-item"]'
            ]

            for selector in video_selectors:
                try:
                    video_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)[:limit]

                    for element in video_elements:
                        try:
                            # Extract video information
                            img_element = element.find_element(By.TAG_NAME, 'img')
                            thumbnail_url = img_element.get_attribute('src')

                            # Try to get video link
                            link_element = element.find_element(By.TAG_NAME, 'a')
                            video_url = link_element.get_attribute('href')

                            # Get thumbnail as base64
                            thumbnail_base64 = self.download_and_encode_image(thumbnail_url) if thumbnail_url else None

                            content_list.append(ContentData(
                                platform='tiktok',
                                hashtag=hashtag,
                                title=f"TikTok video with {hashtag}",
                                thumbnail_url=thumbnail_url or '',
                                video_url=video_url,
                                thumbnail_base64=thumbnail_base64
                            ))
                        except Exception as e:
                            continue

                    if content_list:
                        break
                except Exception as e:
                    continue

        except Exception as e:
            logger.error(f"Error searching TikTok for {hashtag}: {e}")

        return content_list

    def search_youtube_hashtag(self, hashtag: str, limit: int = 10) -> List[ContentData]:
        """Search YouTube for specific hashtag content"""
        content_list = []
        try:
            if not self.driver:
                return content_list

            # Search YouTube
            query = hashtag.replace('#', '%23')  # URL encode hashtag
            url = f"https://www.youtube.com/results?search_query={query}"

            self.driver.get(url)
            time.sleep(5)

            # Get video results
            video_elements = self.driver.find_elements(
                By.CSS_SELECTOR,
                '#contents ytd-video-renderer, #contents ytd-rich-item-renderer'
            )[:limit]

            for element in video_elements:
                try:
                    # Get thumbnail
                    thumbnail_element = element.find_element(By.CSS_SELECTOR, 'img')
                    thumbnail_url = thumbnail_element.get_attribute('src')

                    # Get title
                    title_element = element.find_element(By.CSS_SELECTOR, 'a#video-title')
                    title = title_element.get_attribute('title') or title_element.text
                    video_url = title_element.get_attribute('href')

                    # Get creator
                    try:
                        creator_element = element.find_element(
                            By.CSS_SELECTOR,
                            '#text a, .ytd-channel-name a'
                        )
                        creator = creator_element.text
                    except:
                        creator = None

                    # Get view count
                    try:
                        views_element = element.find_element(
                            By.CSS_SELECTOR,
                            '#metadata-line span:first-child, .style-scope ytd-video-meta-block span'
                        )
                        view_count = views_element.text
                    except:
                        view_count = None

                    # Download thumbnail
                    thumbnail_base64 = self.download_and_encode_image(thumbnail_url) if thumbnail_url else None

                    content_list.append(ContentData(
                        platform='youtube',
                        hashtag=hashtag,
                        title=title or 'Untitled',
                        thumbnail_url=thumbnail_url or '',
                        video_url=f"https://youtube.com{video_url}" if video_url and not video_url.startswith(
                            'http') else video_url,
                        view_count=view_count,
                        creator=creator,
                        thumbnail_base64=thumbnail_base64
                    ))

                except Exception as e:
                    continue

        except Exception as e:
            logger.error(f"Error searching YouTube for {hashtag}: {e}")

        return content_list

    def analyze_hashtag_content(self, hashtags: List[str], platform: str = 'both', limit_per_hashtag: int = 5) -> Dict[
        str, List[ContentData]]:
        """Analyze content for given hashtags"""
        results = {}

        for hashtag in hashtags:
            logger.info(f"Analyzing content for hashtag: {hashtag}")
            results[hashtag] = []

            if platform in ['both', 'tiktok']:
                tiktok_content = self.search_tiktok_hashtag(hashtag, limit_per_hashtag)
                results[hashtag].extend(tiktok_content)

            if platform in ['both', 'youtube']:
                youtube_content = self.search_youtube_hashtag(hashtag, limit_per_hashtag)
                results[hashtag].extend(youtube_content)

            time.sleep(2)  # Rate limiting

        return results

    def close(self):
        """Close the webdriver"""
        if hasattr(self, 'driver') and self.driver:
            self.driver.quit()


# Usage Example Functions
def get_trending_hashtags(geo_location: str = 'US') -> List[Dict]:
    """Main function to get trending hashtags"""
    scraper = TrendingHashtagScraper()

    try:
        hashtags = scraper.get_all_trending_hashtags()

        # Convert to dictionary for JSON serialization
        result = []
        for hashtag in hashtags:
            result.append({
                'hashtag': hashtag.hashtag,
                'platform': hashtag.platform,
                'trend_score': hashtag.trend_score,
                'category': hashtag.category
            })

        return result

    finally:
        if hasattr(scraper, 'driver') and scraper.driver:
            scraper.driver.quit()


def analyze_trending_content(hashtags: List[str], platform: str = 'both', limit: int = 5) -> Dict:
    """Main function to analyze content for trending hashtags"""
    analyzer = ContentAnalyzer()

    try:
        results = analyzer.analyze_hashtag_content(hashtags, platform, limit)

        # Convert to serializable format
        serializable_results = {}
        for hashtag, content_list in results.items():
            serializable_results[hashtag] = []
            for content in content_list:
                serializable_results[hashtag].append({
                    'platform': content.platform,
                    'hashtag': content.hashtag,
                    'title': content.title,
                    'thumbnail_url': content.thumbnail_url,
                    'video_url': content.video_url,
                    'view_count': content.view_count,
                    'creator': content.creator,
                    'description': content.description,
                    'thumbnail_base64': content.thumbnail_base64
                })

        return serializable_results

    finally:
        analyzer.close()


# Example usage
if __name__ == "__main__":
    # Step 1: Get trending hashtags
    print("Getting trending hashtags...")
    trending = get_trending_hashtags('US')

    print(f"Found {len(trending)} trending hashtags:")
    for item in trending[:10]:  # Show top 10
        print(f"- {item['hashtag']} ({item['platform']}) - Score: {item['trend_score']}")

    # Step 2: Analyze content for top hashtags
    top_hashtags = [item['hashtag'] for item in trending[:3]]  # Top 3 hashtags

    print(f"\nAnalyzing content for hashtags: {top_hashtags}")
    content_analysis = analyze_trending_content(top_hashtags, platform='both', limit=3)

    # Display results
    for hashtag, contents in content_analysis.items():
        print(f"\n--- Content for {hashtag} ---")
        for content in contents:
            print(f"Platform: {content['platform']}")
            print(f"Title: {content['title']}")
            print(f"Creator: {content.get('creator', 'Unknown')}")
            print(f"Views: {content.get('view_count', 'N/A')}")
            print(f"Has Thumbnail: {'Yes' if content['thumbnail_base64'] else 'No'}")
            print(f"Video URL: {content.get('video_url', 'N/A')}")
            print("-" * 50)
