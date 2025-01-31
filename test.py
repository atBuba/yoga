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


def process_song(mp3_file, txt_file):
    """Process song text file and generate structured prompts."""

    with open(txt_file, "r") as file:  # Можно использовать "a" для добавления текста
        text = file.read()

    with open('example.txt', 'w') as f:
        f.write(text)
    
    # Parse the response into a structured format
    pattern = r"\*\*Кадр\*\*:\s+(.+?)\n\n\*\*Часть песни\*\*:\s+(.+?)\n\n\*\*Текст\*\*:\s+(.+?)\n\n\*\*Промпт для модели генерирующей изображения\*\*:\s+(.+?)(?=\n\n|\Z)"

    # pattern = r"\#\#\#\# Строчки песни:\s+(.+?)\n\n\*\*Промт для модели генерирующей изображения\*\*:\s+(.+?)(?=\n\n|\Z)"
    matches = re.findall(pattern, text, re.S)

    # image_lyrics = []
    
    prompts_translated = []
    for match in matches:
        shot = match[0].strip()
        part = match[1].strip()
        lyrics = match[2].strip()
        prompt = match[3].strip()
        translated_prompt = translate_text(prompt)
        print(translated_prompt)
        # image_lyrics.appned(lyrics)
        prompts_translated.append({"lyrics": lyrics, 'part': part, 'shot': shot, "prompt": translated_prompt, "image_url": [], 'effect': None, 'effects_next': None})

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


def create_videos(prompts_data, selected_images, txt_file, font, selected_color_1, selected_color_2):
    print("НАААЧАААЛИ!!!!")
    status = st.empty()

    images = []

    time = []
    for i in selected_images:
        images.append(i)

    effects_next = [] 
    for i in prompts_data:
        effects_next.append(i['effects_next'])

    for i in range(len(prompts_data)):
        t = prompts_data[i]['shot'].split('-') 
        if i == 0:
            start = t[0].split(':')
            end = t[1].split(':')
            
            
            start_second = float(start[0]) * 3600 + float(start[1]) * 60 + float(start[2])
            end_second = float(end[0]) * 3600 + float(end[1]) * 60 + float(end[2])
            time.append([start_second, end_second])
        else:
            # print(end)
            end = t[1].split(':')

            end_second = float(end[0]) * 3600 + float(end[1]) * 60 + float(end[2])

            time.append([time[i-1][1], end_second])
            
        
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
        with status:    
            with st.spinner("Создание субтитров 1/5"): 
                ttml_words = adiou_to_time_text(audio_path, lyrics_file)
                ttml_lines = parse(txt_files=lyrics_file)
                ttml_two_lines = parse(txt_files=lyrics_file, two_lines=True)
    else: 
        ttml_words = parse(txt_files=lyrics_file, word=True)
        ttml_two_lines = parse(txt_files=lyrics_file, two_lines=True)
        ttml_lines = parse(txt_files=lyrics_file)
    
    generate_ass(ttml_words, ttml_lines, "static/subtitles.ass", font, selected_color_1, selected_color_2)
    
    duration = 0
    j = -1
    videos = []
    # prompts_data = prompts_data[:6:]
    # for image_path, line in zip(images, prompts_data):   
    #     j += len(line['lyrics'].split())
    #     effect = line['effect']
    #     print(ttml_words[j])
    #     video_url = create_video(image_path=image_path, duration=ttml_words[j]['end'] - duration)
    #     if effect:
    #         add_effect(video_url, effect)
    #     videos.append(VideoFileClip(video_url))
    #     duration = ttml_words[j]['end']

    # time = time[:-1:]
    # for i in time:
    #     print(i)
    with status:
        with st.spinner("Анимация изображений 2/5"):
            for image_path, t , line in zip(images, time, prompts_data):   
                effect = line['effect']
                video_url = create_video(image_path=image_path, duration=t[1] - t[0])
                if effect:
                    add_effect(video_url, effect)
                videos.append(video_url)
    
    # create_slideshow(videos, ttml_words, ttml_lines, font=font, font_color=font_fill_color, output_path = output_video_avi, addSubtitles=subtitles, font_size=font_size)
    print('create_video')

    overlay_videos = [
        'videos/vecteezy_2-color-liquid-black-and-red-transition-green-screen_49115368.mp4',
        'videos/vecteezy_red-liquid-transition-green-screen_49115367.mp4',
        'videos/vecteezy_transition-ink-gradient-color-green-screen-free_48868911.mp4',
        'videos/vecteezy_transitions-love-green-screen_48868982.mp4',
        
    ]

    short_overlay_videos = [
        'videos/1.mp4',
        # 'videos/2.mp4',
        'videos/3.mp4',
        'videos/4.mp4',  
        'videos/5.mp4',  
        'videos/6.mp4',  
        'videos/7.mp4',
        'videos/8.mp4',  
        'videos/9.mp4',  
    ]
    with status:
        with st.spinner("Рендеринг видео 3/5"):
            concatenate_videos(videos, output_video_avi, overlay_videos, short_overlay_videos, effects_next)
    with status:
        with st.spinner("Добавление субтитров 4/5"):
            create_subtitles_2(output_video_avi, "static/subtitles.ass", output_video_mp4)
    with status:
        with st.spinner("Добавление аудио файла к видео 5/5"):
            if check_file_exists(ttml_file_lines) and check_file_exists(audio_path):
                add_audio_to_video('video/temp_video.mp4', audio_path, output_video_mp4)


    if output_video_mp4:
        return output_video_mp4
    else:
        return 'error'

