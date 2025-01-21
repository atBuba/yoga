import streamlit as st
import requests
import os
import re
import openai
from tools import *
import random
from openai import OpenAI

def process_song(mp3_file, txt_file):
    """Process song text file and generate structured prompts."""

    with open(txt_file, "r") as file:  # Можно использовать "a" для добавления текста
        text = file.read()

    # Parse the response into a structured format
    pattern = r"\*\*Строчки песни\*\*:\s+(.+?)\n\n\*\*Промт для модели генерирующей изображения\*\*:\s+(.+?)(?=\n\n|\Z)"

    # pattern = r"\#\#\#\# Строчки песни:\s+(.+?)\n\n\*\*Промт для модели генерирующей изображения\*\*:\s+(.+?)(?=\n\n|\Z)"
    matches = re.findall(pattern, text, re.S)

    # image_lyrics = []
    
    prompts_translated = []
    for match in matches:
        lyrics = match[0].strip()
        prompt = match[1].strip()
        translated_prompt = translate_text(prompt)
        # image_lyrics.appned(lyrics)
        prompts_translated.append({"lyrics": lyrics, "prompt": translated_prompt, "image_url": ""})

    # two_line = ''
    
    # for line in song_text.split('\n'):
    #     if line not in image_lyrics:
    #         two_line += ' ' +  

    return prompts_translated

    # return [{"lyrics": match[0].strip(), "prompt": match[1].strip()} for match in matches]

