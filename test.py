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


def create_videos(prompts_data, selected_images, txt_file, font, font_path, selected_color_1, selected_color_2, audio_type, language):
    print("НАААЧАААЛИ!!!!")
    status = st.empty()

    # Файлы 
    audio_path = 'static/mp3_file.mp3' # файл песни 
    vocal_path = 'static/vocal.mp3' # файл вокала песни
    no_vocal_path = 'static/no_vocal.mp3' # файл инструментала песни 

    output_video_avi = 'video/final_video.mp4' # клип без аудио и субтитров 
    output_video_mp4 = 'video/final_video_with_audio_1.mp4' # финальный клип с аудио и субтитрами 

    lyrics_file = 'static/lyrics.txt' # файл с текстом песни 

    font_size= 60  # размер шрифта 
    
    images = selected_images # список выбранных изображений 
    videos = [] # список сгенерированных видео по изобржаниям
    time = [] # список временных меток кадров 
    effects_next = [] # список выбранных эффектов поверх видео 
    
    # Перевод времени из формата XX:XX:XX в секунды 
    for i in range(len(prompts_data)):
        effects_next.append(prompts_data[i]['effects_next'])
        t = prompts_data[i]['shot'].split('-') 
        if i == 0:
            start = t[0].split(':')
            end = t[1].split(':')
            start_second = float(start[0]) * 3600 + float(start[1]) * 60 + float(start[2])
            end_second = float(end[0]) * 3600 + float(end[1]) * 60 + float(end[2])
            time.append([start_second, end_second])
        else:
            end = t[1].split(':')
            end_second = float(end[0]) * 3600 + float(end[1]) * 60 + float(end[2])
            time.append([time[i-1][1], end_second])

    # Созадние файла с субтитрами 
    with status:    
        with st.spinner("Создание субтитров 1/5"): 
            ttml_words = adiou_to_time_text(audio_path, lyrics_file)
            ttml_lines = parse(txt_files=lyrics_file)
            ttml_two_lines = parse(txt_files=lyrics_file, two_lines=True)
    
            with open(lyrics_file, "r", encoding="utf-8") as f:
                text = f.read()
            text_language = detect_language(text[:999:]) 
            print(text_language)
            if language == text_language:
                generate_ass(ttml_words, ttml_lines, "static/subtitles.ass", font, selected_color_1, selected_color_2)
            else:
                translate_lyrics = translate_text(text, language)
                generate_ass_eng(ttml_words, ttml_lines, translate_lyrics,"static/subtitles.ass", font, font_path, selected_color_1, selected_color_2, font_size) 
                
    # # Созадние видео из изображений 
    # with status:
    #     with st.spinner("Анимация изображений 2/5"):
    #         for image_path, t , line in zip(images, time, prompts_data):   
    #             effect = line['effect']
    #             print(t[1] - t[0])
    #             video_url = create_video(image_path=image_path, duration=t[1] - t[0])
    #             if effect:
    #                 add_effect(video_url, effect)
    #             videos.append(video_url)
                
    # # Объединение всех видео в одно с применением переходов
    # with status:
    #     with st.spinner("Рендеринг видео 3/5"):
    #         concatenate_videos(videos, output_video_avi, effects_next)
            
    # Добавление субтитров на видео 
    with status:
        with st.spinner("Добавление субтитров 4/5"):
            create_subtitles_2(output_video_avi, "static/subtitles.ass", output_video_mp4)
            
    # Добавления аудио к видео 
    with status:
        with st.spinner("Добавление аудио файла к видео 5/5"):
            if audio_type == 'Плюс-фонограмма':
                add_audio_to_video('video/temp_video.mp4', audio_path, output_video_mp4)
            elif audio_type == 'Минус-фонограмма':
                add_audio_to_video('video/temp_video.mp4', no_vocal_path, output_video_mp4)


    return output_video_mp4
    

# Загрузка модели Sambanova
client = OpenAI(
    api_key="c28b215f-2bf4-4f13-a5ac-bf9d0389d24f",
    base_url="https://api.sambanova.ai/v1",
)

