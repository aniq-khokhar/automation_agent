import google.generativeai as genai
import time

def upload_to_gemini(path, mime_type=None):
    """Uploads the given file to Gemini.

    See https://ai.google.dev/gemini-api/docs/prompting_with_media
    """
    file = genai.upload_file(path, mime_type=mime_type)
    print(f"Uploaded file '{file.display_name}' as: {file.uri}")
    return file

def analyze_video_with_gemini(video_path, api_key):
    genai.configure(api_key=api_key)
    print("Uploading file...")
    video_file = upload_to_gemini(video_path, mime_type="video/mp4")

    # Make the LLM request.
    print("Making LLM inference request...")
    model = genai.GenerativeModel(model_name="models/gemini-1.5-pro-latest")
    response = model.generate_content(["Provide a detailed summary of the video.", video_file],
                                      request_options={"timeout": 600})

    # Clean up the uploaded file.
    print(f"Deleting file...")
    genai.delete_file(video_file.name)

    return response.text