import time
import io
from google import genai
from google.genai import types
from tempfile import NamedTemporaryFile
import tempfile
from moviepy import VideoFileClip, concatenate_videoclips

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




def vid_compiler(file_refs: list[str]) -> bytes:
    """
    Downloads videos from VEO3 using file references, merges them in order,
    and returns the final merged video as bytes (no intermediate disk saves).

    Args:
        file_refs (list[str]): List of VEO3 file references (video.video.name).

    Returns:
        bytes: The merged MP4 video file as bytes.
    """
    clips = []

    for file_ref in file_refs:
        # Download the video into an in-memory buffer
        file_data = io.BytesIO()
        client.files.download(file=file_ref)
        file_ref.save(file_data)  # Same style as "video.video.save(...)" but into BytesIO
        file_data.seek(0)

        # MoviePy can't load directly from BytesIO, so we use a temporary file
        with NamedTemporaryFile(suffix=".mp4", delete=False) as temp_video:
            temp_video.write(file_data.read())
            temp_video.flush()
            clip = VideoFileClip(temp_video.name)
            clips.append(clip)

    # Merge all clips
    final_clip = concatenate_videoclips(clips, method="compose")

    # Save merged video to in-memory buffer
    output_buffer = io.BytesIO()
    with NamedTemporaryFile(suffix=".mp4", delete=False) as temp_output:
        final_clip.write_videofile(temp_output.name, codec="libx264", audio_codec="aac")
        temp_output.seek(0)
        output_buffer.write(temp_output.read())

    # Cleanup MoviePy clips
    for clip in clips:
        clip.close()
    final_clip.close()

    output_buffer.seek(0)
    return output_buffer.read()