# Инициализация состояний
if "openai_model" not in st.session_state:
    st.session_state["openai_model"] = "Qwen2.5-72B-Instruct"

if "messages" not in st.session_state:
    st.session_state.messages = []

if "current_page" not in st.session_state:
    st.session_state["current_page"] = "main"  # Устанавливаем начальную страницу

# Устанавливаем роль модели (скрыто от пользователя)
if "role_message" not in st.session_state:
    st.session_state.role_message = (
        ''' 
    Use the entire text carefully. You need to create a slideshow clip for the song, you will receive the lyrics along with timestamps, write a hint to create an image in this frame. The frames that will be shown at the moment when there is no text should simply convey the atmosphere of the clip. Write a hint for the model that will generate images for these frames. The images should be connected to each other, and the entire clip should reflect the meaning of the song and convey its mood. Describe in detail what people are wearing and how they behave, in what colors the image should be, in what mood it should be and in what style. The main characters should look the same in all images, the style of the entire slideshow should be the same, the color palette of all images should be the same, specify at what time or historical period the action takes place, all images should have the same period. The frames that will be shown with the text should convey what is said in these lines, these frames should be shown strictly in accordance with the text.
Please respond in the following format:

**Frame**: (without a number)
a timestamp indicating when this frame will be shown in the format XX:XX:XX.XX - XX:XX:XX.XX 

**Part of the song**: 
Print out which part of the song this frame belongs to: verse, chorus, intro, and so on. 

**Text**: 
Print out the fragments of the song in which this text will be displayed, if this frame will be displayed without text, then simply print "-"

**Prompt for the image generating model**: (maximum number of words - 77)
Specify the style (realistic), the mood, in which colors the image should be executed, the time or historical period in which the events take place, then describe what should be depicted in the picture, what the characters are wearing.
The lyrics along with the timestamps are: '''
    )

if "prompts_data" not in st.session_state:
        st.session_state.prompts_data = []




# Логика страниц
if st.session_state["current_page"] == "main":
    st.title("Создание слайд-шоу для песни")
    
    # Загрузка аудиофайла
    mp3_file = st.file_uploader("Upload an MP3 file", type=["mp3"])
    if mp3_file is not None:
        with open("static/mp3_file.mp3", "wb") as f:
            f.write(mp3_file.read())
            
    # Загрузка текстового файла
    txt_file = st.file_uploader("Upload a TXT file with lyrics", type=["txt"])
    if txt_file is not None and len(st.session_state.messages) == 0:
        text = txt_file.read().decode("utf-8")
        
        lyrics = create_lyrics(text)

        # Добавление роли модели 
        st.session_state.messages.append({
            "role": "system", 
            "content": st.session_state.role_message
        })

        # Добавление временных меток кадров (от лица пользователя)
        st.session_state.messages.append({
                "role": "user", 
                "content": lyrics
        })

    # Отображение истории сообщений
    for message in st.session_state.messages:
        if message["role"] != "system":  # Исключаем системное сообщение
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
    
    
    # Обычный чат после загрузки файлов
    if txt_file:
        if user_input := st.chat_input("Введите ваш вопрос или текст...") or len(st.session_state.messages) == 2:

            # Отображение сообщений пользователя 
            if len(st.session_state.messages) != 2:
                st.session_state.messages.append({"role": "user", "content": user_input})
                with st.chat_message("user"):
                    st.markdown(user_input)
            
            # Отоброжения ответа модели 
            with st.chat_message("assistant"):
                response_container = st.empty()

                messages = [
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages
                ]
                
                with st.spinner("Qwen2.5-72B is generating a response..."):
                    response = ""

                    stream = client.chat.completions.create(
                        model=st.session_state["openai_model"],
                        messages=messages,
                        stream=True,
                        temperature=0.1,
                        top_p=0.1,
                        max_tokens=8000,
                    )
                    
                    for chunk in stream:
                        if chunk.choices:
                            token = chunk.choices[0].delta.content
                            response += token
                            response_container.write(response)
                    
                    st.session_state.messages.append({"role": "assistant", "content": response})

    
    # Кнопка для перехода на страницу загрузки MP3-файла
    if st.button("Перейти к загрузке MP3-файла"):
        st.session_state["current_page"] = "upload"
        st.rerun() 

