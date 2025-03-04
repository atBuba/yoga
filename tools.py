import requests
import os 
import xml.etree.ElementTree as ET
import moviepy.editor as mp
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import *
import random
from subtitles import *
from typing import Union
import re
from datetime import timedelta
import subprocess
from time import sleep
from fontTools.ttLib import TTFont
from test import adiou_to_time_text
import streamlit as st
import shutil

# token for yandex translate 
IAM_TOKEN = 'AQVNzbPNKEeoixhfHLFZavVdM66AJ23Ow4zFkKwQ'
folder_id = 'b1gbfto7jeu1ghuc8heq'

URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"


def translate_text(texts: str, language : str) -> str:
    '''
    Translates text from Russian to English (or another target language) 
    using the Yandex Translate API.

    Parameters:
    -----------
    texts : str
        The source text to be translated.

    Returns:
    --------
    str
        The translated text in the target language.
    '''

    body = {
        "targetLanguageCode": language,
        "texts": texts,
        "folderId": folder_id,
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": "Api-Key {0}".format(IAM_TOKEN)
    }

    response = requests.post('https://translate.api.cloud.yandex.net/translate/v2/translate',
        json=body,
        headers=headers
    )

    return response.json()['translations'][0]['text']


def detect_language(text):
    url = "https://translate.api.cloud.yandex.net/translate/v2/detect"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Api-Key {0}".format(IAM_TOKEN)
    }
    data = {
        "folderId": folder_id,
        "text": text
    }
    
    response = requests.post(url, json=data, headers=headers)
    
    if response.status_code == 200:
        language_code = response.json().get("languageCode", "Не удалось определить язык")
        return language_code
    else:
        return f"Ошибка: {response.status_code}, {response.text}"


def generate_prompt(user_text):    
    # Собираем запрос
    data = {}
    # Указываем тип модели
    data["modelUri"] = f"gpt://{folder_id}/yandexgpt/rc"
    # Настраиваем опции
    data["completionOptions"] = {"temperature": 0.3, "maxTokens": 1000}
    # Указываем контекст для модели
    data["messages"] = [
        {"role": "system", "text": "напиши промт на английском языке для генерации изображения по двум строчкам из песни, затем напиши второй промт для анимации этого изображения изображения. Ответь в формате **Prompt 1** \nprompt \n**Prompt 2**\nprompt"},
        {"role": "user", "text": f"{user_text}"},
    ]
    
    # Отправляем запрос
    response = requests.post(
        URL,
        headers={
            "Accept": "application/json",
            "Authorization":  "Api-Key {0}".format(IAM_TOKEN)
        },
        json=data,
    ).json()

    #Распечатываем результат
    # message  = json.load(response)['result']['alternatives']['message']
    message = response['result']['alternatives'][0]['message']['text']
    prompts = re.findall(r'\*\*Prompt\s+\d+\*\*\s*:?[\s\n]*(.*?)(?=\n\*\*Prompt|\Z)', message, re.DOTALL)
    
    return prompts 


def add_audio_to_video(video_path: str, audio_path: str, output_path: str) -> None:
    """
    Добавляет аудио к видео с помощью FFmpeg.

    Параметры:
    ----------
    video_path : str
        Путь к исходному видеофайлу.
    audio_path : str
        Путь к аудиофайлу, который нужно добавить.
    output_path : str
        Путь для сохранения видео с аудио.

    Возвращает:
    ----------
    None
    """
    import subprocess
    import shutil
    import os

    # Получаем путь до ffmpeg, если он не указан
    ffmpeg_path = shutil.which('ffmpeg') or "C:/Users/admin/Documents/BrokenSource/Broken/Externals/Archives/ffmpeg-master-latest-win64-gpl/ffmpeg-master-latest-win64-gpl/bin/ffmpeg.exe"

    # Формируем команду для добавления аудио к видео
    command = [
        ffmpeg_path, 
        '-i', video_path,      # Видео файл
        '-i', audio_path,      # Обрезанный аудио файл
        '-c:v', 'copy',        # Копирование видео без изменений
        '-c:a', 'aac',         # Используем кодек AAC для аудио
        '-strict', 'experimental',  # Для использования нестандартных кодеков
        '-y',                  # Перезаписываем файл без подтверждения
        output_path            # Выходной файл
    ]
    
    # Запускаем команду
    subprocess.run(command)
    