# Загрузка модели Sambanova
client = OpenAI(
    api_key="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",
    base_url="https://huggingface.co/api/inference-proxy/together",
)

# Инициализация состояния
if "openai_model" not in st.session_state:
    st.session_state["openai_model"] = "mistralai/Mistral-Small-24B-Instruct-2501"

if "messages" not in st.session_state:
    st.session_state.messages = []

if "current_page" not in st.session_state:
    st.session_state["current_page"] = "main"  # Устанавливаем начальную страницу

# Устанавливаем роль модели (скрыто от пользователя)
if "role_message" not in st.session_state:
    st.session_state.role_message = (
        '''Ты должен создать слайд-шоу-клип для песни, ты получишь текст песни вместе с временными метками и должен будешь разделить песню по кадрам и написать промпт для генерации изображения на этом кадре, каждый кадр не должен идти меньше 5 и дольше 7 секунд, ты можешь объеденять строчки, чтобы достич такой длиный. Кадры, которые будут показываться в момент, когда нет текста, должны просто передавать атмосферу клипа, кадры должны быть непрерывны, то есть начало текущего клипа — это конец предыдущего. Напиши промпт для модели, которая будет генерировать изображения для этих кадров, изображения должны быть связанны друг с другом, весь клип должен отражать смысл песни, передавать ее настроение. Распиши подробно, во что одеты люди и как они стоят, в каких тонах должно быть изображение, какого настроение это изображения, в каком стиле. Главные персонажи должны на всех изображениях выглядеть одинаково, стиль всего слайд-шоу должен быть един, цветовая палитра всех картинок должна быть одинакова, укажи, в какое время или исторический период происходят действия, у всех картинок этот период должен быть одинаковый. Кадры, которые будут показываться вместе с текстом, должны передавать то, о чем говорится в этих строчках, эти кадры должны показываться строго вместе с текстом.
Ответь в следующем формате:

**Кадр**: (без номера)
временная метка когда будет показываться этот кадр в формате XX:XX:XX.XX - XX:XX:XX.XX(кадр не должен идти меньше 5 и дольше 7 секунд)

**Часть песни**: 
Выведи, к какой части песни относится этот кадр: куплет, припев, вступление и так далее. 

**Текст**: 
Выведи стрчоки песнис с которыми будет показываться этот текст, если этот кадр будет показываться без текста, то выведи просто "-"

**Промпт для модели генерирующей изображения**:(максимальное количество слов 77)
Укажи стиль(реалистичный, кинематографичный), настроение, в каких цветах должно быть выполнено изображение, время или исторический промежуток, в который происходят события, затем опиши, что должно быть изображено на картинке, во что одеты персонажи.
используй все строчки песни, даже если они повторяются.
текст песни вместе с временными метками: '''
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
                    max_tokens=8000,
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

    col1, col2 = st.columns([1, 1])
    with col1:
        selected_color_1 = st.color_picker("Выберите первичный цвет субтитров:", "#ad6109")[1::]
        selected_color_1 = selected_color_1[4::] + selected_color_1[2:4:] + selected_color_1[:2:]
    with col2:
        selected_color_2 = st.color_picker("Выберите вторичный цвет субтитров:", "#C99457")[1::]
        selected_color_2 = selected_color_2[4::] + selected_color_2[2:4:] + selected_color_2[:2:]
        
    
    # Список шрифтов и их путей
    fonts = ['Balkara Free Condensed - npoekmu.me', 'Manrope', 'Kaph', 'BOWLER']
    fonts_path = {
        'Balkara Free Condensed - npoekmu.me': 'font/ofont.ru_BalkaraCondensed.ttf',
        'Manrope': 'font/ofont.ru_Manrope.ttf',
        'Kaph': 'font/ofont.ru_Kaph.ttf',
        'BOWLER': 'font/ofont.ru_Bowler.ttf',
    }
    
    # Выбор шрифта
    font = st.selectbox("Выберите шрифт:", fonts)
    
    # Текст для отображения
    sample_text = "съешь ещё этих мягких французских булок, да выпей чаю"
    
    # Функция для создания изображения с текстом
    def create_text_image(text, font_path, font_size=24):
        try:
            # Загружаем шрифт
            font = ImageFont.truetype(font_path, font_size)
        except Exception as e:
            st.error(f"Ошибка загрузки шрифта: {e}")
            return None
        
        # Определяем размер текста
        image_width = 800
        image_height = 100
        
        # Создаем изображение
        img = Image.new('RGB', (image_width, image_height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        # Рисуем текст
        draw.text((10, 10), text, font=font, fill=(0, 0, 0))
        return img
    
    # Получаем путь к выбранному шрифту
    font_path = fonts_path.get(font)
    
    if font_path:
        # Создаем изображение с текстом
        img = create_text_image(sample_text, font_path)
        
        if img:
            # Отображаем изображение в Streamlit
            st.image(img, use_container_width=True)
    else:
        st.error("Шрифт не найден!")

            
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
                new_prompts.append(prompt_entry)
                # st.session_state.prompts_data.append(prompt_entry)

        # Add new prompts to session state
        st.session_state.prompts_data.extend(new_prompts)

    effects = {
        'Без эффекта' : None,
        'Звезды' : 'video/vecteezy_million-gold-star-and-dark-triangel-flying-and-faded-on-the_15452899.mp4', 
        'Снег' : 'video/vecteezy_snowfall-overlay-on-green-screen-background-realistic_16108103.mp4', 
        'Листопад' : 'video/ezyZip.mp4', 
        'Искры' : 'video/vecteezy_fire-flame-particle-animation-green-screen-video_24397594.mp4',
        'Кот' : 'video/Green-Screen-Happy-Happy-Happy-Cat-Meme.mp4',
        
        
    }

    effects_next = {
        'Без эффекта' : 0,
        'Короткий' : 2, 
        'Длинный' : 1,         
    }

    number_images = 1
    
    # Display all generated images
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
                st.write(f"**Time:** {shot}")
                st.write(f"**Part:** {part}")
                st.write(f"**Lyrics:** {lyrics}")
                # st.write(f"**Prompt (Translated):** {prompt}")

                user_prompt = st.text_area(
                    '**Prompt**', 
                    value=f"{prompt}", 
                    height=150, 
                    # value=st.session_state.user_data,
                    key=f'user_input_{i}',
                    # label_visibility =False,z
                )
                
                if image_urls != []:
                    img = image_select("", image_urls)
                    st.session_state[f"selected_image_{i}"] = img 
                else:
                    for _ in range(number_images): # количество изображений для одного кадра 
                        with st.spinner(f"Generating image"):
                            image_url = generate_image_for_prompt(prompt)
                            if image_url.startswith("static/"):
                                entry["image_url"].append(image_url)
                            else:
                                st.error(image_url)
                    img = image_select("Выберите изобаржение", entry["image_url"])
                    st.session_state[f"selected_image_{i}"] = img 

                selected_image = st.session_state.get(f"selected_image_{i}", None)
                if selected_image:
                    st.success("Selected image:")
                    st.image(selected_image)
                                
            with col2:
                selected_effect = st.selectbox(
                    "Выберите эффект:",
                    list(effects.keys()),
                    key=f"effect_{i}",
                )
    
                # Обновление выбранного эффекта в prompts_data
                entry['effect'] = effects[selected_effect]
                # print(entry)
                # Отображение выбранного эффекта
                # st.write(f"Выбранный эффект: {selected_effect}")
                selected_effect = st.selectbox(
                    "Выберите эффект переключения на следующие видео:",
                    list(effects_next.keys()),
                    key=f"effect_next_{i}",
                )
    
                # Обновление выбранного эффекта в prompts_data
                entry['effects_next'] = effects_next[selected_effect]

                if st.button("Перегенерировать", key=f'button_{i}'):
                    
                    entry["image_url"] = [] 
                    
                    if user_prompt != prompt: 
                        entry["prompt"] = user_prompt
                        prompt = user_prompt
                        
                    for _ in range(number_images): # количество изображений для одного кадра 
                        with st.spinner(f"Generating image"):
                            image_url = generate_image_for_prompt(prompt)
                            if image_url.startswith("static/"):
                                entry["image_url"].append(image_url)
                            else:
                                st.error(image_url)
                                
                    st.session_state[f"selected_image_{i}"] = None
                    st.rerun()
                    
            st.write('---')
        
    # Generate Video Button
    if st.button("Generate Video with Selected Images"):
        selected_images = [
            st.session_state.get(f"selected_image_{idx}")
            for idx in range(len(st.session_state.prompts_data))
        ]
    
        # Проверяем, что все изображения выбраны
        if None in selected_images:
            st.error("Please select an image for all lyrics!")
        else:
            video_url = create_videos(st.session_state.prompts_data, selected_images, txt_file, font, selected_color_1, selected_color_2)
            if video_url and not video_url.startswith("Error"):
                st.video(video_url)
            else:
                st.error(f"Failed to create video: {video_url}")

    # Button to return to main page
    if st.button("Вернуться на главную"):
        st.session_state["current_page"] = "main"
        st.rerun()