import streamlit as st
import requests
import os
import re
import openai
from tools import *

def process_song(mp3_file, txt_file):
    """Process song text file and generate structured prompts."""
    client = openai.OpenAI(
        api_key="51739d1a-35eb-4bf0-a78b-dd1c1f65fc1b",
        base_url="https://api.sambanova.ai/v1",
    )


    # Read the text file content
    song_text = txt_file.read().decode("utf-8")

    # Call the OpenAI API to process song
    response = client.chat.completions.create(
        model='Meta-Llama-3.1-405B-Instruct',
        messages=[
            {"role":"system","content":'''Ты должен создать слайд-шоу клип для песни, раздели текст песни на смысловые части, напиши промпт для модели которая будет генерировать изображения по этим строчкам, изображения должны быть связанны друг с другом, весь клип должен отражать смысл песни, передавать ее настроение. Распиши подробно во что одеты люди и как они стоят,  в каких тоннах должно быть изображение, какого настроение это изображения, в к каком стиле. Главные персонажи  должны на всех изображениях выглядеть одинаково, стиль всего слайд шоу должен быть един. Ты должен обязательно использовать все строчки песни
    Ответь в следующей форме: 
    **Строчки песни**: 
    Строчки песни которые будут показываться вместе с этой картинкой
    **Промт для модели генерирующей изображения**: 
    Тут указывай все подсказки для генерации изображения по строчкам из песни, укажи здесь настроение, главных персонажей, время и цветовую палитру 
    песня: 
    '''},
            {"role":"user","content":song_text}],
        temperature =  0.1,
        top_p = 0.1
    )

    text = response.choices[0].message.content

    # Parse the response into a structured format
    pattern = r"\*\*Строчки песни\*\*:\s+(.+?)\n\n\*\*Промт для модели генерирующей изображения\*\*:\s+(.+?)(?=\n\n|\Z)"
    matches = re.findall(pattern, text, re.S)


    prompts_translated = []
    for match in matches:
        lyrics = match[0].strip()
        prompt = match[1].strip()
        translated_prompt = translate_text(prompt)
        prompts_translated.append({"lyrics": lyrics, "prompt": translated_prompt})

    return prompts_translated

    # return [{"lyrics": match[0].strip(), "prompt": match[1].strip()} for match in matches]

def generate_image_for_prompt(prompt):
    """Send a request to the Flask app to generate an image for a prompt."""
    FLASK_API_URL = "http://localhost:5000/generate"
    payload = {
        "prompt": prompt,
        "seed": 0,
        "height": 480,
        "width": 848,
        "guidance_scale": 3.5,
        "num_inference_steps": 25
    }
    try:
        response = requests.post(FLASK_API_URL, json=payload)
        response_data = response.json()
        if response_data.get("success"):
            return response_data["image_url"]
        else:
            return f"Error: {response_data.get('error', 'Unknown error')}"
    except Exception as e:
        return f"Error: {str(e)}"
    
def create_video_request(images, durations):
    """Send a request to create a video from images."""
    FLASK_VIDEO_API_URL = "http://127.0.0.1:6000/process_images"
    payload = {
        "images": images,
        "durations": durations
    }
    try:
        response = requests.post(FLASK_VIDEO_API_URL, json=payload)
        if response.status_code == 200:
            return response.json().get("video_url")
        else:
            return f"Error: {response.text}"
    except Exception as e:
        return f"Error: {str(e)}"

# Streamlit App
st.title("MP3 & Lyrics Image Generator")

# File upload section
mp3_file = st.file_uploader("Upload an MP3 file", type=["mp3"])
txt_file = st.file_uploader("Upload a TXT file with lyrics", type=["txt"])

images = []
image_durations = []

# Generate Images Button
if mp3_file and txt_file and st.button("Generate Images"):
    # Process files
    prompts_data = process_song(mp3_file, txt_file)

    st.write("### Song Prompts")
    for entry in prompts_data:
        lyrics = entry["lyrics"]
        prompt = entry["prompt"]
        st.write(f"**Lyrics:** {lyrics}")
        st.write(f"**Prompt (Translated):** {prompt}")
        with st.spinner(f"Generating image for: '{lyrics}'..."):
            image_placeholder = st.empty()
            image_url = generate_image_for_prompt(prompt)  # Generate the image
            if image_url.startswith("static/"):
                image_placeholder.image(image_url)
                images.append(image_url)
                image_durations.append(5)  # Example duration for each image
            else:
                image_placeholder.error(image_url)

# Generate Video Button
if images and st.button("Generate Video"):
    with st.spinner("Creating video..."):
        video_url = create_video_request(images, image_durations)
        if video_url and not video_url.startswith("Error"):
            st.success("Video created successfully!")
            st.video(video_url)
        else:
            st.error(f"Failed to create video: {video_url}")