def parse(ttml_file: str =None, txt_files: str =None, two_lines: bool = False,  word: bool = False) -> list[dict[str, Union[float, str]]]:
    '''
    Parses a TTML (Timed Text Markup Language) file or txt and extracts subtitles
    as a list of dictionaries with start time, end time, and text.

    Parameters:
    -----------
    ttml_file : str
        The path to the TTML file to be parsed.
    txt_file : str
        The path to the TTML file to be parsed.
    two_lines : bool
        True if you need to combine the text into two lines
    word : bool
        True if you need parse word in txt. file format 

    Returns:
    --------
    list[dict[str, str]]:
        A list of dictionaries, where each dictionary represents a subtitle entry
        with the following keys:
        - 'start': flost - The start time of the subtitle.
        - 'end': float - The end time of the subtitle. If not specified, it will be set
          to the start time of the next subtitle.
        - 'text': str - The text content of the subtitle.
    '''

    slides = []
    
    #parse ttml
    if ttml_file:
        tree = ET.parse(ttml_file)
        root = tree.getroot()
        
        namespace = "{http://www.w3.org/ns/ttml}"  # Стандартное пространство имен TTML
        
        # Parsing ttml file and create list 
        for elem in root.findall(f".//{namespace}body//{namespace}p"):
            start_time = elem.attrib['begin']
            end_time = elem.attrib.get('end', None)
            text = elem.text.strip() if elem.text else ""
            
            slides.append({
                'start': start_time,
                'end': end_time,
                'text': text
            })
        
        # normalizing the ttml file (end word == start next word)
        for i in range(0, len(slides) - 1):
            slides[i]['end'] = slides[i + 1]['start']

        for i, line in enumerate(slides):
            line['start'] = float(line['start'][:-1:])
            line['end'] = float(line['end'][:-1:])

    #parse txt for lines 
    elif txt_files and not(word):
        duration_line = 4
        current_line = 0
        
        file = open(txt_files, 'r', encoding='utf-8') 
        lyrics = file.read()

        lyrics = re.sub(r'\[.*?\]', '', lyrics).strip()

        lyrics = lyrics.split('\n')[::]

        for line in lyrics:
            slides.append({
                'start' : current_line,
                'end' : current_line + duration_line,
                'text' : line,
            })
            current_line += duration_line   

    #parse txt for words 
    elif txt_files and word:
        slides.append({
            'start' : 0,
            'end' : 0,
            'text' : '',
        })

        duration_line = 4
        duration_word = 0
        current_word = 0

        file = open(txt_files, 'r', encoding='utf-8') 
        lyrics = file.read().split('\n')

        for line in lyrics:
            duration_word = duration_line / len(line.split(' '))
            for word in line.split():
                slides.append({
                    'start' : current_word,
                    'end' : current_word + duration_word,
                    'text' : word,
                })
                current_word += duration_word   

    
    # combining lines
    if two_lines:
        slides_two_lines = []
        combinedText = ''
        combinedTextStart = 0
        combinedTextEnd = 0
        start = 0 
        end = 0
        
        for i in range(0, len(slides), 2):
            if i + 1 < len(slides):
                s = slides[i]['text'] +  ' \n' + slides[i + 1]['text']
                start = slides[i]['start']
                end = slides[i + 1]['end']
            else:
                s = slides[i]['text']
                start = slides[i]['start']
                end = slides[i]['end']

            


            if combinedText:
                s = combinedText + ' \n' + s
                combinedText = ''
                start = combinedTextStart
                combinedTextStart = 0
                combinedTextEnd = 0
            

            if len(s.split(' ')) <= 6:
                combinedText = s
                combinedTextStart = start 
                combinedTextEnd = end
            else:     
                slides_two_lines.append({
                'start': start,
                'end': end,
                'text':s
        })
            
        if (combinedTextStart == 0) and (combinedTextEnd ==  0):
            slides_two_lines.append({
                'start': combinedTextStart,
                'end': combinedTextEnd,
                'text':combinedText
            })

        slides = slides_two_lines[::]

    return slides


def generate_ass(ttml_words, ttml_lines, output_file, font, font_color_1, font_color_2):
    header = f"""[Script Info]
Title: Karaoke Lyrics
ScriptType: v4.00+
Collisions: Normal
PlayDepth: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},23,&H00{font_color_1},&H00{font_color_2},&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,3,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    j = 0

    ttml_lines = ttml_lines[::]
    for line in ttml_lines:
        # if j != 0:
        #     start_time, end_time = ttml_words[j - 1]['end'], ttml_words[j + len(line['text'].split()) - 1]['end']
        # else: 
        #     start_time, end_time = 0, ttml_words[j + len(line['text'].split()) - 1]['end']

        start_time, end_time = ttml_words[j]['start'] - 0.4, ttml_words[j + len(line['text'].split()) - 1]['end']
        duration_clip= end_time - start_time
            
        karaoke_line = ""
        for i in range(j, j + len(line['text'].split())):
            if i != j:
                duration = (ttml_words[i]['end'] - ttml_words[i - 1]['end']) * 100  # duration in centiseconds
                karaoke_line += f"{{\\kf{int(duration)}}}{ttml_words[i]['text']} "               
            else:
                duration = (ttml_words[i]['end'] - start_time) * 100  # duration in centiseconds
                karaoke_line += f"{{\\fad(400,0)\\an2\\kf{int(duration)}}}{ttml_words[i]['text']} "

        events.append(f"Dialogue: 0,{format_time(start_time)},{format_time(end_time)},Default,,0,0,0,,{karaoke_line.strip()}")
        j += len(line['text'].split())

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(events))


def generate_ass_eng(ttml_words, ttml_lines, eng_lyrics, output_file, font, font_path, font_color_1, font_color_2, font_size):
    header = f"""[Script Info]
Title: Karaoke Lyrics
ScriptType: v4.00+
PlayResX: {1280}
PlayResY: {720}
Collisions: Normal
PlayDepth: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},{font_size},&H00{font_color_1},&H00{font_color_2},&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,3,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    j = 0

    eng_lyrics = eng_lyrics.split('\n')
    effects = [apply_fade_in, apply_scale_up, apply_word_fade_in, apply_word_fly_in, apply_letter_fly_in]  # Список эффектов
    
    for i, line in enumerate(ttml_lines):
        start_time, end_time = ttml_words[j]['start'] - 0.4, ttml_words[j + len(line['text'].split()) - 1]['end'] - 0.2
        effect_func = random.choice(effects)  # Выбираем случайный эффект
        effect_text = effect_func(eng_lyrics[i], font_size, font_path, start_time, end_time)  # Применяем эффект
        events.append(f"{effect_text}")
        j += len(line['text'].split())

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(events))

# Эффекты:
def apply_fade_in(text, font_size, font_path, start_time, end_time):
    """Эффект появления текста (fade in)"""
    return f"Dialogue: 0,{format_time(start_time)},{format_time(end_time)},Default,,0,0,0,,{{\\alpha&HFF&\\t(0,200,\\alpha&H00&)}}{text}"

