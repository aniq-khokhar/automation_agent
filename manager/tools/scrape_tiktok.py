from apify_client import ApifyClient
import os

# Initialize the ApifyClient with your API token
API_TOKEN = os.getenv("APIFY_API_TOKEN")
client = ApifyClient(API_TOKEN)


def scrape_tiktok(category: str, region: str, results_per_page: int = 3) -> list[dict]:
    """
    Scrape TikTok videos by category and region.

    Returns:
        list[dict]: A list of dictionaries, each containing:
            - description (str)
            - views (int)
            - link (str)
    """
    run_input = {
        "excludePinnedPosts": False,
        "proxyCountryCode": "US",
        "resultsPerPage": results_per_page,
        "scrapeRelatedVideos": False,
        "searchQueries": [category],
        "searchSection": "/video",
        "shouldDownloadAvatars": False,
        "shouldDownloadCovers": False,
        "shouldDownloadMusicCovers": False,
        "shouldDownloadSlideshowImages": False,
        "shouldDownloadSubtitles": False,
        "shouldDownloadVideos": True,
        "profileScrapeSections": ["videos"],
        "profileSorting": "latest",
        "maxProfilesPerQuery": 10
    }

    # Run the Actor
    run = client.actor("GdWCkxBtKWOsKjdch").call(run_input=run_input)

    # Collect results
    results = []
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        results.append({
            "title": item.get("text", ""),
            "url": item.get("webVideoUrl", ""),
            "viewCount": item.get("playCount", 0)
        })

    return results


# # Example usage
# if __name__ == "__main__":
#     data = scrape_tiktok("gaming", "US", 5)
#     print(data)
#
