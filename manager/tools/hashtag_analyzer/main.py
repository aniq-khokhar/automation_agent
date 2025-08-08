# main.py - Example usage of the hashtag analyzer

from hashtag_analyzer import process_hashtags

if __name__ == '__main__':
    # Define the hashtags you want to analyze
    my_hashtags = ['#nature', '#technology']

    # Call the main function to process the hashtags
    # The function will handle printing its own progress
    video_summaries = process_hashtags(my_hashtags)

    # Print the final results
    print("\n--- Final Summaries ---")
    print(video_summaries)