def apply_scale_up(text, font_size, font_path, start_time, end_time):
    """Эффект увеличения текста (scale up)"""
    return f"Dialogue: 0,{format_time(start_time)},{format_time(end_time)},Default,,0,0,0,,{{\\fscx30\\fscy30\\t(0,200,\\fscx100\\fscy100)}}{text}"

def apply_word_fade_in(text, font_size, font_path, start_time, end_time, screen_width=1280, screen_height=720, duration=200):
    """Эффект плавного появления каждого слова с правильным выравниванием"""
    result = []
    margin_bottom = 10  # Отступ от низа экрана
    glyph_widths_px = get_glyph_widths_in_pixels(font_path, font_size)  # Расстояние между буквами
    line_height = font_size  # Высота строки

    lines = split_text_into_lines(text, screen_width - 40, glyph_widths_px)  # Автоперенос строк
    num_lines = len(lines)
    
    delay_step = 0.7 * (end_time - start_time) / max(len(text.split()), 1) 

    for line_index, line in enumerate(lines):
        text_line, width  = line 
        text_width = width  # Ширина строки
        start_x = (screen_width - text_width) // 2  # Центрируем строку
        start_y = screen_height - margin_bottom - (num_lines - 1 - line_index) * line_height  # Центр внизу



        final_x = start_x
        final_y = start_y

        current_word = ""
        word_witdh = 0

        for i, letter in enumerate(text_line + " "):
            if letter.strip():  # Пропускаем пробелы
                word_witdh += glyph_widths_px[letter]
                current_word += letter

            else: 
                 # Добавляем эффект ускорения и кривой траектории
                effect = f"{{\\pos({start_x + word_witdh // 2},{final_y})\\alpha&HFF&\\t(0,{duration},\\alpha&H00&)}}"
                result.append(f"Dialogue: 0,{format_time(start_time)},{format_time(end_time)},Default,,0,0,0,,{effect}{current_word}")
                start_time += delay_step
                
                current_word = ""
                word_witdh += glyph_widths_px[" "]
                start_x += word_witdh
                word_witdh = 0
                

    return "\n".join(result)


def apply_word_fly_in(text, font_size, font_path, start_time, end_time, screen_width=1280, screen_height=720, duration=400):
    """Эффект появления букв в случайных местах с изменением траектории и ускорением"""
    result = []
    margin_bottom = 10  # Отступ от низа экрана
    glyph_widths_px = get_glyph_widths_in_pixels(font_path, font_size)  # Расстояние между буквами
    line_height = font_size  # Высота строки

    lines = split_text_into_lines(text, screen_width - 40, glyph_widths_px)  # Автоперенос строк
    num_lines = len(lines)
    
    directions = ["left", "right", "top", "bottom"]
    
    for line_index, line in enumerate(lines):
        text_line, width  = line 
        text_width = width  # Ширина строки
        start_x = (screen_width - text_width) // 2  # Центрируем строку
        start_y = screen_height - margin_bottom - (num_lines - 1 - line_index) * line_height  # Центр внизу



        final_x = start_x
        final_y = start_y

        current_word = ""
        word_witdh = 0
        
        for i, letter in enumerate(text_line + " "):
            if letter.strip():  # Пропускаем пробелы
                word_witdh += glyph_widths_px[letter]
                current_word += letter

            else: 
                direction = random.choice(directions)
        
                if direction == "left":
                    x, y = -100, start_y
                elif direction == "right":
                    x, y = screen_width + 100, start_y
                elif direction == "top":
                    x, y = start_x, -50
                else:  # bottom
                    x, y = start_x, screen_height + 50
                    
                 # Добавляем эффект ускорения и кривой траектории
                effect = f"{{\\move({x},{y},{start_x + word_witdh // 2},{final_y},0,{duration})\\t(0,{duration},1}}"
                result.append(f"Dialogue: 0,{format_time(start_time)},{format_time(end_time)},Default,,0,0,0,,{effect}{current_word}")
                current_word = ""
                word_witdh += glyph_widths_px[" "]
                start_x += word_witdh
                word_witdh = 0
                

    return "\n".join(result)
    
    
    glyph_widths_px = get_glyph_widths_in_pixels(font_path, font_size)

    for i, word in enumerate(words):
        

        final_x = start_x
        final_y = start_y

        effect = f"{{\\move({x},{y},{final_x},{final_y},0,{duration})}}"
        result.append(f"Dialogue: 0,{format_time(start_time)},{format_time(end_time)},Default,,0,0,0,,{effect}{word}")

        start_x += glyph_widths_px.get(word, font_size) + 10  # Смещаем вправо

    return "\n".join(result)

def apply_letter_fly_in(text, font_size, font_path, start_time=0.0, end_time=0.0, screen_width=1280, screen_height=720, duration=400):
    """Эффект появления букв в случайных местах с изменением траектории и ускорением"""
    result = []
    margin_bottom = 10  # Отступ от низа экрана
    glyph_widths_px = get_glyph_widths_in_pixels(font_path, font_size)  # Расстояние между буквами
    line_height = font_size  # Высота строки

    lines = split_text_into_lines(text, screen_width - 40, glyph_widths_px)  # Автоперенос строк
    num_lines = len(lines)
    
    for line_index, line in enumerate(lines):
        text_line, width  = line 
        text_width = width  # Ширина строки
        start_x = (screen_width - text_width) // 2  # Центрируем строку
        start_y = screen_height - margin_bottom - (num_lines - 1 - line_index) * line_height  # Центр внизу



        final_x = start_x
        final_y = start_y
        
        for i, letter in enumerate(text_line):
            if letter.strip():  # Пропускаем пробелы
                # Случайные начальные координаты (вне экрана)
                x = random.randint(100, screen_width - 100)
                y = random.randint(100, screen_height - 100)

                # Финальные координатыяё
                

                # Добавляем эффект ускорения и кривой траектории
                effect = f"{{\\move({x},{y},{start_x + glyph_widths_px[letter] // 2},{final_y},0,{duration})\\t(0,{duration},0.5}}"

                # Добавляем строку с эффектом
                result.append(f"Dialogue: 0,{format_time(start_time)},{format_time(end_time)},Default,,0,0,0,,{effect}{letter}")
                start_x += glyph_widths_px[letter]
            else: 
                start_x += glyph_widths_px[" "]

    return "\n".join(result)


