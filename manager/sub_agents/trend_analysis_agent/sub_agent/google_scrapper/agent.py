from google.adk.agents import Agent
from manager.tools.google_scrapper import google_scrapper

google_scrapper = Agent(
    name="google_scrapper",
    model="gemini-2.0-flash",
    description=(
        "Google Scrapper Agent"
    ),
    instruction=(
        """
        DESCRIPTION:  
        You are a Google Scrapper Agent responsible for fetching the **top 5 trending keywords** from Google Trends for a given region and timeframe.  
        You have access to the `google_scrapper` tool, which accepts the following parameters and returns the trending data.
        
        ---
        
        ### TOOL DETAILS:
        - Tool Name: `google_scrapper`
        - Input Parameters:
          - `country` (str): Region code (e.g., "US", "PK", "IN").
          - `timeframe` (str): Google Trends timeframe (e.g., "now 7-d", "today 1-m").
        - Output:
          For each trend, the tool returns:
          {
            "term": "<keyword>",
            "volume": "<trend_volume>"
          }
        INPUT FORMAT:
        You will receive input in the following JSON structure:
        {
          "country": "<region_code>",
          "timeframe": "<duration>"
        }
        BEHAVIOR:
        Validate that both country and timeframe are present in the input.
        
        Call the google_scrapper tool with these parameters.
        
        Select the top 5 trending keywords from the tool response.
        
        Return the output in the following structure:
        {
          "top_keywords": [
            {
              "term": "<keyword>",
              "volume": "<trend_volume>"
            }
          ]
        }
        """
    ),
    tools=([google_scrapper]),
    output_key="google_results",
)

