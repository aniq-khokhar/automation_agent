import time
from google import genai
from google.genai.types import GenerateVideosConfig
import json

client = genai.Client()


def vid_generation(prompt: str, userid: int, filename: str, bucket_name: str) -> str:
    """
    Generate a video with Veo3 and save it directly to GCS.

    Args:
        prompt (str): Prompt for the video.
        userid (int): User ID (used as directory in GCS).
        filename (str): Output filename.
        bucket_name (str): GCS bucket name.

    Returns:
        str: GCS URI of the generated video.
    """

    # Path where video will be stored in GCS
    output_gcs_uri = f"gs://{bucket_name}/{userid}/{filename}"

    # Request video generation
    operation = client.models.generate_videos(
        model="veo-3.0-generate-001",
        prompt=prompt,
        config=GenerateVideosConfig(
            aspect_ratio="16:9",
            output_gcs_uri=output_gcs_uri,
        ),
    )

    # Poll until the video is ready
    while not operation.done:
        time.sleep(15)
        operation = client.operations.get(operation)

    # Return final GCS URI
    return output_gcs_uri



def batch_vid_generation(prompts: list, userid: int, bucket_name: str) -> list:
    """
    Generate a batch of videos with Veo3 based on a multi-part JSON prompt.

    Args:
        prompts (list): List of JSON objects, each containing a "video_prompt".
        userid (int): User ID (used as directory in GCS).
        bucket_name (str): GCS bucket name.

    Returns:
        list: List of GCS URIs of generated videos.
    """
    gcs_uris = []

    for part in prompts:
        part_num = part.get("part")
        video_prompt = part.get("video_prompt")

        # Convert video_prompt dict into a usable string for the model
        # (You can format this however Veo3 expects)
        prompt_text = json.dumps(video_prompt, indent=2)

        # Construct filename (e.g., "part_1.mp4", "part_2.mp4", etc.)
        filename = f"part_{part_num}.mp4"
        output_gcs_uri = f"gs://{bucket_name}/{userid}/{filename}"

        # Request video generation
        operation = client.models.generate_videos(
            model="veo-3.0-generate-001",
            prompt=prompt_text,
            config=GenerateVideosConfig(
                aspect_ratio="16:9",
                output_gcs_uri=output_gcs_uri,
            ),
        )

        # Poll until ready
        while not operation.done:
            time.sleep(15)
            operation = client.operations.get(operation)

        # Save URI
        gcs_uris.append(output_gcs_uri)

    return gcs_uris




def main():
    # Sample test values
    test_prompt = """
    Create a cinematic 10-second video of a sunrise over snowy mountains.
    Show a gradual warm glow as the sun rises, casting golden light.
    Include soft background music, and overlay text: 'A New Dawn'.
    """
    userid = 12345
    filename = "test_sunrise.mp4"
    bucket_name = "my-veo3-videos"   # <-- replace with your actual GCS bucket name

    try:
        result_uri = vid_generation(
            prompt=test_prompt,
            userid=userid,
            filename=filename,
            bucket_name=bucket_name,
        )
        print("✅ Video generation successful!")
        print("GCS URI:", result_uri)

    except Exception as e:
        print("❌ Error during video generation:", str(e))


if __name__ == "__main__":
    main()