def get_glyph_widths_in_pixels(font_path, font_size_px=16):
    """Возвращает ширину каждого символа в пикселях."""
    font = TTFont(font_path)
    hmtx = font["hmtx"]  # Таблица горизонтальных метрик
    cmap = font.getBestCmap()  # Таблица соответствия символов и глифов
    units_per_em = font["head"].unitsPerEm  # Количество единиц на em

    glyph_widths_px = {}
    for char_code, glyph_name in cmap.items():
        width_units, _ = hmtx[glyph_name]  # Ширина в em-единицах
        width_px = round((width_units / units_per_em) * font_size_px)  # Перевод в пиксели
        glyph_widths_px[chr(char_code)] = width_px

    return glyph_widths_px




def split_text_into_lines(text, max_width, glyph_widths_px):
    """Разбивает текст на строки, учитывая максимальную ширину"""

    lines = []
    text = list(text + ' ')

    current_word = ""
    current_line = "" 

    word_width = 0
    current_width = 0

    for character in text:
        if character != " ":
            current_word += character
            word_width += glyph_widths_px[character]
        else: 
            if current_width + word_width > max_width:  # Перенос строки
                lines.append([current_line.strip(), current_width])
                current_line = current_word
                current_width = word_width
                current_word = ""
                word_width = 0
            else:
                current_line += " " + current_word
                current_width += word_width + glyph_widths_px[" "] 
                current_word = ""
                word_width = 0
                 

    if current_line:
        lines.append([current_line.strip(), current_width])

    return lines

def format_time(seconds):
    td = timedelta(seconds=float(seconds))
    # Получаем количество секунд с остаточными миллисекундами
    total_seconds = td.total_seconds()
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    seconds, milliseconds = divmod(seconds, 1)
    milliseconds = round(milliseconds, 3)  # округляем до 3 знаков после запятой

    # Форматируем время с часами, минутами, секундами и миллисекундами
    return f"{int(hours):0>2}:{int(minutes):0>2}:{int(seconds):0>2}.{int(milliseconds * 1000):03}"[:-1:]

def  create_subtitles_2(input_video, subtitles_file, output_video):
    command = [
            "ffmpeg",
            "-i", input_video,
            "-vf", f"ass={subtitles_file}",
            '-y',
            # '-attach', 'font/BalkaraCondensed.ttf', 
            'video/temp_video.mp4',
        ]
        # Запуск команды FFmpeg
    subprocess.run(command, check=True)  

def add_effect(video, effect):
    temp_file = "videos/temp.mp4"

    # print(effect)
    # print(video)
    if get_video_duration(video) > get_video_duration(effect):
        command = [
            "ffmpeg",
            "-i", video,
            "-stream_loop", "-1",
            "-i", effect,
            "-filter_complex", "[0:v][1:v]overlay=shortest=1",
            '-c:a', 'copy',
            # "-c:v", "libx264",
            # "-crf", "23",
            # "-preset", "veryfast",
            '-t', str(get_video_duration(video)),
            "-y", temp_file
        ]
    else: 
        command = [
            "ffmpeg",
            "-i", video,
            # "-stream_loop", "-1",
            "-i", effect,
            "-filter_complex", "[0:v][1:v]overlay=shortest=1",
            '-c:a', 'copy',        
            # "-c:v", "libx264",
            # "-crf", "23",
            # "-preset", "veryfast",
            '-t', str(get_video_duration(video)),
            "-y", temp_file
        ]
    subprocess.run(command, check=True)  
    os.replace(temp_file, video)



# Функция для создания команды FFmpeg
def concatenate_videos(video_files, output_file, effects_next, fade_duration=0.2):
    print('Создание видео со склейкой и эффектом появления (fade in)')
    
    filter_complex_parts = []
    input_files = []
    
    for i, video in enumerate(video_files):
        input_files.extend(["-i", video])
        filter_complex_parts.append(
            f"[{i}:v]fade=t=in:st=0:d={fade_duration}[v{i}]"
        )
    
    video_streams = "".join(f"[v{i}]" for i in range(len(video_files)))
    filter_complex = ";".join(filter_complex_parts) + f";{video_streams}concat=n={len(video_files)}:v=1:a=0[outv]"
    
    command = [
        "ffmpeg",
        *input_files,
        "-filter_complex", filter_complex,
        "-map", "[outv]",  
        "-c:v", "libx264",
        "-preset", "fast",
        "-y", output_file
    ]
    print(command)
    
    print(' '.join(command))
    
    try:
        subprocess.run(command, shell=False, check=True)
    except subprocess.CalledProcessError as e:
        print("Ошибка при обработке видео:", e)

    durations = []
    dd = 0
    for i in range(len(video_files) - 1):
        video_duration = get_video_duration(video_files[i])
        if effects_next[i]: 
            durations.append([effects_next[i], dd + float(video_duration)])    
            dd = 0
            
        else: 
            dd += float(video_duration)
            
    if len(durations):
        apply_chromakey_with_overlays(output_file, durations,)


def get_video_duration(video_file):
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", video_file], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return float(result.stdout)