elif st.session_state["current_page"] == "upload":
    # Streamlit App
    st.title("MP3 & Lyrics Image Generator")

    
    # Получение последненго овтета модели 
    model_response  = st.session_state.messages[-1]["content"]

    # Сохранения ответа файла (для удобства)
    with open("static/text.txt", "w", encoding="utf-8") as f:
        f.write(model_response)
    txt_file = "static/text.txt"

    # Выбор цвета субтитров(вторичный цвет - цвет в который изначально красится текст, первичиный цвет в который перекрашивается текст когда произносится конкретное слово)
    col1, col2 = st.columns([1, 1])
    with col1:
        selected_color_1 = st.color_picker("Выберите первичный цвет субтитров:", "#ad6109")[1::]
        selected_color_1 = selected_color_1[4::] + selected_color_1[2:4:] + selected_color_1[:2:]
    with col2:
        selected_color_2 = st.color_picker("Выберите вторичный цвет субтитров:", "#C99457")[1::]
        selected_color_2 = selected_color_2[4::] + selected_color_2[2:4:] + selected_color_2[:2:]
        
    
    # Список шрифтов и их путей
    fonts_path = {
        'Balkara Free Condensed - npoekmu.me': 'font/ofont.ru_BalkaraCondensed.ttf',
        'Manrope': 'font/ofont.ru_Manrope.ttf',
        'Kaph': 'font/ofont.ru_Kaph.ttf',
        'BOWLER': 'font/ofont.ru_Bowler.ttf',
        'Handelson Five_CYR': 'font/18035.otf',
        'Garamond' : 'font/Garamond-Garamond-Regular.ttf', 
        'Huiwen ZhengKai Font (китайский шрифт)': 'font/Huiwen-ZhengKai-Font.ttf',
    }

    # Список языков для субтитров
    languages = {
        'Русский' : 'ru',
        'Английский' : 'en',
        'Китайский' : 'zh',
    }
    
    # Список вида фонограмм 
    phonograms = [
        'Плюс-фонограмма', 
        'Минус-фонограмма',
    ]

    # Выбор языка 
    language = st.selectbox('Выбрите язык субтитров', list(languages.keys()))
    language = languages[language]
    
    # Выбор шрифта
    # Для китайского языка подходят только конкретный шрфиты 
    if language == 'zh':
        font = st.selectbox("Выберите шрифт:", list({'Huiwen ZhengKai Font (китайский шрифт)': 'font/Huiwen-ZhengKai-Font.ttf'}.keys()))
    else:
        font = st.selectbox("Выберите шрифт:", list(fonts_path.keys()))
    font_path = fonts_path.get(font)
    
    #Выбор вида фонограммы 
    audio_type = st.selectbox(
        "Выберите вид фонограммы:",
        phonograms,
    )
    

    # Создаем изображение с текстом
    if font_path:
        sample_text = "Съешь ещё этих мягких французских булок, да выпей чаю" 
        img = create_text_image(sample_text, font_path)
        st.image(img, use_container_width=True)
    else:
        st.error("Шрифт не найден!")


    # Кнопка генерации изображения 
    if st.button("Generate Images"):
        prompts_data = process_song(model_response)
        
        new_prompts = []
        st.session_state.prompts_data = []
        for prompt_entry in prompts_data:
            if prompt_entry not in st.session_state.prompts_data:
                new_prompts.append(prompt_entry)

        st.session_state.prompts_data.extend(new_prompts)

    # Список эффектов, накладываемых поверх видео 
    effects = {
        'Без эффекта' : None,
        'Старая камера' : 'effects/vecteezy_flickering-super-8-film-projector-perfect-for-transparent_9902616.mov',
        'Звезды' : 'effects/vecteezy_million-gold-star-and-dark-triangel-flying-and-faded-on-the_15452899.mov', 
        'Снег' : 'effects/vecteezy_snowfall-overlay-on-green-screen-background-realistic_16108103.mov', 
        'Листопад' : 'effects/ezyZip.mov', 
        'Искры' : 'effects/vecteezy_fire-flame-particle-animation-green-screen-video_24397594.mov',
        'Кот' : 'effects/Green-Screen-Happy-Happy-Happy-Cat-Meme.mov',
        'Облака' : 'effects/vecteezy_4k-alpha-channel-render-fly-through-the-realistic-procedural_720p.mov',
        'Дождевые облака' : 'effects/vecteezy_free-download-rain-clouds-stock-video-clip_6529321.mov',
        'Солнечные лучи' : 'effects/vecteezy_light-leak-of-blue-lens-flare-in-the-background-light_38190348.mov',
        'Зеленый' : 'effects/vecteezy_light-leaks-light-green.mov',
        'Красный' : 'effects/vecteezy_light-leaks-light-red.mov',
        'Белый' : 'effects/vecteezy_light-leaks-light-white.mov',
        'Фиолетовый' : 'effects/vecteezy_light-leaks-purple.mov',
        'Летучие мыши' : 'effects/vecteezy_the-glowing-midnight-bats-in-black-screen_52182187.mov',
        'Желты летающие частици' : 'effects/vecteezy_gradient-background-from-brown-to-black-with-transparent_1794889.mov',
    }

    # Список видов переходов 
    effects_next = {
        'Без эффекта' : 0,
        'Короткий' : 2, 
        'Длинный' : 1,         
    }

    # Список коротких переходов между кадрами 
    short_effect = {
        "Красная капля" : 'effect_next/1.mov',
        "Черная капля" : 'effect_next/2.mov',
        "Фиолетовая капля " : 'effect_next/3.mov',
        "Белая капля" : 'effect_next/4.mov',  
        "Синяя волна" : 'effect_next/5.mov',  
        "Фиолетовая волна" : 'effect_next/6.mov',  
        "Розовая волна" : 'effect_next/7.mov',
        "Белая заморозка" : 'effect_next/8.mov',  
        "Желтая заморозка" : 'effect_next/9.mov', 
        "Белый дым" : 'effect_next/10.mov',  
        "Черный дым" : 'effect_next/11.mov',  
    }

    # Список длинных переходов между кадрами 
    long_effect = {
        "Черно красный круг" : 'effect_next/vecteezy_2-color-liquid-black-and-red-transition-green-screen_49115368.mov',
        "Красно белый жидкий переход" : 'effect_next/vecteezy_red-liquid-transition-green-screen_49115367.mov',
        "Градиентные чернила" : 'effect_next/vecteezy_transition-ink-gradient-color-green-screen-free_48868911.mov',
        "Сердечки" : 'effect_next/vecteezy_transitions-love-green-screen_48868982.mov',
        "Черный дым" : 'effect_next/vecteezy_smoke-transition-green-screen-black_48021329.mov',
        "Белый дым" : 'effect_next/vecteezy_smoke-transition-green-screen-white_48021329.mov',
    }

    # Количество изображений для каждого кадра 
    number_images = 1
    
    # Отображаем и генерируем изображения для каждого кадра
    if st.session_state.prompts_data:
        st.write("# Generated Images")

        # Переменная для отслеживания смены части песни
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

            # Отображение части песни, текста кадра, времнной метки кадра, промпта для генерации изображения и изображения, из которых нужно будет выбрать пользователю 
            with col1: 
                st.write(f"**Part:** {part}")
                st.write(f"**Lyrics:** {lyrics}")
                user_shot = st.text_area(
                    '**Prompt**', 
                    value=f"{shot}", 
                    height=68 , 
                    key=f'user_shot_{i}',
                )
                user_prompt = st.text_area(
                    '**Prompt**', 
                    value=f"{prompt}", 
                    height=150, 
                    key=f'user_input_{i}',
                )

                # отоброжение уже сгенерированных изобржаений, нужно того что бы при перезагрузки изображения каждый раз не перегенировались 
                if image_urls != []:
                    img = image_select("", image_urls)
                    st.session_state[f"selected_image_{i}"] = img 
                else:
                    # генерация изображений 
                    for _ in range(number_images): 
                        with st.spinner(f"Generating image"):
                            image_url = generate_image_for_prompt(prompt)
                            if image_url.startswith("static/"):
                                entry["image_url"].append(image_url)
                            else:
                                st.error(image_url)
                    img = image_select("Выберите изобаржение", entry["image_url"])
                    st.session_state[f"selected_image_{i}"] = img 

                #выбор изображения 
                selected_image = st.session_state.get(f"selected_image_{i}", None)
                if selected_image:
                    st.success("Selected image:")
                    st.image(selected_image)
                    
            # Отображение выбора эффекта, накладываемого на кадр, эффекта перехода на следующий кадр, кнопка перегенерировать     
            with col2:
                # выбор эффекта 
                selected_effect = st.selectbox(
                    "Выберите эффект:",
                    list(effects.keys()),
                    key=f"effect_{i}",
                )
    
                # Обновление выбранного эффекта в prompts_data
                entry['effect'] = effects[selected_effect]

                # Выбор вида эффекта перехода на следующий слайд 
                selected_effect = st.selectbox(
                    "Выберите эффект переключения на следующие видео:",
                    list(effects_next.keys()),
                    key=f"effect_next_{i}",
                )
                
                # Долгие эффекты переходов
                if selected_effect == "Длинный": 
                    effect_type = st.selectbox(
                        "Выберите эффект переключения на следующие видео:",
                        list(long_effect.keys()),
                        key=f"effect_next_long{i}",
                    )
                    entry['effects_next'] = long_effect[effect_type]

                # Быстрые эффекты перехода 
                elif selected_effect == "Короткий":
                    effect_type = st.selectbox(
                        "Выберите эффект переключения на следующие видео:",
                        list(short_effect.keys()),
                        key=f"effect_next_short{i}",
                    )

                    entry['effects_next'] = short_effect[effect_type]
                else: 
                    entry['effects_next'] = None
                
                # Кнопка перегенерировать 
                if st.button("Перегенерировать", key=f'button_{i}'):
                    
                    entry["image_url"] = [] 

                    # Проверяем изменен ли промпт 
                    if user_prompt != prompt: 
                        entry["prompt"] = user_prompt
                        prompt = user_prompt

                    # Генерация новых изображений 
                    for _ in range(number_images): # количество изображений для одного кадра 
                        with st.spinner(f"Generating image"):
                            image_url = generate_image_for_prompt(prompt)
                            if image_url.startswith("static/"):
                                entry["image_url"].append(image_url)
                            else:
                                st.error(image_url)
                                
                    st.session_state[f"selected_image_{i}"] = None
                    st.rerun()

            # проверяем изменина ли временная метка кадра
            if user_shot != shot: 
                entry["shot"] = user_shot
                shot = user_shot 
            
            st.write('---')
        
    # Кнопка генерации видео по выбранным изобаржениям 
    if st.button("Generate Video with Selected Images"):

        # Выбранные изображения 
        selected_images = [
            st.session_state.get(f"selected_image_{idx}")
            for idx in range(len(st.session_state.prompts_data))
        ]
    
        # Проверяем, что все изображения выбраны
        if None in selected_images:
            st.error("Please select an image for all lyrics!")
        else:
            # Генерация и отображение видео 
            video_url = create_videos(st.session_state.prompts_data, selected_images, txt_file, font, font_path, selected_color_1, selected_color_2, audio_type, language)
            if video_url and not video_url.startswith("Error"):
                st.video(video_url)
            else:
                st.error(f"Failed to create video: {video_url}")

    # Кнопка перехода на главную страницу 
    if st.button("Вернуться на главную"):
        st.session_state["current_page"] = "main"
        st.rerun()

    
        