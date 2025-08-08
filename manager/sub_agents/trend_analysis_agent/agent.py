from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool

trend_analysis_agent = Agent(
    name="trend_analysis_agent",
    model="gemini-2.0-flash",
    description=(
        "Trend agent which analyze what's trending online"
    ),
    instruction=(
        """
    You are the Manager Agent, responsible for overseeing and coordinating the work of other agents in the system.
    You do not execute tasks yourself—instead, you analyze the incoming prompt and always delegate the task to the most appropriate agent.

    Your Responsibilities:
    Analyze the Prompt
    Carefully read and analyze the incoming prompt or user request to understand the task.

    Delegate to the Appropriate Agent
    Based on your analysis, use your best judgment to determine which agent is best suited for the task, and delegate it accordingly.

    If the task involves creating a video, delegate it to the 8s_video_generation_agent.

    Agents Available to You:
    You have access to the following agents:

    - 8s_video_generation_agent
    - assembler_agent
    - posting_agent
    - single_prompter_agent
    - story_prompter_agent
    - trend_analysis_agent
    - video_generation_agent

    Use your best judgment to select the most appropriate agent based on the nature of the task. Always delegate.
        """
    ),
    sub_agents=([]),
    # tools=[get_weather, get_current_time]
)

"""
Building a Browser Agent with Google ADK (Real Implementation)
This shows how to create browser automation capabilities within Google's ADK framework
"""

import asyncio
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, asdict
import re
from collections import Counter

# Google ADK Core Components
from adk.agents import BaseAgent, Agent
from adk.config import AgentConfig
from adk.tools import Tool
from adk.memory import MemoryManager
from adk.llm import LLMClient
from adk.schemas import Message, Response

# Browser automation (we need to integrate this ourselves)
from playwright.async_api import async_playwright, Browser, Page
import requests
from bs4 import BeautifulSoup


@dataclass
class BrowserAction:
    """Structure for browser actions"""
    action_type: str  # navigate, click, type, scroll, extract
    target: str  # URL, selector, or element
    value: Optional[str] = None
    wait_time: float = 1.0
    screenshot: bool = False


@dataclass
class BrowserResult:
    """Structure for browser action results"""
    success: bool
    data: Any = None
    screenshot_path: Optional[str] = None
    error: Optional[str] = None
    page_url: str = ""