def apply_chromakey_with_overlays(base_video, durations):
    # Выходное видео сохраняется с тем же именем
    temp_file = "videos/temp.mp4"

    filter_complex = []
    inputs = [f'-i {base_video}']
    for i, dur in enumerate(durations):
        if dur[0]:
            inputs.append(f'-i {dur[0]}')

    
    overlay_streams = []

    duration = 0 
    for i, dur in enumerate(durations):
        if dur[0]:
            time = get_video_duration(dur[0])
            if time > 3.0:
                tr = f'tr{i}'
                over = f'over{i}'
                delay = duration + durations[i][1] - 2.0  
                duration += durations[i][1]
                filter_complex.append(
                    f'[{i+1}:v]setpts=PTS+{delay}/TB[{tr}]'
                )
                overlay_streams.append(tr)
            else:
                tr = f'tr{i}'
                over = f'over{i}'
                delay = duration + durations[i][1] - 0.6
                duration += durations[i][1]
                filter_complex.append(
                    f'[{i+1}:v]setpts=PTS+{delay}/TB[{tr}]'
                )
                overlay_streams.append(tr)   
            
    base = '[0:v]'
    for i, over in enumerate(overlay_streams):
        output = f'base{i+1}' if i < len(overlay_streams) - 1 else 'v'
        filter_complex.append(f'{base}[{over}]overlay[{output}]')
        base = f'[{output}]'
    
    filter_complex_str = '; '.join(filter_complex)
    
    command = [
        'ffmpeg',
        *inputs,
        '-filter_complex', f'"{filter_complex_str}"',
        '-map', '[v]',
        '-c:v', 'libx264',
        '-c:a', 'aac',
        '-preset', 'fast',
        '-y', temp_file  # Перезаписываем исходный файл
    ]

    print(' '.join(command))
    
    subprocess.run(' '.join(command), shell=True)

    os.replace(temp_file, base_video)

    return base_video  # Возвращаем путь к перезаписанному файлу

    


def  create_subtitles(ttml_lines: list[dict[str, Union[float, str]]], ttml_words: list[dict[str, Union[float, str]]], font: str ="arial.ttf", font_color: str = 'white', size=(848, 480), font_size: int =40) -> list[CompositeVideoClip]:
    '''
    Create list of CompositeVideoClip of animated subtitles with a transparent background

    Parameters:
    -----------
    ttml_lines : list[dict[str, Union[float, str]]]:
        A list of dictionaries, where each dictionary represents a line from the song
        with the following keys:
        - 'start': flost - The start time of the subtitle.
        - 'end': float - The end time of the subtitle. If not specified, it will be set
          to the start time of the next subtitle.
        - 'text': str - The text content of the subtitle.
    ttml_words : list[dict[str, Union[float, str]tr]]:
        A list of dictionaries, where each dictionary represents a one word from the song
        with the following keys:
        - 'start': flost - The start time of the subtitle.
        - 'end': float - The end time of the subtitle. If not specified, it will be set
          to the start time of the next subtitle.
        - 'text': str - The text content of the subtitle
    font : str
        The path for .otf or .ttf file format
    font_color : str
        The color of the text

    Returns:
    --------
    list of CompositeVideoClip of subtitles with a transparent background
    '''

    final_video = []
    animations = [
        movie_latters,
        animate_words_pop_up,
        # animate_cross,
        animate_words,
        animate_left_angle,
    ]

    word_number = 0
    animation_number = 0

    for i, line in enumerate(ttml_lines):  
        print(line)
        animation  = animations[animation_number]
        words = ttml_words[word_number:word_number + len(line['text'].split())]

        if animation_number == 1 and len(words) > 5:
            animation  = animations[0]
        if animation_number == 2 and len(words) > 5:
            animation  = animations[0]  

        animation_number += 1
        animation_number %= len(animations) 
        word_number += len(line['text'].split())
        
        clip = animation(text=line['text'], ttml=words, duration=words[-1]['end'] - words[0]['start'], font=font, font_color=font_color, size=size, font_size=font_size)
        final_video.append(clip.set_start(words[0]['start']).set_position('right'))

    return final_video

def animation(image: ImageClip, animation: str) -> ImageClip:
    '''
    Сreates an animation of the appearance of an image

    Parameters:
    -----------
    image : ImageClip
        The image whose appearance should be animated
    animation : str
        The name of animation (fading, center, right2left, left2right)

    Returns:
    --------
    ImageClip with appearance animated  
    '''

    effect_duration = 0.1
    image_width = image.w
    step = image_width / effect_duration

    if animation == 'fading': 
        image = image.fadein(effect_duration)
    elif animation == 'center':
        image = image.set_position(('center', 'center'))
        image = image.resize(lambda t: 0.1 + 0.9 * min(t / effect_duration, 1))
    elif animation == 'rigth2left':
        image = image.set_position(
            lambda t: (image_width - step * t, 'center') if t < effect_duration else ('center', 'center')
        )
    elif animation == 'left2right':
        image = image.set_position(
            lambda t: (-image_width + step * t, 'center') if t < effect_duration else ('center', 'center')
        )
    
    return image

