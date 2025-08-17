from apify_client import ApifyClient
import os
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv("APIFY_API_TOKEN")
client = ApifyClient(API_TOKEN)

def google_scrapper(country: str, timeframe: str)-> list[dict]:
    """
    Fetch trending Google searches for a given category and timeframe.

    Args:
        Country (str): The category for trending searches (example: 'all', 'sports', 'business').
        timeframe (str): Timeframe in hours or days (example: '24', '7d', '30d').

    Returns:
        list: A list of trending search data.
    """


    # Prepare the Actor input
    run_input = {
        "enableTrendingSearches": True,
        "fetchRegionalData": False,
        "proxyConfiguration": {
            "useApifyProxy": True,
            "apifyProxyGroups": []
        },
        "trendingSearchesCountry": "US",
        "trendingSearchesTimeframe": timeframe,   # From function parameter
        "rendingSearchesCountry": country      # New category field
    }

    # Run the Actor and wait for it to finish
    run = client.actor("nWhM7vTPu16lcwuIg").call(run_input=run_input)

    # Fetch and return Actor results from the run's dataset
    results = []
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        if "trending_searches" in item:
            top_5 = item["trending_searches"][:5]
            for trend in top_5:
                results.append({
                    "term": trend["term"],
                    "volume": trend["trend_volume"]
                })

    return results

# # Example usage:
# if __name__ == "__main__":
#     trending_data = google_scrapper(country="US", timeframe="24")
#     for entry in trending_data:
#         print(entry)