class BrowserTool(Tool):
    """Custom Browser Tool for Google ADK"""

    def __init__(self):
        super().__init__(name="browser", description="Web browser automation tool")
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None

    async def initialize(self):
        """Initialize the browser"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled'
            ]
        )

        # Create context with realistic settings
        context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            extra_http_headers={
                'Accept-Language': 'en-US,en;q=0.9',
            }
        )

        self.page = await context.new_page()

        # Add stealth techniques
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
        """)

    async def execute(self, action: BrowserAction) -> BrowserResult:
        """Execute a browser action"""
        if not self.page:
            await self.initialize()

        try:
            if action.action_type == "navigate":
                await self.page.goto(action.target, wait_until='networkidle', timeout=30000)
                await asyncio.sleep(action.wait_time)

                return BrowserResult(
                    success=True,
                    page_url=self.page.url,
                    data={"url": self.page.url, "title": await self.page.title()}
                )

            elif action.action_type == "click":
                await self.page.click(action.target)
                await asyncio.sleep(action.wait_time)
                return BrowserResult(success=True, data={"clicked": action.target})

            elif action.action_type == "type":
                await self.page.type(action.target, action.value or "")
                await asyncio.sleep(action.wait_time)
                return BrowserResult(success=True, data={"typed": action.value})

            elif action.action_type == "scroll":
                if action.target == "bottom":
                    await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                elif action.target == "top":
                    await self.page.evaluate("window.scrollTo(0, 0)")
                else:
                    await self.page.evaluate(f"window.scrollBy(0, {action.value or 500})")

                await asyncio.sleep(action.wait_time)
                return BrowserResult(success=True, data={"scrolled": action.target})

            elif action.action_type == "extract":
                # Extract data based on selectors
                extracted_data = await self.page.evaluate(f"""
                    () => {{
                        const elements = document.querySelectorAll('{action.target}');
                        return Array.from(elements).map(el => ({{
                            text: el.textContent?.trim(),
                            html: el.innerHTML,
                            href: el.href,
                            src: el.src,
                            attributes: Object.fromEntries(
                                Array.from(el.attributes).map(attr => [attr.name, attr.value])
                            )
                        }}));
                    }}
                """)

                return BrowserResult(
                    success=True,
                    data=extracted_data,
                    page_url=self.page.url
                )

            elif action.action_type == "wait_for_selector":
                await self.page.wait_for_selector(action.target, timeout=10000)
                return BrowserResult(success=True, data={"selector_found": action.target})

            elif action.action_type == "screenshot":
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_path = f"screenshot_{timestamp}.png"
                await self.page.screenshot(path=screenshot_path)
                return BrowserResult(
                    success=True,
                    screenshot_path=screenshot_path,
                    data={"screenshot": screenshot_path}
                )

            else:
                return BrowserResult(
                    success=False,
                    error=f"Unknown action type: {action.action_type}"
                )

        except Exception as e:
            return BrowserResult(
                success=False,
                error=str(e),
                page_url=self.page.url if self.page else ""
            )

    async def cleanup(self):
        """Close browser and cleanup"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()


class WebScrapingTool(Tool):
    """Enhanced web scraping tool for ADK"""

    def __init__(self):
        super().__init__(name="web_scraper", description="Advanced web scraping capabilities")
        self.browser_tool = BrowserTool()

    async def scrape_social_media(self, platform: str, hashtag: str, limit: int = 20) -> Dict:
        """Scrape social media content"""
        await self.browser_tool.initialize()

        if platform.lower() == "instagram":
            return await self._scrape_instagram(hashtag, limit)
        elif platform.lower() == "twitter":
            return await self._scrape_twitter(hashtag, limit)
        else:
            return {"error": f"Platform {platform} not supported"}

    async def _scrape_instagram(self, hashtag: str, limit: int) -> Dict:
        """Scrape Instagram hashtag page"""
        url = f"https://www.instagram.com/explore/tags/{hashtag.replace('#', '')}/"

        # Navigate to Instagram
        nav_result = await self.browser_tool.execute(
            BrowserAction("navigate", url, wait_time=3)
        )

        if not nav_result.success:
            return {"error": f"Failed to navigate to {url}"}

        # Scroll to load more content
        for i in range(3):
            await self.browser_tool.execute(
                BrowserAction("scroll", "bottom", wait_time=2)
            )

        # Extract post links
        posts_result = await self.browser_tool.execute(
            BrowserAction("extract", 'a[href*="/p/"]')
        )

        if not posts_result.success:
            return {"error": "Failed to extract posts"}

        posts_data = []
        post_links = [item.get('href', '') for item in posts_result.data[:limit]]

        for i, post_url in enumerate(post_links):
            if i >= limit:
                break

            print(f"Analyzing Instagram post {i + 1}/{len(post_links)}")

            # Navigate to individual post
            post_nav = await self.browser_tool.execute(
                BrowserAction("navigate", post_url, wait_time=2)
            )

            if post_nav.success:
                # Extract post details
                post_data = await self._extract_instagram_post_data()
                if post_data:
                    posts_data.append(post_data)

        return {
            "platform": "Instagram",
            "hashtag": hashtag,
            "posts": posts_data,
            "total_found": len(posts_data)
        }

    async def _extract_instagram_post_data(self) -> Dict:
        """Extract data from current Instagram post page"""
        try:
            # Extract various elements
            caption_result = await self.browser_tool.execute(
                BrowserAction("extract", 'h1, [data-testid="post-caption"], article div:has(span)')
            )

            likes_result = await self.browser_tool.execute(
                BrowserAction("extract", 'button span, section span')
            )

            author_result = await self.browser_tool.execute(
                BrowserAction("extract", 'header a, h2 a')
            )

            # Process extracted data
            caption = ""
            if caption_result.success and caption_result.data:
                caption = next((item['text'] for item in caption_result.data if item['text']), "")

            author = ""
            if author_result.success and author_result.data:
                author = next((item['text'] for item in author_result.data if item['text']), "")

            # Extract engagement numbers
            likes = 0
            if likes_result.success and likes_result.data:
                for item in likes_result.data:
                    text = item.get('text', '')
                    if text and any(keyword in text.lower() for keyword in ['like', 'heart']):
                        # Extract number from text
                        numbers = re.findall(r'[\d,]+', text)
                        if numbers:
                            likes = int(numbers[0].replace(',', ''))
                            break

            # Detect content type
            media_result = await self.browser_tool.execute(
                BrowserAction("extract", 'video, img[alt*="Photo"], img[alt*="Video"]')
            )

            content_type = "image"
            if media_result.success and media_result.data:
                if any('video' in str(item).lower() for item in media_result.data):
                    content_type = "video"
                elif len(media_result.data) > 2:
                    content_type = "carousel"

            return {
                "caption": caption[:500],  # Limit length
                "author": author,
                "likes": likes,
                "content_type": content_type,
                "url": self.browser_tool.page.url if self.browser_tool.page else "",
                "extracted_at": datetime.now().isoformat()
            }

        except Exception as e:
            print(f"Error extracting Instagram post data: {e}")
            return None

    async def _scrape_twitter(self, hashtag: str, limit: int) -> Dict:
        """Scrape Twitter hashtag search"""
        search_url = f"https://twitter.com/search?q=%23{hashtag.replace('#', '')}&f=top"

        nav_result = await self.browser_tool.execute(
            BrowserAction("navigate", search_url, wait_time=3)
        )

        if not nav_result.success:
            return {"error": f"Failed to navigate to Twitter search"}

        # Scroll to load more tweets
        for i in range(3):
            await self.browser_tool.execute(
                BrowserAction("scroll", "bottom", wait_time=2)
            )

        # Extract tweets
        tweets_result = await self.browser_tool.execute(
            BrowserAction("extract", '[data-testid="tweet"]')
        )

        if not tweets_result.success:
            return {"error": "Failed to extract tweets"}

        tweets_data = []

        # Process each tweet element
        for i, tweet_element in enumerate(tweets_result.data[:limit]):
            if i >= limit:
                break

            # Extract tweet details (this would need more specific selectors)
            tweet_data = {
                "text": tweet_element.get('text', ''),
                "author": "Unknown",  # Would extract from specific selectors
                "likes": 0,  # Would extract from like buttons
                "retweets": 0,  # Would extract from retweet buttons
                "content_type": "text",
                "url": "",
                "extracted_at": datetime.now().isoformat()
            }

            tweets_data.append(tweet_data)

        return {
            "platform": "Twitter",
            "hashtag": hashtag,
            "posts": tweets_data,
            "total_found": len(tweets_data)
        }

    async def cleanup(self):
        """Cleanup resources"""
        await self.browser_tool.cleanup()


class SocialMediaViralAgent(BaseAgent):
    """Social Media Viral Content Agent using Google ADK"""

    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.web_scraper = WebScrapingTool()
        self.llm_client = LLMClient(model_name="gemini-2.0-flash-exp")  # Use actual Gemini model
        self.memory = MemoryManager()

    async def initialize(self):
        """Initialize the agent"""
        await super().initialize()
        print("🤖 Social Media Viral Agent initialized")

    async def handle_message(self, message: Message) -> Response:
        """Handle incoming messages"""
        content = message.content.lower()

        if "analyze hashtag" in content or "hashtag analysis" in content:
            return await self._handle_hashtag_analysis(message)
        elif "help" in content:
            return self._get_help_message()
        else:
            return Response(
                content="I can help you analyze viral social media content. Try saying 'analyze hashtag #AI' or 'help' for more options.",
                metadata={"type": "info"}
            )

    async def _handle_hashtag_analysis(self, message: Message) -> Response:
        """Handle hashtag analysis requests"""
        # Extract hashtag from message
        hashtag_match = re.search(r'#(\w+)', message.content)
        if not hashtag_match:
            return Response(
                content="Please specify a hashtag to analyze, like: analyze hashtag #AI",
                metadata={"type": "error"}
            )

        hashtag = hashtag_match.group(1)

        try:
            print(f"🔍 Starting analysis for #{hashtag}")

            # Store in memory
            self.memory.store("current_hashtag", hashtag)
            self.memory.store("analysis_start_time", datetime.now().isoformat())

            # Scrape Instagram
            instagram_data = await self.web_scraper.scrape_social_media("instagram", hashtag, 15)

            # Scrape Twitter
            twitter_data = await self.web_scraper.scrape_social_media("twitter", hashtag, 15)

            # Combine results
            all_posts = []
            if instagram_data.get("posts"):
                all_posts.extend(instagram_data["posts"])
            if twitter_data.get("posts"):
                all_posts.extend(twitter_data["posts"])

            if not all_posts:
                return Response(
                    content=f"❌ No viral content found for #{hashtag}. The hashtag might be too new or have limited public posts.",
                    metadata={"type": "warning"}
                )

            # Analyze with LLM
            analysis_prompt = f"""
            Analyze these {len(all_posts)} social media posts for hashtag #{hashtag}:

            Posts data: {json.dumps(all_posts[:10], indent=2)}  # Limit for prompt size

            Provide insights about:
            1. Most viral content types
            2. Common themes and topics
            3. Engagement patterns
            4. Content strategy recommendations

            Format as JSON with clear insights.
            """

            llm_response = await self.llm_client.generate_async(analysis_prompt)

            # Format response
            response_content = f"""
