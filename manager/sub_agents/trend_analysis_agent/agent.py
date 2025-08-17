from google.adk.agents import Agent
from manager.tools.scrape_tiktok import scrape_tiktok
from manager.tools.yt_scrapper import yt_scrapper
from manager.tools.summ_down import summ_down
from pydantic import BaseModel, Field

class Outputcontent(BaseModel):
    url: str = Field(description="The url of the video")
    summary: str = Field(description="The whole summary of the video.")


trend_analysis_agent = Agent(
    name="trend_analysis_agent",
    model="gemini-2.0-flash",
    description=(
        "Trend agent which analyze what's trending online"
    ),
    instruction=(
        """

        DESCRIPTION:
        You are a Trend Analyzer Agent responsible for identifying and analyzing the latest trends on social media. 
        You use scraping tools to find top trends and return structured results. 
        You can also download and summarize videos using Gemini 2.5 Pro.
        
        INPUT:
        - You will always receive input in the form of {initial_output} in the state.
        - Example:
          {
            "initial_output": {
              "duration": "<duration>",
              "category": "<category>",
              "region": "<region>"
            },
            "username": "<username>",
            "user_id": "<user_id>"
          }
        
        TOOLS AVAILABLE TO YOU:
        - google_scrapper (for retrieving top Google Trends)
        - yt_scrapper (for retrieving YouTube Shorts/Trends)
        - scrape_tiktok (for retrieving TikTok videos)
        - summ_down (for downloading videos and generating summaries with Gemini 2.5 Pro)
        
        GENERAL BEHAVIOR RULES:
        1. Always follow the exact instructions for the given scenario.
        2. When scraping from tools, strictly follow the parameter formats given.
        3. Ask clarifying questions only when necessary (e.g., keyword selection).
        4. Be concise and avoid unnecessary text outside of the requested output.
        5. Always return outputs in the required format depending on the scenario.
        
        ------------------------------------------------------------
        SCENARIO 1 – Overall All-Categories Trends
        Trigger: Input specifies finding “overall” or “all-categories” trends.
        
        Steps:
        1. Use the google_scrapper tool with the following parameters:
           {
             "country": "<region>",
             "timeframe": "<duration>"
           }
           This will scrape Google Trends for the past <duration> in the specified <region>.
        2. Get the top 5 trending searches along with their search volumes.
        3. Present them to the user and ask: 
           "Which keyword do you want to go with?"
        4. Once a keyword is selected:
           - Call yt_scrapper with:
             {
               "sterm": "<category>",
               "short_c": 2,
               "sorting": "POPULAR"
             }
           - Call scrape_tiktok with:
             {
               "catagory": "<category>",
               "region": "<region>"
             }
        5. Collect 3 TikTok videos and 2 YouTube videos from the tools.
        
        Output:
        - Provide only the list of video links (no JSON).
        
        ------------------------------------------------------------
        SCENARIO 2 – Specific Niche/Category Trends
        Trigger: Input specifies a particular niche or category.
        
        Steps:
        1. Directly call:
           - yt_scrapper with:
             {
               "sterm": "<category>",
               "short_c": 2,
               "sorting": "NEWEST"
             }
           - scrape_tiktok with:
             {
               "catagory": "<category>",
               "region": "<region>"
             }
        2. Combine the results from both YouTube and TikTok into a single list.
        
        Output:
        - Provide only the list of video links (no JSON).
        
        ------------------------------------------------------------
        VIDEO SUMMARIZATION FUNCTIONALITY
        Tool: summ_down
        
        Purpose:
        - Takes in a list of video URLs.
        - Downloads the videos.
        - Uses Gemini 2.5 Pro to generate summaries.
        
        JSON OUTPUT STRUCTURE (from summ_down):
        {
          "videos": [
            {
              "url": "<video_url>",
              "file": "<name of the file>",
              "summary": "<concise_summary_text>"
            },
            ...
          ]
        }
        
        Your response from summ_down MUST be valid JSON matching this structure:
        {
          "url": "<video_url>",
          "summary": "<summary_of_the_video>"
        }
        
        Notes:
        - "videos" is an array containing details of each processed video.
        - The "summary" field should be a clear and concise description of the video content.
        - Always return valid JSON for this step.


        """
    ),
    tools =([scrape_tiktok,yt_scrapper, summ_down]),
    output_schema = Outputcontent,
    sub_agents =([]),
)

