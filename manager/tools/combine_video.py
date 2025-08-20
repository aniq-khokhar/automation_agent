import time
from google.cloud import video

def combine_videos(
    project_id: str,
    bucket_name: str,
    user_id: str,
    videolinks: list,
    location: str = "us-central1"
):
    """
    Combine multiple videos in GCS using Google Cloud Transcoder API.

    Args:
        project_id (str): Your Google Cloud project ID.
        bucket_name (str): GCS bucket name.
        user_id (str): Folder (user) where the output video will be stored.
        videolinks (list): List of GCS URIs of input videos.
        location (str, optional): Transcoder region (default="us-central1").

    Returns:
        str: GCS path to the final combined video.
    """

    client = video.TranscoderServiceClient()
    parent = f"projects/{project_id}/locations/{location}"

    # Define inputs and edit list
    inputs = {}
    edit_list = []
    for i, link in enumerate(videolinks):
        input_key = f"input{i}"
        inputs[input_key] = video.Input(uri=link)
        edit_list.append(video.EditAtom(key=f"atom{i}", inputs=[input_key]))

    # Define output path
    output_uri = f"gs://{bucket_name}/{user_id}/"
    output_file = "final_combined.mp4"

    # Create job config
    job_config = video.JobConfig(
        inputs=inputs,
        edit_list=edit_list,
        elementary_streams=[
            video.ElementaryStream(
                key="video_stream",
                video_stream=video.VideoStream(codec="h264")
            ),
            video.ElementaryStream(
                key="audio_stream",
                audio_stream=video.AudioStream(codec="aac")
            )
        ],
        mux_streams=[
            video.MuxStream(
                key="combined",
                container="mp4",
                elementary_streams=["video_stream", "audio_stream"]
            )
        ]
    )

    # Submit job
    job = video.Job(
        parent=parent,
        output_uri=output_uri,
        config=job_config,
    )

    response = client.create_job(parent=parent, job=job)
    job_name = response.name
    print(f"Job created: {job_name}")

    # Poll until job completes
    while True:
        job_state = client.get_job(name=job_name)
        if job_state.state == video.Job.ProcessingState.SUCCEEDED:
            print("✅ Transcoding job completed successfully.")
            break
        elif job_state.state == video.Job.ProcessingState.FAILED:
            raise RuntimeError("❌ Transcoding job failed.")
        else:
            print(f"Job in progress... current state: {job_state.state}")
            time.sleep(10)  # wait 10s before checking again

    return f"{output_uri}{output_file}"