def create_slideshow(images: list[ImageClip] , ttml_words: list[dict] =None, ttml_lines: list[dict] =None, font: str ="arial.ttf", font_color: str='white', output_path:str ="combined_images.mp4", addSubtitles: bool =False, font_size: int =40) -> None:
    '''
    creates and saves videos in output_path with animated appearance of images and animated appearance of text

    Parameters:
    -----------
    images : list[ImageClip]
        The list of image whose be in video
    animation : str
        The name of animation (fading, center, right2left, left2right)
    ttml_lines : list[dict[str, str]]:
        A list of dictionaries, where each dictionary represents a line from the song
        with the following keys:
        - 'start': flost - The start time of the subtitle.
        - 'end': float - The end time of the subtitle. If not specified, it will be set
          to the start time of the next subtitle.
        - 'text': str - The text content of the subtitle.
    ttml_words : list[dict[str, str]]: 
        A list of dictionaries, where each dictionary represents a one word from the song
        with the following keys:
        - 'start': flost - The start time of the subtitle.
        - 'end': float - The end time of the subtitle. If not specified, it will be set
          to the start time of the next subtitle.
        - 'text': str - The text content of the subtitle
    font : str
        The path for .otf or .ttf file format
    font_color : str
        The color of the text
    addSubtitles : bool
        True if need add subtitles for video
    output_path : str
        The path where the video be saved 

    Returns:
    --------
    None
    '''
    animations = ['fading', 'rigth2left', 'left2right']
    animation_clips = []
    current_start_time = 0 
    textbox_size = (int(images[0].size[0]*0.45), int(images[0].size[1]*0.8))
    
    for image in images:
        anim = random.choice(animations)
        clip = animation(image, anim)
        clip = clip.set_start(current_start_time)
        current_start_time += (clip.duration)
        animation_clips.append(clip)
    
    # Concatenate animation clips
    final_clip = concatenate_videoclips(animation_clips, method="compose")

    # Ensure output directory exists
    if not os.path.exists('video'):
        os.makedirs('video')
    
    # Write the final video file
    final_clip.write_videofile(output_path, fps=30, codec='libx264', threads=0)
    if addSubtitles:
        create_subtitles_2(output_path, 'static/subtitles.ass', output_path)
    print(f"Видео сохранено как: {output_path}")



def check_file_exists(file_path: str) -> bool:
    '''
    Cheak exists file in file_path

    Parameters:
    -----------
    file_path : str
        The path to the file 

    Returns:
    --------
    True - file in file path   
    False - else
    
    '''

    return os.path.exists(file_path)


def adjust_video_duration(video_path, required_duration):
    clip = VideoFileClip(video_path)
    current_duration = clip.duration
    if current_duration < required_duration:
        # Calculate how many times to repeat the video
        repeat_count = math.ceil(required_duration / current_duration)
        clips = [clip] * repeat_count
        extended_clip = concatenate_videoclips(clips)
        # Trim to required duration
        extended_clip = extended_clip.subclip(0, required_duration)
    else:
        # Trim to required duration
        extended_clip = clip.subclip(0, required_duration)
    return extended_clip

def create_lyrics(text):

    pattern = re.compile(r"(\[.*?\])\s*(.*?)(?=\n\[|\Z)", re.DOTALL)
    text = re.sub(r'\(.*?\)', '', text)
    
    parsed_lyrics = [
        {"text": line.strip(), "section": match[0].strip("[]")}
        for match in pattern.findall(text)
        for line in match[1].strip().split("\n") if line.strip()
    ]
    
    lyrics = ""
    
    # Вывод результата
    for item in parsed_lyrics:
        lyrics += item["text"] + "\n"
    
    audio_path = 'static/mp3_file.mp3'
    vocal_path = 'static/vocal.mp3'
    no_vocal_path = 'static/no_vocal.mp3'
    
    lyrics_file = 'static/lyrics.txt'
    
    with open(lyrics_file, "w", encoding="utf-8") as file:
        file.write(lyrics + "\n")  
    
    
    words_timestamps  = adiou_to_time_text(audio_path, lyrics_file)
    
    start, end = 0.0, 0.0
    
    number_word = 0
    
    for item in parsed_lyrics:
        start = words_timestamps[number_word]['start']
            
        end = words_timestamps[number_word + len(item['text'].split()) - 1]['end']
    
        number_word += len(item['text'].split())   
    
        item['start'] = start 
        item["end"] = end

    
    frames = []


    if parsed_lyrics[0]['start']  > 5.0:
        first_frame = {
            'start' : 0.0,
            'end' : parsed_lyrics[0]['start'],
            'text' : '-',
            'section' : '[intro]',
        }
        number_line = 0
    else:
        first_frame = {
            'start' : 0.0,
            'end' : parsed_lyrics[0]['end'],
            'text' : parsed_lyrics[0]['text'],
            'section' : parsed_lyrics[0]['section'],
        }
        number_line = 1
    
    frame_start = first_frame['start']
    frame_end = first_frame['end']
    frame_text = first_frame['text']
    frame_section = first_frame['section']
    
    while number_line < len(parsed_lyrics):
    
        if ((frame_end - frame_start) > 10.0) and (frame_text == '-'):
            div = 2
            while ((frame_end - frame_start) / (div + 1)) > 5.0:
                div += 1
            dur = (frame_end - frame_start) / (div)
            for i in range(div):
                frames.append({
                    'start' : frame_start + i * dur,
                    'end' : frame_start + (i + 1) * dur,
                    'text' : frame_text,
                    'section' : frame_section,
                })
                
            if parsed_lyrics[number_line]['start'] - frame_end < 5.0: 
                frame_start = parsed_lyrics[number_line]['start'] 
                frame_end = parsed_lyrics[number_line]['end']
                frame_text = parsed_lyrics[number_line]['text']
                frame_section = parsed_lyrics[number_line]['section']
    
                number_line += 1
            else: 
                frame_end = parsed_lyrics[number_line]['start']
                frame_text = '-'
                frame_section = '[break]'
            
                
        elif ((frame_end - frame_start) < 5.0) and (frame_text != '-'):
            if frame_section == parsed_lyrics[number_line]['section']:
                frame_end = parsed_lyrics[number_line]['end']
                frame_text += '\n' + parsed_lyrics[number_line]['text']
                number_line += 1
            else: 
                frames.append({
                    'start' : frame_start,
                    'end' : frame_end,
                    'text' : frame_text,
                    'section' : frame_section,
                })
    
                frame_start = frame_end
    
                if parsed_lyrics[number_line]['start'] - frame_end < 5.0: 
                    frame_end = parsed_lyrics[number_line]['end']
                    frame_text = parsed_lyrics[number_line]['text']
                    frame_section = parsed_lyrics[number_line]['section']
    
                    number_line += 1
                else: 
                    frame_end = parsed_lyrics[number_line]['start']
                    frame_text = '-'
                    frame_section = '[break]'
    
        else:
            frames.append({
                'start' : frame_start,
                'end' : frame_end,
                'text' : frame_text,
                'section' : frame_section,
            })
    
            frame_start = frame_end
    
            if parsed_lyrics[number_line]['start'] - frame_end < 5.0: 
                frame_end = parsed_lyrics[number_line]['end']
                frame_text = parsed_lyrics[number_line]['text']
                frame_section = parsed_lyrics[number_line]['section']
    
                number_line += 1
            else: 
                frame_end = parsed_lyrics[number_line]['start']
                frame_text = '-'
                frame_section = '[break]'
    
    frames.append({
        'start' : frame_start,
        'end' : frame_end,
        'text' : frame_text,
        'section' : frame_section,
    })

    full_respones = '' 

    for item in frames:
        full_respones += format_time(item['start']) + ','
        full_respones += format_time(item['end']) + ','
        full_respones += item['text'] + ','
        full_respones += item['section'] + '\n\n'

    return full_respones