🎯 **Viral Content Analysis for #{hashtag}**

📊 **Data Collected:**
• Instagram posts: {len(instagram_data.get('posts', []))}
• Twitter posts: {len(twitter_data.get('posts', []))}
• Total analyzed: {len(all_posts)}

🔍 **AI Analysis:**
{llm_response.text}

🏆 **Top Viral Posts:**
"""

            # Add top posts
            sorted_posts = sorted(all_posts, key=lambda x: x.get('likes', 0), reverse=True)
            for i, post in enumerate(sorted_posts[:3], 1):
                response_content += f"\n{i}. @{post.get('author', 'Unknown')} - {post.get('likes', 0)} likes"
                response_content += f"\n   \"{post.get('caption', '')[:100]}...\""

            # Save results
            analysis_result = {
                "hashtag": hashtag,
                "timestamp": datetime.now().isoformat(),
                "posts": all_posts,
                "instagram_data": instagram_data,
                "twitter_data": twitter_data,
                "llm_analysis": llm_response.text
            }

            filename = f"viral_analysis_{hashtag}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w') as f:
                json.dump(analysis_result, f, indent=2)

            response_content += f"\n\n💾 **Full analysis saved to:** {filename}"

            return Response(
                content=response_content,
                metadata={
                    "type": "analysis_complete",
                    "hashtag": hashtag,
                    "total_posts": len(all_posts),
                    "filename": filename
                }
            )

        except Exception as e:
            return Response(
                content=f"❌ Error analyzing #{hashtag}: {str(e)}",
                metadata={"type": "error", "error": str(e)}
            )

        finally:
            # Cleanup browser resources
            await self.web_scraper.cleanup()

    def _get_help_message(self) -> Response:
        """Get help message"""
        help_content = """
