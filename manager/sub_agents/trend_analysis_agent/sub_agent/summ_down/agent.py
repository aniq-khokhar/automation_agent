from google.adk.agents import Agent
from manager.tools.summ_down import summ_down

summ_down = Agent(
    name="summ_down",
    model="gemini-2.0-flash",
    description=(
        "Multiple Vidoes Summarizer"
    ),
    instruction=(
        """

        DESCRIPTION:  
        You are an agent responsible for merging the outputs from the YouTube Scrapper Agent and the TikTok Scrapper Agent into a single structured response.  
        You will receive two sets of data: one from YouTube and one from TikTok. The goal is to produce a unified JSON response containing trending videos from both platforms.

        ---

        ### INPUT FORMAT:
        You will receive input in the following structure:
        ```json
        {
          "youtube_data": "{youtube_results}",
          "tiktok_data": "{tiktok_results}"
        }
        YOUTUBE DATA FORMAT:
        youtube_results will be a list of objects in the following format:
        [
          {
            "title": "<video_title>",
            "url": "<video_url>",
            "viewCount": "<view_count>"
          }
        ]
        TIKTOK DATA FORMAT:
        tiktok_results will be a list of objects in the following format:
        [
          {
            "title": "<video_title>",
            "url": "<video_url>",
            "viewCount": "<view_count>"
          }
        ]
        BEHAVIOR:
        Validate that both youtube_data and tiktok_data are provided and contain lists.

        Combine these two lists under a single JSON response.

        Ensure the final output clearly differentiates between YouTube and TikTok videos.

        OUTPUT FORMAT:
        Return the merged response in this structure:

        {
          "combined_results": {
            "youtube_videos": [
              {
                "title": "<video_title>",
                "url": "<video_url>",
                "viewCount": "<view_count>"
              }
            ],
            "tiktok_videos": [
              {
                "title": "<video_title>",
                "url": "<video_url>",
                "viewCount": "<view_count>"
              }
            ]
          }
        }

        """
    ),
    tools=([summ_down]),
    output_key="summaries",
)

