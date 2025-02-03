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


# token for yandex translate 
IAM_TOKEN = 'AQVNzbPNKEeoixhfHLFZavVdM66AJ23Ow4zFkKwQ'
folder_id = 'b1gbfto7jeu1ghuc8heq'
target_language = 'en'

URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"


def translate_text(texts: str) -> str:
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
        "targetLanguageCode": target_language,
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
    
    command = [
        "ffmpeg",
        # "-stream_loop", "-1",
        "-i", effect,
        "-i", video,
        "-filter_complex", "[0:v]chromakey=0x00FF00:0.2:0.3[cleaned]; [cleaned]scale=1280:720[scaled]; [1:v][scaled]overlay=0:0:shortest=1",
        "-c:v", "libx264",
        "-crf", "23",
        "-preset", "veryfast",
        "-y", temp_file
    ]

    subprocess.run(command, check=True)  
    os.replace(temp_file, video)



# Функция для создания команды FFmpeg
def concatenate_videos(video_files, output_file, overlay_videos, short_overlay_videos, effects_next):
    print('Создание видео путем склеивания без переходов')
    
    with open("file_list.txt", "w") as f:
        for video in video_files:
            f.write(f"file '{video}'\n")
    
    command = [
        'ffmpeg',
        '-f', 'concat',
        '-safe', '0',
        '-i', 'file_list.txt',
        '-c', 'copy',
        '-y', output_file
    ]
    
    print(' '.join(command))
    try:
        subprocess.run(command, shell=False, check=True)
        print("Видео успешно склеены!")
    except subprocess.CalledProcessError as e:
        print("Ошибка при склеивании видео:", e)

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
        apply_chromakey_with_overlays(output_file, overlay_videos, short_overlay_videos, durations,)


def get_video_duration(video_file):
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", video_file], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return float(result.stdout)




def apply_chromakey_with_overlays(base_video, overlay_videos, short_overlay_videos, durations):
    # Выходное видео сохраняется с тем же именем
    temp_file = "videos/temp.mp4"

    filter_complex = []
    inputs = [f'-i {base_video}']
    for i, dur in enumerate(durations):
        if dur[0] == 1:
            inputs.append(f'-i {random.choice(overlay_videos)}')
        elif dur[0] == 2: 
            inputs.append(f'-i {random.choice(short_overlay_videos)}')

    
    overlay_streams = []

    duration = 0 
    for i, dur in enumerate(durations):
        if dur[0] == 1:
            tr = f'tr{i}'
            over = f'over{i}'
            delay = duration + durations[i][1] - 2.5  
            duration += durations[i][1]
            filter_complex.append(
                f'[{i+1}:v]chromakey=0x00FF00:0.1:0.2,setpts=PTS+{delay}/TB[{tr}]'
            )
            overlay_streams.append(tr)
        elif dur[0] == 2:
            tr = f'tr{i}'
            over = f'over{i}'
            delay = duration + durations[i][1] - 0.6
            duration += durations[i][1]
            filter_complex.append(
                f'[{i+1}:v]chromakey=0x00FF00:0.1:0.2,setpts=PTS+{delay}/TB[{tr}]'
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