def create_text_image(text, font_path, font_size=24):
        '''A function for creating an image with text'''
        try:
            # Загружаем шрифт
            font = ImageFont.truetype(font_path, font_size)
        except Exception as e:
            st.error(f"Ошибка загрузки шрифта: {e}")
            return None
        
        # Определяем размер текста
        image_width = 1050
        image_height = 100
        
        # Создаем изображение
        img = Image.new('RGB', (image_width, image_height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        # Рисуем текст
        draw.text((10, 10), text, font=font, fill=(0, 0, 0))
        return img

def process_song(model_response):
    """Process song text and generate structured prompts."""
    
     # Преобразуйте ответ в структурированный формат
    pattern = r"\*\*Frame\*\*:\s+(.+?)\n\*\*Part of the song\*\*:\s+(.+?)\n\*\*Text\*\*:\s+(.+?)\n\*\*Prompt for the image generating model\*\*:\s+(.+?)(?=\n\n|\Z)"
    matches = re.findall(pattern, model_response, re.S)

    
    prompts_translated = []
    for match in matches:
        shot = match[0].strip()
        part = match[1].strip()
        lyrics = match[2].strip()
        prompt = match[3].strip()
        prompts_translated.append({"lyrics": lyrics, 'part': part, 'shot': shot, "prompt": prompt, "image_url": [], 'effect': None, 'effects_next': None})

    return prompts_translated


class Video:
    """Video object"""

    def __init__(prompts_data, selected_images, txt_file, font, font_path, selected_color_1, selected_color_2, audio_type, language):
        self.selected_images = selected_images
        self.txt_file = txt_file
        self.font = font
        self.font_path = font_path
        self.selected_color_1 = selected_color_1
        self.selected_color_2 = selected_color_2
        self.audio_type = audio_type
        self.language = language

        time = [] # список временных меток кадров 
        effects_next = [] # список выбранных эффектов перехода на следующее видео 
        effects = [] # список выбранных эффектов поверх видео 
        
        # Перевод времени из формата XX:XX:XX в секунды и получение название эффекта перехода 
        for i in range(len(prompts_data)):
            effects_next.append(prompts_data[i]['effects_next'])
            effects.append(prompts_data[i]['effect'])
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
                
        self.time = time
        self.effects_next = effects_next
        self.effects = effect
        self.videos = []

        self.video_path = "video/video.mp4"
        self.video_with_audio_path = "video/video_with_audio.mp4"

    def get_video_duration(video_file):
        """Get video duration"""
        result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", video_file], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return float(result.stdout)
        
    def create():
        """Create video from images"""
        for image_path, t , effect in zip(self.selected_images, self.time, self.effects):  

            payload = {
                'image_path': image_path,
                'duration': t[1] - t[0]
            }
            response = requests.post("http://127.0.0.1:6000/process_images", json=payload)
            video_url = response.json().get('video_url')
    
            if effect:
                add_effect(video_url, effect)
            self.videos.append(video_url)

            
     
        filter_complex_parts = []
        input_files = []
        
        for i, video in enumerate(self.videos):
            input_files.extend(["-i", video])
            filter_complex_parts.append(
                f"[{i}:v]fade=t=in:st=0:d={fade_duration}[v{i}]"
            )
        
        video_streams = "".join(f"[v{i}]" for i in range(len(video_files)))
        filter_complex = ";".join(filter_complex_parts) + f";{video_streams}concat=n={len(video_files)}:v=1:a=0[outv]"
        
        command = [
            "ffmpeg",
            *input_files,
            "-filter_complex", filter_complex,
            "-map", "[outv]",  
            "-c:v", "libx264",
            "-preset", "fast",
            "-y", self.video_path
        ]

        # объединяем короткие видео в одно с эффектом Fade-in
        subprocess.run(command, shell=False, check=True)
    
        effect_next_time = []
        dd = 0
        for i in range(len(video_files) - 1):
            video_duration = get_video_duration(video_files[i])
            if effects_next[i]: 
                effect_next_time.append([effects_next[i], dd + float(video_duration)])    
                dd = 0
                
            else: 
                dd += float(video_duration)

        # добавление эффектов переходов 
        if len(effect_next_time):
    
            # Выходное видео сохраняется с тем же именем
            temp_file = "videos/temp.mp4"
        
            filter_complex = []
            inputs = [f'-i {base_video}']
            for i, dur in enumerate(effect_next_time):
                if dur[0]:
                    inputs.append(f'-i {dur[0]}')
        
            
            overlay_streams = []
        
            duration = 0 
            for i, dur in enumerate(effect_next_time):
                if dur[0]:
                    time = get_video_duration(dur[0])
                    if time > 3.0:
                        tr = f'tr{i}'
                        over = f'over{i}'
                        delay = duration + effect_next_time[i][1] - 2.0  
                        duration += dueffect_next_timerations[i][1]
                        filter_complex.append(
                            f'[{i+1}:v]setpts=PTS+{delay}/TB[{tr}]'
                        )
                        overlay_streams.append(tr)
                    else:
                        tr = f'tr{i}'
                        over = f'over{i}'
                        delay = duration + effect_next_time[i][1] - 0.6
                        duration += effect_next_time[i][1]
                        filter_complex.append(
                            f'[{i+1}:v]setpts=PTS+{delay}/TB[{tr}]'
                        )
                        overlay_streams.append(tr)   
                    
            base = '[0:v]'
            for i, over in enumerate(overlay_streams):
                output = f'base{i+1}' if i < len(overlay_streams) - 1 else 'v'
                filter_complex.append(f'{base}[{over}]overlay[{output}]')
                base = f'[{output}]'
            
            filter_complex_str = '; '.join(filter_complex)
            
            command = [
                'ffmpeg',
                *inputs,
                '-filter_complex', f'"{filter_complex_str}"',
                '-map', '[v]',
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-preset', 'fast',
                '-y', temp_file  # Перезаписываем исходный файл
            ]
            
            subprocess.run(' '.join(command), shell=True)
        
            os.replace(temp_file, self.video_path)

        def add_audio(audio_path):
            command = [
                'ffmpeg', 
                '-i', self.video_path,      # Видео файл
                '-i', audio_path,      # Обрезанный аудио файл
                '-c:v', 'copy',        # Копирование видео без изменений
                '-c:a', 'aac',         # Используем кодек AAC для аудио
                '-strict', 'experimental',  # Для использования нестандартных кодеков
                '-y',                  # Перезаписываем файл без подтверждения
                self.video_with_audio_path,  # Выходной файл
            ]
            
            # Запускаем команду
            subprocess.run(command)       

        def add_subtitels(subtitels_path):
            temp_file = "videos/temp.mp4"
            command = [
                "ffmpeg",
                "-i", self.video_path,
                "-vf", f"ass={subtitels_path}",
                '-y',
                'video/temp_video.mp4',
            ]
            
            os.replace(temp_file, self.video_path)
            
            # Запуск команды FFmpeg
            subprocess.run(command, check=True) 
                
        
class Subtitles:
    """Subtitles object"""
    
    def __init__(audio_path, lyrics_file, font, font_path, font_color_1, font_color_2, font_size):
        self.ttml_words = adiou_to_time_text(audio_path, lyrics_file)

        with open(lyrics_file, "r", encoding="utf-8") as f:
            text = f.read()
       
        self.text_language = detect_language(text[:999:]) 
        self.select_language = self.text_language

        self.lyrics = text
        self.translate_lyrics = ""
        
        self.output_file = "static/subtitles.ass"
        self.font = font
        self.font_path = font_path
        self.font_color_1 = font_color_1
        self.font_color_2 =font_color_2
        self.font_size = font_size
        

    def create():
        header = f"""[Script Info]
Title: Karaoke Lyrics
ScriptType: v4.00+
PlayResX: {1280}
PlayResY: {720}
Collisions: Normal
PlayDepth: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{self.font},{self.font_size},&H00{self.font_color_1},&H00{self.font_color_2},&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,3,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        events = []
        j = 0
        lines = self.lyrics.split("\n")

        if self.translate_lyrics == "":
            for line in lines:
                start_time, end_time = self.ttml_words[j]['start'] - 0.4, self.ttml_words[j + len(line['text'].split()) - 1]['end']
                duration_clip= end_time - start_time
                    
                karaoke_line = ""
                for i in range(j, j + len(line['text'].split())):
                    if i != j:
                        duration = (self.ttml_words[i]['end'] - self.ttml_words[i - 1]['end']) * 100  # duration in centiseconds
                        karaoke_line += f"{{\\kf{int(duration)}}}{self.ttml_words[i]['text']} "               
                    else:
                        duration = (self.ttml_words[i]['end'] - start_time) * 100  # duration in centiseconds
                        karaoke_line += f"{{\\fad(400,0)\\an2\\kf{int(duration)}}}{self.ttml_words[i]['text']} "
        
                events.append(f"Dialogue: 0,{format_time(start_time)},{format_time(end_time)},Default,,0,0,0,,{karaoke_line.strip()}")
                j += len(line['text'].split())
        
            with open(self.output_file, "w", encoding="utf-8") as f:
                f.write(header + "\n".join(events))

        else:
            translate_lyrics = translate_lyrics.split('\n')
            effects = [apply_fade_in, apply_scale_up, apply_word_fade_in, apply_word_fly_in, apply_letter_fly_in]  # Список эффектов
            
            for i, line in enumerate(lines):
                start_time, end_time = self.ttml_words[j]['start'] - 0.4, self.ttml_words[j + len(line['text'].split()) - 1]['end'] - 0.2
                effect_func = random.choice(effects)  # Выбираем случайный эффект
                effect_text = effect_func(translate_lyrics[i], self.font_size, self.font_path, start_time, end_time)  # Применяем эффект
                events.append(f"{effect_text}")
                j += len(line['text'].split())
        
            with open(self.output_file, "w", encoding="utf-8") as f:
                f.write(header + "\n".join(events))

    def translate(language):
        self.translate_lyrics = translate_text(self.lyrics, language)
        self.select_language = language
        



















    