def generate_image_for_prompt(prompt):
    """Send a request to the Flask app to generate an image for a prompt."""
    FLASK_API_URL = "http://localhost:5000/generate"
    payload = {
        "prompt": prompt,
        "seed": 0,
        "height": 720,
        "width": 1280,
        "guidance_scale": 3.5,
        "num_inference_steps": 25, 
        "seed": random.randint(0, 2**32 - 1), 
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
    
def create_video(image_path, duration):

    payload = {
        'image_path': image_path,
        'duration': duration
    }

    response = requests.post("http://127.0.0.1:6000/process_images", json=payload)

    if response.status_code == 200:
        video_url = response.json().get('video_url')
        return video_url
    else:
        return None

def adiou_to_time_text(audio_path, text_path):

    payload = {
        'audio_path': audio_path,
        'text_path': text_path,
        'language': 'iso',
    }

    response = requests.post("http://127.0.0.1:7000/align", json=payload)

    if response.status_code == 200:
        video_url = response.json().get('word_timestamps')
        return video_url
    else:
        return None


def create_videos(prompts_data, txt_file):
    print("НАААЧАААЛИ!!!!")

    images = []
    for i in prompts_data:
        images.append(i["image_url"])
        
    subtitles = True
    font_path = "font/Faberge-Regular.otf"
    font_fill_color = "white"
    font_size= 90  

    # path to files 
    audio_path = 'static/mp3_file.mp3'
    ttml_file_lines = 'static/ttml_file_lines.ttml'
    ttml_file_words = 'static/ttml_file_words.ttml'

    output_video_avi = 'video/final_video.mp4'
    output_video_mp4 = 'video/final_video_with_audio_1.mp4'

    lyrics_file = 'static/lyrics.txt'
    
    if check_file_exists(ttml_file_lines) and check_file_exists(ttml_file_words):
        ttml_words = parse(ttml_file=ttml_file_words)
        ttml_two_lines = parse(ttml_file=ttml_file_lines, two_lines=True)
        ttml_lines = parse(ttml_file=ttml_file_lines)
    elif check_file_exists(audio_path) and check_file_exists(lyrics_file):
        ttml_words = adiou_to_time_text(audio_path, lyrics_file)
        ttml_lines = parse(txt_files=lyrics_file)
        ttml_two_lines = parse(txt_files=lyrics_file, two_lines=True)
    else: 
        ttml_words = parse(txt_files=lyrics_file, word=True)
        ttml_two_lines = parse(txt_files=lyrics_file, two_lines=True)
        ttml_lines = parse(txt_files=lyrics_file)
     
    generate_ass(ttml_words, ttml_lines, output_file="static/subtitles.ass")
    
    duration = 0
    j = -1
    videos = []
    # prompts_data = prompts_data[:6:]
    for image_path, line in zip(images, prompts_data):   
        j += len(line['lyrics'].split())
        print(ttml_words[j])
        video_url = create_video(image_path=image_path, duration=ttml_words[j]['end'] - duration)
        videos.append(VideoFileClip(video_url))
        duration = ttml_words[j]['end']
        
    
    create_slideshow(videos, ttml_words, ttml_lines, font=font_path, font_color=font_fill_color, output_path = output_video_avi, addSubtitles=subtitles, font_size=font_size)

    if check_file_exists(ttml_file_lines) and check_file_exists(audio_path):
        add_audio_to_video('video/temp_video.mp4', audio_path, output_video_mp4)


    if output_video_mp4:
        return output_video_mp4
    else:
        return 'error'

# Загрузка модели Sambanova
client = OpenAI(
    api_key="51739d1a-35eb-4bf0-a78b-dd1c1f65fc1b",
    base_url="https://api.sambanova.ai/v1",
)

# Инициализация состояния
if "openai_model" not in st.session_state:
    st.session_state["openai_model"] = "Qwen2.5-72B-Instruct"

if "messages" not in st.session_state:
    st.session_state.messages = []

if "current_page" not in st.session_state:
    st.session_state["current_page"] = "main"  # Устанавливаем начальную страницу

# Устанавливаем роль модели (скрыто от пользователя)
if "role_message" not in st.session_state:
    st.session_state.role_message = (
        '''Ты должен создать слайд-шоу клип для песни, раздели текст песни на смыссловые части, напиши промпт для модели, которая будет генерировать изображения по этим строчкам, изображения должны быть связанны друг с другом, весь клип должен отражать смысл песни, передавать ее настроение. Распиши подробно, во что одеты люди и как они стоят, в каких тонах должно быть изображение, какого настроение это изображения, в каком стиле. Главные персонажи должны на всех изображениях выглядеть одинаково, стиль всего слайд-шоу должен быть един, цветовая палитра всех картинок должна быть одинакова, укажи, в какое время или исторический период происходят действия, у всех картинок этот период должен быть одинаковый.
Ответь в следующем формате:
**Строчки песни**: 
Строчки песни которые будут показываться вместе с этой картинкой

**Промт для модели генерирующей изображения**:(максимальное количество слов 77)
Укажи стиль(реалистичный), настроение, в каких цветах должно быть выполнено изображение, время или исторический промежуток, в который происходят события, затем опиши, что должно быть изображено на картинке, во что одеты персонажи.
используй все строчки песни, даже если они повторяются.
текст песни: '''
    )

# Добавляем роль модели в историю сообщений только для запроса
if len(st.session_state.messages) == 0:
    st.session_state.messages.append({
        "role": "system", 
        "content": st.session_state.role_message
    })


# Логика страниц
if st.session_state["current_page"] == "main":
    st.title("Создание слайд-шоу для песни")
    
    # Отображение истории сообщений
    for message in st.session_state.messages:
        if message["role"] != "system":  # Исключаем системное сообщение
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    # Ввод пользователя
    if user_input := st.chat_input("Введите ваш вопрос или текст..."):
        # Добавляем сообщение пользователя в историю
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        # Отправляем запрос модели
        with st.chat_message("assistant"):
            with st.spinner("Qwen2.5-72B is generating a response..."):
                # Формируем историю чата для отправки модели
                messages = [
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages
                ]

                # Генерация ответа с потоковой передачей
                response = ""
                response_container = st.empty()
                stream = client.chat.completions.create(
                    model=st.session_state["openai_model"],
                    messages=messages,
                    stream=True,
                    temperature=0.7,
                    top_p=0.9,
                    max_tokens=3500,
                )

                for chunk in stream:
                    if chunk.choices:
                        token = chunk.choices[0].delta.content
                        response += token
                        response_container.markdown(response)

                # Добавляем финальный ответ в историю
                st.session_state.messages.append({"role": "assistant", "content": response})
    
    # Кнопка для перехода на страницу загрузки MP3-файла
    if st.button("Перейти к загрузке MP3-файла"):
        st.session_state["current_page"] = "upload"
        st.rerun() 

elif st.session_state["current_page"] == "upload":
    # Streamlit App
    st.title("MP3 & Lyrics Image Generator")

    # File upload section
    mp3_file = st.file_uploader("Upload an MP3 file", type=["mp3"])
    if mp3_file is not None:
        with open("static/mp3_file.mp3", "wb") as f:
            f.write(mp3_file.read())
    txt_file = st.file_uploader("Upload a TXT file with lyrics", type=["txt"])
    if txt_file is not None:
        with open("static/lyrics.txt", "w", encoding="utf-8") as f:
            f.write(txt_file.read().decode("utf-8"))
    
    # Загрузка TXT файла с текстом
    text = st.session_state.messages[-1]["content"]
    with open("static/text.txt", "w", encoding="utf-8") as f:
        f.write(text)
    txt_file = "static/text.txt"

    # Initialize session state for images
    if "prompts_data" not in st.session_state:
        st.session_state.prompts_data = []

    # Generate Images Button
    if mp3_file and txt_file and st.button("Generate Images"):
        # Process files
        prompts_data = process_song(mp3_file, txt_file)
        
        # Add only new prompts
        new_prompts = []
        st.session_state.prompts_data = []
        for prompt_entry in prompts_data:
            if prompt_entry not in st.session_state.prompts_data:
                print(prompt_entry)
                new_prompts.append(prompt_entry)
                # st.session_state.prompts_data.append(prompt_entry)

        # Add new prompts to session state
        st.session_state.prompts_data.extend(new_prompts)
    
    # Display all generated images
    if st.session_state.prompts_data:
        st.write("### Generated Images")
        for entry in st.session_state.prompts_data:
            lyrics = entry["lyrics"]
            prompt = entry["prompt"]
            image_url = entry.get("image_url", None)
            
            # Display image if it exists; otherwise, generate and save it
            st.write(f"**Lyrics:** {lyrics}")
            st.write(f"**Prompt (Translated):** {prompt}")
            if image_url:
                st.image(image_url, caption=lyrics)
            else:
                with st.spinner(f"Generating image for: '{lyrics}'..."):
                    image_url = generate_image_for_prompt(prompt)
                    if image_url.startswith("static/"):
                        entry["image_url"] = image_url
                        st.image(image_url, caption=lyrics)
                    else:
                        st.error(image_url)

    # Generate Video Button
    if st.session_state.prompts_data and st.button("Generate Video"):
        with st.spinner("Creating video..."):
            video_url = create_videos(st.session_state.prompts_data, txt_file)
            if video_url and not video_url.startswith("Error"):
                st.video(video_url)
            else:
                st.error(f"Failed to create video: {video_url}")

    # Button to return to main page
    if st.button("Вернуться на главную"):
        st.session_state["current_page"] = "main"
        st.rerun()

