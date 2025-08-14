import time
from google import genai
from google.genai import types

client = genai.Client()

def vid_generation(prompt: str) -> str:
    operation = client.models.generate_videos(
        model="veo-3.0-generate-preview",
        prompt=prompt
    )

    # Wait until video is ready
    while not operation.done:
        time.sleep(20)
        operation = client.operations.get(operation)

    # Get the file reference for later download
    generated_video = operation.result.generated_videos[0]
    file_ref = generated_video.video.name  # Unique file identifier on Google's servers

    return file_ref


def batch_vid_generation(prompts: list[str]) -> list[str]:
    """
    Generates videos for a list of prompts using Google VEO3 and returns their file references.

    Args:
        prompts (list[str]): A list of video prompts.

    Returns:
        list[str]: A list of file reference strings for later download.
    """
    file_refs = []

    for prompt in prompts:
        # Request video generation
        operation = client.models.generate_videos(
            model="veo-3.0-generate-preview",
            prompt=prompt
        )

        # Wait until video is ready
        while not operation.done:
            time.sleep(20)
            operation = client.operations.get(operation)

        # Extract the file reference from the result
        generated_video = operation.result.generated_videos[0]
        file_ref = generated_video.video.name  # Unique file ID on Google's servers
        file_refs.append(file_ref)

    return file_refs