🤖 **Social Media Viral Agent - Help**

**Available Commands:**
• `analyze hashtag #YourHashtag` - Analyze viral content for a hashtag
• `help` - Show this help message

**Examples:**
• "analyze hashtag #AI"
• "analyze hashtag #tech" 
• "analyze hashtag #innovation"

**Features:**
✅ Instagram hashtag analysis
✅ Twitter hashtag search
✅ Viral content extraction
✅ AI-powered insights
✅ Engagement metrics
✅ Content type detection
✅ Results export to JSON

**Note:** Analysis may take 1-2 minutes depending on content volume.
        """

        return Response(
            content=help_content,
            metadata={"type": "help"}
        )

    async def cleanup(self):
        """Cleanup agent resources"""
        await self.web_scraper.cleanup()
        await super().cleanup()


# Agent Runner
async def main():
    """Run the Social Media Viral Agent"""

    # Configure the agent
    config = AgentConfig(
        name="SocialMediaViralAgent",
        description="Analyzes viral social media content using browser automation",
        version="1.0.0"
    )

    # Create and initialize agent
    agent = SocialMediaViralAgent(config)
    await agent.initialize()

    print("🚀 Social Media Viral Agent is ready!")
    print("💡 Try: 'analyze hashtag #AI' or 'help'")

    try:
        # Interactive loop
        while True:
            user_input = input("\n👤 You: ").strip()

            if user_input.lower() in ['quit', 'exit', 'bye']:
                break

            if user_input:
                message = Message(content=user_input)
                response = await agent.handle_message(message)
                print(f"\n🤖 Agent: {response.content}")

    except KeyboardInterrupt:
        print("\n👋 Goodbye!")

    finally:
        await agent.cleanup()


if __name__ == "__main__":
    asyncio.run(main())