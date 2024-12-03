from moviepy.editor import ImageClip, CompositeVideoClip, vfx, TextClip
from moviepy.video.tools.segmenting import findObjects
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from  numpy import ndarray
import math
import textwrap
from typing import Union

from PIL import Image, ImageDraw, ImageFont
from textwrap import wrap
import numpy as np

def create_text_image(text: str, font: str = "arial.ttf", font_size: int = 180, color: str = 'white', max_width: int = 400, angle: float = 0.0, align: str = 'center', padding: int = 10) -> np.array:
    '''
    Creates an image of text with a transparent background, preserving newline characters.

    Parameters:
    -----------
    text : str
        The text that is used to create an image, with newline characters (\n) for line breaks.
    font : str
        The path for .ttf or .otf file format.
    font_size : int
        The size of the font.
    color : str
        The color of the font.
    max_width : int
        The maximum width of the text area.
    angle : float
        The rotation angle in degrees.
    align : str
        Alignment of the text: 'center' or 'left'.
    padding : int
        Padding around the text.

    Returns:
    --------
    np.array
        NumPy array of the image of text with a transparent background.
    '''
    font = ImageFont.truetype(font, font_size)
    lines = text.split('\n')  # Split text into lines based on newline characters

    # Wrap each line if it exceeds max_width
    wrapped_lines = []
    for line in lines:
        words = line.split()
        current_line = ""
        for word in words:
            if font.getbbox(current_line + word)[2] - font.getbbox(current_line)[0] <= max_width - 2 * padding:
                current_line += word + " "
            else:
                wrapped_lines.append(current_line.strip())
                current_line = word + " "
        wrapped_lines.append(current_line.strip())

    # Calculate the total height of the image
    total_height = len(wrapped_lines) * font_size + 2 * padding

    # Create a new image with the calculated dimensions
    image = Image.new('RGBA', (max_width, total_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    y_text = padding
    for line in wrapped_lines:
        # Calculate the bounding box for each line
        bbox = font.getbbox(line)
        line_width = bbox[2] - bbox[0]
        line_height = bbox[3] - bbox[1]

        if align == 'center':
            # Calculate the position to center the text horizontally
            x_text = (max_width - line_width) / 2
        elif align == 'left':
            # Set the x-coordinate for left alignment with padding
            x_text = padding
        else:
            raise ValueError("Invalid align value. Choose 'center' or 'left'.")

        # Draw the line on the image
        draw.text((x_text, y_text), line, font=font, fill=color)
        y_text += font_size  # Move to the next line

    # Rotate the image if necessary
    rotated_image = image.rotate(angle, expand=True)

    # Return the NumPy array of the image
    return np.array(rotated_image)
    

def rotate_to_left(clip: ImageClip, duration: float, rotate_duration: float=0.5, size: tuple[int, int] =(480, 848), font_size: int =40) -> ImageClip:
    """
    Animation of rotation and movement around a circle.

    Parameters:
    -----------
    clip : ImageClip
        The text that will be rotated
    duration : flaot
        The total duration of the animation
    rotate_duration: float
        The time it takes for the turn to take place.
    size : tuple[int, int]
        The size of ImageCLip 

    Returns:
    --------
    ImageClip containing an animation of text rotation
    """

    # animation of text rotation
    rotated_clip = clip.fx(
        vfx.rotate,
        lambda t: min(89 * t / rotate_duration, 89),  
        expand=True
    ).set_duration(duration)
    
    # animation of text moving
    radius = size[1] / 6  # radius
    center_x = size[0] / 2
    center_y = size[1] / 2

    def circular_position(t):
        """A function for moving around a circle."""
        if t < rotate_duration:
            angle = -math.pi / 2 * t / rotate_duration
        else:
            angle = -math.pi / 2  

        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)
        return (x - rotated_clip.w / 2, y - rotated_clip.h / 2)

    rotated_clip = rotated_clip.set_position(circular_position)
    return rotated_clip


def animate_words_pop_up(text: str, ttml: dict[float, Union[float, str]], duration: float, font: str ="arial.ttf", font_color: str ='white', word_duration: float = 0.2, line_spacing: int = 40, initial_scale: float = 2.0, size: tuple[int, int] =(480, 848), font_size: int =40) -> CompositeVideoClip:
    '''
    Creates animation jumping out words

    Parameters:
    -----------
    text : str
        The text that be animated
    ttml : list[dict[str, Union[float, str]]]:
        A list of dictionaries, where each dictionary represents a one word from the song
        with the following keys:
        - 'start': flost - The start time of the subtitle.
        - 'end': float - The end time of the subtitle. If not specified, it will be set
          to the start time of the next subtitle.
        - 'text': str - The text content of the subtitle
    duration : flaot
        The duration of the entire animated 
    font : str
        The path for .ttf or .otf file format
    font_color : str
        The color of the text
    word_duration : float
        The duration of word animation
    line_spasing : in
        Vertical distance between words 
    initial_scale : float 
        How many times to increase a word before decreasing it
    size : tuple[int, int]
        Size of result video
    
    Returns:
    --------
    Video with animated text
    '''

    words = text.split()
    word_clips = []
    current_y = size[1] // 16  
    current_w = size[0] // 4  

    for i, word in enumerate(words):
        word_image = create_text_image(word, font=font, color=font_color, max_width=size[0], font_size=font_size, align='left')
        word_clip = ImageClip(word_image).set_duration(duration)
        h = word_clip.h
        
        word_clip = word_clip.set_position((current_w, current_y)).set_start(ttml[i]['start'] - ttml[0]['start'])

        scale = initial_scale
        word_clip = word_clip.resize(lambda t: scale - (initial_scale - 1) * t / word_duration if t < word_duration else 1.0)
        
        word_clips.append(word_clip)
        
        current_y += h // 2 + line_spacing

    animated_clip = CompositeVideoClip(word_clips, size=size)
    return animated_clip.set_duration(duration)


def animate_cross(text: str, ttml: dict[float, Union[float, str]], duration: float, font: str ="arial.ttf", font_color: str ='white', word_duration=0.2, line_spacing=10, size: tuple[int, int] =(480, 848),  font_size: int =40) -> CompositeVideoClip:
    '''
    Сreates a staggered word appearance animation

    Parameters:
    -----------
    text : str
        The text that be animated
    ttml : list[dict[str, Union[float, str]]]:
        A list of dictionaries, where each dictionary represents a one word from the song
        with the following keys:
        - 'start': flost - The start time of the subtitle.
        - 'end': float - The end time of the subtitle. If not specified, it will be set
          to the start time of the next subtitle.
        - 'text': str - The text content of the subtitle
    duration : flaot
        The duration of the entire animated 
    font : str
        The path for .ttf or .otf file format
    font_color : str
        The color of the text
    word_duration : float
        The duration of word animation
    line_spasing : int
        Vertical distance between words 
    size : tuple[int, int]
        Size of result video
    
    Returns:
    --------
    Video with animated text
    '''

    words = text.split()
    word_clips = []
    current_y = size[1] // 32  
    current_w = 10

    for i, word in enumerate(words):
        word_image = create_text_image(word, font=font, color=font_color, max_width=size[0], font_size=font_size, align='left')
        word_clip = ImageClip(word_image).set_duration(duration)

        if current_w == 10:
            current_w = size[0] // 2 
        else:
            current_w = 10        
        current_y += word_clip.h // 2 + line_spacing

        word_clip = word_clip.set_position((current_w, current_y)).set_start(ttml[i]['start'] - ttml[0]['start'])
        word_clip = word_clip.crossfadein(word_duration)

        word_clips.append(word_clip)

    animated_clip = CompositeVideoClip(word_clips, size=size)
    return animated_clip.set_duration(duration) 
        

def animate_words(text: str, ttml: dict[float, Union[float, str]], duration: float, font: str ="arial.ttf", font_color: str ='white', word_duration:float =0.5, line_spacing:int =10, size: tuple[int, int] =(480, 848), font_size: int =40) -> CompositeVideoClip:
    '''
    Creates an animation of the smooth appearance of words

    Parameters:
    -----------
    text : str
        The text that be animated
    ttml : list[dict[str, Union[float, str]]]:
        A list of dictionaries, where each dictionary represents a one word from the song
        with the following keys:
        - 'start': flost - The start time of the subtitle.
        - 'end': float - The end time of the subtitle. If not specified, it will be set
          to the start time of the next subtitle.
        - 'text': str - The text content of the subtitle
    duration : flaot
        The duration of the entire animated 
    font : str
        The path for .ttf or .otf file format
    font_color : str
        The color of the text
    word_duration : float
        The duration of word animation
    line_spasing : int
        Vertical distance between words 
    size : tuple[int, int]
        Size of result video
    
    Returns:
    --------
    Video with animated text
    '''
    
    words = text.split()
    word_clips = []
    current_y = 0 
    
    current_x = size[0] // 4


    for i, word in enumerate(words):
        word_image = create_text_image(word, font=font, color=font_color, max_width=size[0], font_size=font_size, align='left')
        word_clip = ImageClip(word_image).set_duration(duration)
        
        # word_clip = word_clip.resize((word_clip.w, word_clip.h))
        word_clip = word_clip.set_start(ttml[i]['start'] - ttml[0]['start']).set_position((current_x, current_y))
        
        word_clip = word_clip.crossfadein(word_duration)
        word_clips.append(word_clip)
        
        current_y += word_clip.h

    animated_clip = CompositeVideoClip(word_clips, size=size)
    return animated_clip.set_duration(duration)


def animate_left_angle(text: str, duration: float, ttml: dict[float, Union[float, str]] = None, font: str ="arial.ttf", font_color: str ='white', angle: int = 20, size=None,  font_size: int =40) -> ImageClip:
    '''
    Creates text at an 'angle' angle

    Parameters:
    -----------
    text : str
        The text that be animated
    ttml : list[dict[str, Union[float, str]]]:
        A list of dictionaries, where each dictionary represents a one word from the song
        with the following keys:
        - 'start': flost - The start time of the subtitle.
        - 'end': float - The end time of the subtitle. If not specified, it will be set
          to the start time of the next subtitle.
        - 'text': str - The text content of the subtitle
    duration : flaot
        The duration of the entire animated 
    font : str
        The path for .ttf or .otf file format
    font_color : str
        The color of the text
    angel : int 
        The angle at which the image is rotated.
    
    Returns:
    --------
    Video with animated text
    '''

    text_image = create_text_image(text, font=font, color=font_color, max_width=1080, angle=angle, font_size=font_size)
    clip = ImageClip(text_image).set_position('center').set_duration(duration)

    
    effect_duration = 0.2
    initial_scale = 0.2
    scale = initial_scale
    clip = clip.resize(lambda t: scale + (1 - initial_scale) * t / effect_duration if t < effect_duration else 1.0)

    return clip


def movie_latters(text: str, duration: float, ttml: dict[float, Union[float, str]] = None, font: str ="arial.ttf", size: tuple[int, int]=(480, 848), font_color:str = 'white',  font_size: int =40) -> CompositeVideoClip:
    '''
    Creates an animation of the appearance of words from letters that arrive one at a time

    Parameters:
    -----------
    text : str
        The text that be animated
    ttml : list[dict[str, Union[float, str]]]:
        A list of dictionaries, where each dictionary represents a one word from the song
        with the following keys:
        - 'start': flost - The start time of the subtitle.
        - 'end': float - The end time of the subtitle. If not specified, it will be set
          to the start time of the next subtitle.
        - 'text': str - The text content of the subtitle
    duration : flaot
        The duration of the entire animated 
    font : str
        The path for .ttf or .otf file format
    angel : int 
        The angle at which the image is rotated.
    size : tuple[int, int]
        Size of result video
    font_color : str
        The color of the text 
    
    Returns:
    --------
    Video with animated text
    '''

    text = text.replace(" ", "\n")

    txtClip = ImageClip(create_text_image(text=text, font=font, color=font_color, max_width=size[0], font_size=font_size))

    # Composite video clip для текста
    cvc = CompositeVideoClip([txtClip], size=size)

    # Вспомогательная функция для матрицы поворота
    rotMatrix = lambda a: np.array([[np.cos(a), np.sin(a)], [-np.sin(a), np.cos(a)]])

    # Функция для эффекта текста
    def effect1(screenpos, i, nletters):
        d = lambda t: 1.0 / (0.3 + t ** 8)
        a = i * np.pi / nletters
        v = rotMatrix(a).dot([-1, 0])
        if i % 2: v[1] = -v[1]
        return lambda t: screenpos + 400 * d(t) * rotMatrix(0.5 * d(t) * a).dot(v)

    # Разбиение текста на буквы
    letters = findObjects(cvc)

    # Функция для анимации текста
    def moveLetters(letters, funcpos):
        return [letter.set_pos(funcpos(letter.screenpos, i, len(letters)))
                for i, letter in enumerate(letters)]

    # Создание текстового эффекта
    text_effect_clip = CompositeVideoClip(
        moveLetters(letters, effect1),
        size=size
    ).set_duration(duration)

    return text_effect_clip
