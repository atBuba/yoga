import streamlit as st
import requests
import os
import re
import openai
from tools import *
import random
from openai import OpenAI
from streamlit_image_select import image_select
from datetime import datetime
from time import sleep
from PIL import Image, ImageDraw, ImageFont
import json
import shutil

# Функции для работы с состоянием и проектом
def create_project_folder():
    """Создает уникальную папку проекта на основе даты и времени."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    project_folder = f"project_{timestamp}"
    images_folder = os.path.join(project_folder, "images")
    videos_folder = os.path.join(project_folder, "videos")
    video_folder = os.path.join(project_folder, "video")
    audio_folder = os.path.join(project_folder, "audio")
    os.makedirs(project_folder, exist_ok=True)
    os.makedirs(images_folder, exist_ok=True)
    os.makedirs(videos_folder, exist_ok=True)
    os.makedirs(video_folder, exist_ok=True)
    os.makedirs(audio_folder, exist_ok=True)
    return project_folder

def save_state(state, filename="state.json", project_folder=None):
    """Сохраняет состояние приложения в JSON-файл внутри папки проекта."""
    if project_folder:
        filename = os.path.join(project_folder, filename)
    with open(filename, "w", encoding="utf-8") as f:
        state_to_save = {
            "openai_model": state["openai_model"],
            "messages": state["messages"],
            "current_page": state["current_page"],
            "prompts_data": state["prompts_data"],
            "project_folder": state.get("project_folder", ""),
            "final_video": state.get("final_video", None),  # Сохраняем путь к видео
        }
        json.dump(state_to_save, f, ensure_ascii=False, indent=4)

def load_state(filename="state.json", project_folder=None):
    """Загружает состояние приложения из JSON-файла."""
    if project_folder:
        filename = os.path.join(project_folder, filename)
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def copy_file_to_project(src_path, project_folder, new_name=None):
    """Копирует файл в папку проекта с возможностью переименования."""
    if not os.path.exists(src_path):
        return None
    if not new_name:
        new_name = os.path.basename(src_path)
    dest_path = os.path.join(project_folder, new_name)
    shutil.copy2(src_path, dest_path)
    return dest_path

# Инициализация базовых значений в st.session_state
if "project_folder" not in st.session_state:
    st.session_state["project_folder"] = None
if "current_page" not in st.session_state:
    st.session_state["current_page"] = "main"
if "openai_model" not in st.session_state:
    st.session_state["openai_model"] = "Qwen2.5-72B-Instruct"
if "messages" not in st.session_state:
    st.session_state.messages = []
if "prompts_data" not in st.session_state:
    st.session_state.prompts_data = []
if "final_video" not in st.session_state:
    st.session_state["final_video"] = None

# Инициализация selected_project в st.session_state
if "selected_project" not in st.session_state:
    st.session_state["selected_project"] = None

# Sidebar для выбора проекта
st.sidebar.title("Проекты")
existing_projects = [d for d in os.listdir() if d.startswith("project_")]

# Определяем index для st.selectbox на основе текущего выбранного проекта
if st.session_state["selected_project"] == "Создать новый":
    index = 0  # "Создать новый" — первый элемент списка
elif st.session_state["selected_project"] in existing_projects:
    index = existing_projects.index(st.session_state["selected_project"]) + 1  # +1 из-за "Создать новый"
else:
    index = None

selected_project = st.sidebar.selectbox(
    "Выберите проект",
    ["Создать новый"] + existing_projects,
    index=index,
    placeholder="Выберите проект...",
    label_visibility="collapsed"
)

# Обновление project_folder и selected_project
if selected_project:
    if selected_project == "Создать новый":
        new_project_folder = create_project_folder()
        st.session_state["project_folder"] = new_project_folder
        st.session_state["selected_project"] = new_project_folder  # Сохраняем новый проект как выбранный
        # Инициализация состояния для нового проекта
        st.session_state["openai_model"] = "Qwen2.5-72B-Instruct"
        st.session_state.messages = []
        st.session_state["current_page"] = "main"
        st.session_state.prompts_data = []
        st.session_state["final_video"] = None
    elif selected_project != st.session_state["project_folder"]:
        st.session_state["project_folder"] = selected_project
        st.session_state["selected_project"] = selected_project  # Обновляем выбранный проект
        initial_state = load_state(project_folder=st.session_state["project_folder"])
        if initial_state:
            for key, value in initial_state.items():
                st.session_state[key] = value
        else:
            # Если состояния нет, инициализируем базовые значения
            st.session_state["openai_model"] = "Qwen2.5-72B-Instruct"
            st.session_state.messages = []
            st.session_state["current_page"] = "main"
            st.session_state.prompts_data = []
            st.session_state["final_video"] = None
            
# Инициализация role_message, если его нет
if "role_message" not in st.session_state:
    st.session_state.role_message = (
        ''' 
    Use the entire text carefully. You need to create a slideshow clip for the song, you will receive the lyrics along with timestamps, write a hint to create an image in this frame. The frames that will be shown at the moment when there is no text should simply convey the atmosphere of the clip. Write a hint for the model that will generate images for these frames. The images should be connected to each other, and the entire clip should reflect the meaning of the song and convey its mood. Describe in detail what people are wearing and how they behave, in what colors the image should be, in what mood it should be and in what style. The main characters should look the same in all images, the style of the entire slideshow should be the same, the color palette of all images should be same, specify at what time or historical period the action takes place, all images should have the same period. The frames that will be shown with the text should convey what is said in these lines, these frames should be shown strictly in accordance with the text.
    Please respond in the following format:

    **Frame**: (without a number)
    a timestamp indicating when this frame will be shown in the format XX:XX:XX.XX - XX:XX:XX.XX 

    **Part of the song**: 
    Print out which part of the song this frame belongs to: verse, chorus, intro, and so on. 

    **Text**: 
    Print out the fragments of the song in which this text will be displayed, if this frame will be displayed without text, then simply print "-"

    **Prompt for the image generating model**: (maximum number of words - 77)
    Specify the style (Realistic), the mood, in which colors the image should be executed, the time or historical period in which the events take place, then describe what should be depicted in the picture, what the characters are wearing.
    The lyrics along with the timestamps are: '''
    )

# Загрузка модели Sambanova
client = OpenAI(
    api_key="c28b215f-2bf4-4f13-a5ac-bf9d0389d24f",
    base_url="https://api.sambanova.ai/v1",
)

# Функции генерации (оставлены без изменений)
def generate_image_for_prompt(prompt, images_folder):
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
            image_url = response_data["image_url"]
            new_image_path = os.path.join(images_folder, f"{os.path.basename(image_url)}")
            shutil.copy2(image_url, new_image_path)
            return new_image_path
        else:
            return f"Error: {response_data.get('error', 'Unknown error')}"
    except Exception as e:
        return f"Error: {str(e)}"

def create_video(image_path, duration, project_folder):
    """Create video from image."""
    payload = {
        'image_path': image_path,
        'duration': duration
    }
    response = requests.post("http://127.0.0.1:6000/process_images", json=payload)
    if response.status_code == 200:
        video_url = response.json().get('video_url')
        new_video_path = os.path.join(project_folder, f"video_{os.path.basename(video_url)}")
        shutil.copy2(video_url, new_video_path)
        return new_video_path
    else:
        return None

def audio_to_time_text(audio_path, text_path):
    """Align audio to text timestamps."""
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

def button_create_videos(prompts_data, selected_images, font, font_path, font_color_1, font_color_2, audio_type, language, project_folder):
    """Create video with subtitles and audio."""
    print("НАААЧААЛИ!!!!")
    status = st.empty()

    audio_path = os.path.join(project_folder, "audio/mp3_file.mp3")    
    vocal_path = os.path.join(project_folder, "audio/vocal.mp3")
    no_vocal_path = os.path.join(project_folder, "audio/no_vocal.mp3")
    lyrics_file = os.path.join(project_folder, "lyrics.txt")

    font_size = 60

    with status:
        with st.spinner("Создание субтитров 1/4"):
            subtitels_path = os.path.join(project_folder, "subtitles.ass")
            subtitels = Subtitles(audio_path, lyrics_file, font, font_path, font_color_1, font_color_2, font_size, subtitels_path)
            if language != subtitels.text_language:
                subtitels.translate(language)
            subtitels.create()

    with status:
        with st.spinner("Создания видео 2/4"):
            video = Video(prompts_data, selected_images, lyrics_file, font, font_path, font_color_1, font_color_2, audio_type, language, project_folder)
            video.create(new_videos=True)

    with status:
        with st.spinner("Добавление субтитров 3/4"):
            print(subtitels_path)
            video.add_subtitels(subtitels_path)

    with status:
        with st.spinner("Добавление аудио файла к видео 4/4"):
            if audio_type == 'Плюс-фонограмма':
                video.add_audio(audio_path)
            elif audio_type == 'Минус-фонограмма':
                video.add_audio(no_vocal_path)
            final_video_path = os.path.join(project_folder, "video/final_video.mp4")
            shutil.move(video.video_with_audio_path, final_video_path)

    # Сохраняем путь к видео в состояние
    st.session_state["final_video"] = final_video_path
    save_state(st.session_state, project_folder=st.session_state["project_folder"])
    return final_video_path

# Логика страниц
if st.session_state["project_folder"] is None:
    st.warning("Пожалуйста, выберите проект или создайте новый в боковой панели.")
else:
    if st.session_state["current_page"] == "main":

        video_type = st.selectbox(
            "Выбирите вид Lyrics-виде",
            ("с изоражениями", "без изображений"),
        )

        if video_type == "без изображений":
            st.session_state["current_page"] = "only-text"
            st.rerun()
        
        st.title("Создание слайд-шоу для песни")
        
        mp3_file = st.file_uploader("Upload an MP3 file", type=["mp3"])
        if mp3_file is not None:
            audio_path = os.path.join(st.session_state["project_folder"], "audio/mp3_file.mp3")
            with open(audio_path, "wb") as f:
                f.write(mp3_file.read())
                
        txt_file = st.file_uploader("Upload a TXT file with lyrics", type=["txt"])
        if txt_file is not None:
            text = txt_file.read().decode("utf-8")
            lyrics_file = os.path.join(st.session_state["project_folder"], "lyrics.txt") 
            with open(lyrics_file, "w", encoding="utf-8") as f:
                f.write(text)

        if txt_file is not None and len(st.session_state.messages) == 0:
            lyrics = create_lyrics(text, audio_path, lyrics_file)
            st.session_state.messages.append({"role": "system", "content": st.session_state.role_message})
            st.session_state.messages.append({"role": "user", "content": lyrics})

        for message in st.session_state.messages:
            if message["role"] != "system":
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

        if txt_file:
            if user_input := st.chat_input("Введите ваш вопрос или текст...") or len(st.session_state.messages) == 2:
                if len(st.session_state.messages) != 2:
                    st.session_state.messages.append({"role": "user", "content": user_input})
                    with st.chat_message("user"):
                        st.markdown(user_input)
                
                with st.chat_message("assistant"):
                    response_container = st.empty()
                    messages = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
                    with st.spinner("Qwen2.5-72B is generating a response..."):
                        response = ""
                        stream = client.chat.completions.create(
                            model=st.session_state["openai_model"],
                            messages=messages,
                            stream=True,
                            temperature=0.8,
                            top_p=0.8,
                            max_tokens=8000,
                        )
                        for chunk in stream:
                            if chunk.choices:
                                token = chunk.choices[0].delta.content
                                response += token
                                response_container.write(response)
                        st.session_state.messages.append({"role": "assistant", "content": response})

        if st.button("Перейти к загрузке MP3-файла"):
            st.session_state["current_page"] = "upload"
            st.rerun()

    elif st.session_state["current_page"] == "upload":
        st.title("MP3 & Lyrics Image Generator")

        images_folder = os.path.join(st.session_state["project_folder"], "images")
        os.makedirs(images_folder, exist_ok=True)
        
        model_response = st.session_state.messages[-1]["content"]

        col1, col2 = st.columns([1, 1])
        with col1:
            selected_color_1 = st.color_picker("Выберите первичный цвет субтитров:", "#ad6109")[1:]
            selected_color_1 = selected_color_1[4:] + selected_color_1[2:4] + selected_color_1[:2]
        with col2:
            selected_color_2 = st.color_picker("Выберите вторичный цвет субтитров:", "#C99457")[1:]
            selected_color_2 = selected_color_2[4:] + selected_color_2[2:4] + selected_color_2[:2]

        fonts_path = {
            'Balkara Free Condensed - npoekmu.me': 'font/ofont.ru_BalkaraCondensed.ttf',
            'Manrope': 'font/ofont.ru_Manrope.ttf',
            'Kaph': 'font/ofont.ru_Kaph.ttf',
            'BOWLER': 'font/ofont.ru_Bowler.ttf',
            'Handelson Five_CYR': 'font/18035.otf',
            'Garamond': 'font/Garamond-Garamond-Regular.ttf',
            'Huiwen ZhengKai Font (китайский шрифт)': 'font/Huiwen-ZhengKai-Font.ttf',
        }

        languages = {
            'Русский': 'ru',
            'Английский': 'en',
            'Китайский': 'zh',
        }
        
        phonograms = ['Плюс-фонограмма', 'Минус-фонограмма']

        language = st.selectbox('Выберите язык субтитров', list(languages.keys()))
        language = languages[language]

        if language == 'zh':
            font = st.selectbox("Выберите шрифт:", list({'Huiwen ZhengKai Font (китайский шрифт)': 'font/Huiwen-ZhengKai-Font.ttf'}.keys()))
        else:
            font = st.selectbox("Выберите шрифт:", list(fonts_path.keys()))
        font_path = fonts_path.get(font)

        audio_type = st.selectbox("Выберите вид фонограммы:", phonograms)

        if font_path:
            sample_text = "Съешь ещё этих мягких французских булок, да выпей чаю"
            img = create_text_image(sample_text, font_path)
            st.image(img, use_container_width=True)
        else:
            st.error("Шрифт не найден!")

        if st.button("Generate Images"):
            prompts_data = process_song(model_response)
            new_prompts = [p for p in prompts_data if p not in st.session_state.prompts_data]
            st.session_state.prompts_data.extend(new_prompts)

        # Остальной код для эффектов и генерации изображений остается без изменений...
        effects = {
            'Без эффекта': None,
            'Звезды': 'effects/vecteezy_million-gold-star-and-dark-triangel-flying-and-faded-on-the_15452899.mov',
            'Молнии': 'effects/vecteezy_the-thunderbolt-effect-in-black-background_27118256.mov',
            'Старая камера': 'effects/vecteezy_flickering-super-8-film-projector-perfect-for-transparent_9902616.mov',
            'Снег': 'effects/vecteezy_snowfall-overlay-on-green-screen-background-realistic_16108103.mov',
            'Листопад': 'effects/ezyZip.mov',
            'Искры': 'effects/vecteezy_fire-flame-particle-animation-green-screen-video_24397594.mov',
            'Кот': 'effects/Green-Screen-Happy-Happy-Happy-Cat-Meme.mov',
            'Облака': 'effects/vecteezy_4k-alpha-channel-render-fly-through-the-realistic-procedural_720p.mov',
            'Дождевые облака': 'effects/vecteezy_free-download-rain-clouds-stock-video-clip_6529321.mov',
            'Солнечные лучи': 'effects/vecteezy_light-leak-of-blue-lens-flare-in-the-background-light_38190348.mov',
            'Зеленый': 'effects/vecteezy_light-leaks-light-green.mov',
            'Красный': 'effects/vecteezy_light-leaks-light-red.mov',
            'Белый': 'effects/vecteezy_light-leaks-light-white.mov',
            'Фиолетовый': 'effects/vecteezy_light-leaks-purple.mov',
            'Летучие мыши': 'effects/vecteezy_the-glowing-midnight-bats-in-black-screen_52182187.mov',
            'Желтые летающие частицы': 'effects/vecteezy_gradient-background-from-brown-to-black-with-transparent_1794889.mov',
        }

        effects_next = {
            'Без эффекта': 0,
            'Короткий': 2,
            'Длинный': 1,
        }

        short_effect = {
            "Красная капля": 'effect_next/1.mov',
            "Черная капля": 'effect_next/2.mov',
            "Фиолетовая капля": 'effect_next/3.mov',
            "Белая капля": 'effect_next/4.mov',
            "Синяя волна": 'effect_next/5.mov',
            "Фиолетовая волна": 'effect_next/6.mov',
            "Розовая волна": 'effect_next/7.mov',
            "Белая заморозка": 'effect_next/8.mov',
            "Желтая заморозка": 'effect_next/9.mov',
            "Белый дым": 'effect_next/10.mov',
            "Черный дым": 'effect_next/11.mov',
        }

        long_effect = {
            "Черно-красный круг": 'effect_next/vecteezy_2-color-liquid-black-and-red-transition-green-screen_49115368.mov',
            "Красно-белый жидкий переход": 'effect_next/vecteezy_red-liquid-transition-green-screen_49115367.mov',
            "Градиентные чернила": 'effect_next/vecteezy_transition-ink-gradient-color-green-screen-free_48868911.mov',
            "Сердечки": 'effect_next/vecteezy_transitions-love-green-screen_48868982.mov',
            "Черный дым": 'effect_next/vecteezy_smoke-transition-green-screen-black_48021329.mov',
            "Белый дым": 'effect_next/vecteezy_smoke-transition-green-screen-white_48021329.mov',
        }

        number_images = 1
        images_folder = os.path.join(st.session_state["project_folder"], "images")
        
        if st.session_state.prompts_data:
            st.write("# Generated Images")
            previous_part = ''

            for i, entry in enumerate(st.session_state.prompts_data):
                lyrics = entry["lyrics"]
                part = entry["part"]
                shot = entry["shot"]
                prompt = entry["prompt"]
                image_urls = entry.get("image_url", [])

                if previous_part != part:
                    st.write("***")
                    st.write(f"## {part}")
                    previous_part = part

                col1, col2 = st.columns([5, 1])
                with col1:
                    st.write(f"**Part:** {part}")
                    st.write(f"**Lyrics:** {lyrics}")
                    user_shot = st.text_area('**Shot**', value=f"{shot}", height=68, key=f'user_shot_{i}')
                    user_prompt = st.text_area('**Prompt**', value=f"{prompt}", height=150, key=f'user_input_{i}')
                    if image_urls:
                        img = image_select("", image_urls)
                        st.session_state[f"selected_image_{i}"] = img
                    else:
                        for _ in range(number_images):
                            with st.spinner(f"Generating image"):
                                image_url = generate_image_for_prompt(prompt, images_folder)
                                entry["image_url"].append(image_url)
                        img = image_select("Выберите изображение", entry["image_url"])
                        st.session_state[f"selected_image_{i}"] = img
                    selected_image = st.session_state.get(f"selected_image_{i}", None)
                    if selected_image:
                        st.success("Selected image:")
                        st.image(selected_image)
                with col2:
                    selected_effect = st.selectbox("Выберите эффект:", list(effects.keys()), key=f"effect_{i}")
                    entry['effect'] = effects[selected_effect]
                    selected_effect_next = st.selectbox("Выберите эффект переключения на следующие видео:", list(effects_next.keys()), key=f"effect_next_{i}")
                    if selected_effect_next == "Длинный":
                        effect_type = st.selectbox("Выберите эффект переключения на следующие видео:", list(long_effect.keys()), key=f"effect_next_long{i}")
                        entry['effects_next'] = long_effect[effect_type]
                    elif selected_effect_next == "Короткий":
                        effect_type = st.selectbox("Выберите эффект переключения на следующие видео:", list(short_effect.keys()), key=f"effect_next_short{i}")
                        entry['effects_next'] = short_effect[effect_type]
                    else:
                        entry['effects_next'] = None
                    if st.button("Перегенерировать", key=f'button_{i}'):
                        if user_prompt != prompt:
                            entry["prompt"] = user_prompt
                            prompt = user_prompt
                        for _ in range(number_images):
                            with st.spinner(f"Generating image"):
                                image_url = generate_image_for_prompt(prompt, images_folder)
                                if image_url.startswith("static/"):
                                    entry["image_url"].append(image_url)
                                else:
                                    st.error(image_url)
                        st.session_state[f"selected_image_{i}"] = None
                        st.rerun()
                if user_shot != shot:
                    entry["shot"] = user_shot
                st.write('---')

        if st.button("Generate Video with Selected Images"):
            selected_images = [st.session_state.get(f"selected_image_{idx}") for idx in range(len(st.session_state.prompts_data))]
            if None in selected_images:
                st.error("Please select an image for all lyrics!")
            else:
                video_url = button_create_videos(st.session_state.prompts_data, selected_images, font, font_path, selected_color_1, selected_color_2, audio_type, language, st.session_state["project_folder"])
                if video_url and not video_url.startswith("Error"):
                    st.session_state["final_video"] = video_url
                else:
                    st.error(f"Failed to create video: {video_url}")

        if st.session_state.get("final_video") and os.path.exists(st.session_state["final_video"]):
            st.video(st.session_state["final_video"])

        if st.button("Вернуться на главную"):
            st.session_state["current_page"] = "main"
            st.rerun()


    elif st.session_state["current_page"] == "only-text":
        video_type = st.selectbox(
            "Выбирите вид Lyrics-виде",
            ("с изоражениями", "без изображений"),
        )

        if video_type == "c изображений":
            st.session_state["current_page"] = "main"
            st.rerun()
        
        st.title("Создание слайд-шоу для песни")
        
        mp3_file = st.file_uploader("Upload an MP3 file", type=["mp3"])
        if mp3_file is not None:
            audio_path = os.path.join(st.session_state["project_folder"], "audio/mp3_file.mp3")
            with open(audio_path, "wb") as f:
                f.write(mp3_file.read())
                
        txt_file = st.file_uploader("Upload a TXT file with lyrics", type=["txt"])
        if txt_file is not None:
            text = txt_file.read().decode("utf-8")
            lyrics_file = os.path.join(st.session_state["project_folder"], "lyrics.txt") 

            pattern = re.compile(r"(\[.*?\])\s*(.*?)(?=\n\[|\Z)", re.DOTALL)
            text = re.sub(r'\(.*?\)', '', text)
            
            parsed_lyrics = [
                {"text": line.strip(), "section": match[0].strip("[]")}
                for match in pattern.findall(text)
                for line in match[1].strip().split("\n") if line.strip()
            ]
            
            lyrics = ""
            
            # Вывод результата
            for i, item in enumerate(parsed_lyrics):
                if i + 1 != len(parsed_lyrics):
                    lyrics += item["text"] + "\n"
                else:
                    lyrics += item["text"]
        
            with open(lyrics_file, "w", encoding="utf-8") as f:
                f.write(lyrics)

        fonts_path = {
            'Balkara Free Condensed - npoekmu.me': 'font/ofont.ru_BalkaraCondensed.ttf',
            'Manrope': 'font/ofont.ru_Manrope.ttf',
            'Kaph': 'font/ofont.ru_Kaph.ttf',
            'BOWLER': 'font/ofont.ru_Bowler.ttf',
            'Handelson Five_CYR': 'font/18035.otf',
            'Garamond': 'font/Garamond-Garamond-Regular.ttf',
            'Huiwen ZhengKai Font (китайский шрифт)': 'font/Huiwen-ZhengKai-Font.ttf',
        }

        languages = {
            'Русский': 'ru',
            'Английский': 'en',
            'Китайский': 'zh',
        }
        
        phonograms = ['Плюс-фонограмма', 'Минус-фонограмма']

        language = st.selectbox('Выберите язык субтитров', list(languages.keys()))
        language = languages[language]

        if language == 'zh':
            font = st.selectbox("Выберите шрифт:", list({'Huiwen ZhengKai Font (китайский шрифт)': 'font/Huiwen-ZhengKai-Font.ttf'}.keys()))
        else:
            font = st.selectbox("Выберите шрифт:", list(fonts_path.keys()))
        font_path = fonts_path.get(font)

        audio_type = st.selectbox("Выберите вид фонограммы:", phonograms)

        if font_path:
            sample_text = "Съешь ещё этих мягких французских булок, да выпей чаю"
            img = create_text_image(sample_text, font_path)
            st.image(img, use_container_width=True)
        else:
            st.error("Шрифт не найден!")

        font_color_1 = "#FFFFFF"
        font_color_2 = "#FFFFFF" 
        font_size = 48

        subtitels_path = os.path.join(st.session_state["project_folder"], "subtitles.srt")
                
        if st.button("Создать файл с субтитрами") and mp3_file and txt_file:
            subtitels = Subtitles(audio_path, lyrics_file, font, font_path, font_color_1, font_color_2, font_size, subtitels_path)
            if language != subtitels.text_language:
                subtitels.translate(language)
                
            subtitels.create_srt()

        if os.path.exists(subtitels_path):
            # Чтение содержимого файла
            with open(subtitels_path, "r", encoding="utf-8") as f:
                srt_content = f.read()
            
            # Отображение содержимого файла .srt в текстовом поле для редактирования
            edited_srt = st.text_area("Редактировать субтитры (.srt)", srt_content, height=300)
            
            # Кнопка для сохранения изменений
            if st.button("Сохранить изменения"):
                with open(subtitels_path, "w", encoding="utf-8") as f:
                    f.write(edited_srt)

        if st.button("Создать видео"):
            manim_script_path = "/yoga/lyrics_speaker.py"  # Укажите путь к вашему Manim-скрипту
            video_output_path = os.path.join(st.session_state["project_folder"], "video.mp4")
            print(subtitels_path)
            # Запускаем Manim для создания видео
            try:
                subprocess.run([
                    "manim", manim_script_path, subtitels_path,
                    # "-o", video_output_path,
                    # "--format=mp4"
                ], check=True)
        
                # Проверяем, создано ли видео
                if os.path.exists(video_output_path):
                    st.success("Видео успешно создано!")
                    st.video(video_output_path)
                else:
                    st.error("Не удалось создать видео.")
            except subprocess.CalledProcessError:
                st.error("Ошибка при запуске Manim. Убедитесь, что Manim установлен и путь к скрипту верный.")
       

# Кнопки в sidebar
if st.sidebar.button("Сохранить и выйти"):
    save_state(st.session_state, project_folder=st.session_state["project_folder"])
    st.stop()

if st.sidebar.button("Очистить состояние"):
    if st.session_state["project_folder"] and os.path.exists(st.session_state["project_folder"]):
        shutil.rmtree(st.session_state["project_folder"])
    st.session_state.clear()
    st.session_state["project_folder"] = None
    st.session_state["openai_model"] = "Qwen2.5-72B-Instruct"
    st.session_state.messages = []
    st.session_state["current_page"] = "main"
    st.session_state.prompts_data = []
    st.session_state["final_video"] = None
    st.rerun()
    