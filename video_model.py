import os
import glob
import random
import subprocess
from DepthFlow.Scene import DepthScene
from DepthFlow.Motion import Presets, Components, Target
from flask import Flask, request, send_file, jsonify, url_for

# Set random seed for reproducibility (optional)
random.seed(random.randint(0, 2**32 - 1))

# Define a list of possible animations with randomized parameters
animation_options = [
    lambda: Presets.Vertical(intensity=0.6, smooth=True, loop=True, phase=0.25, steady=0.15, isometric=0.3),
    lambda: Presets.Horizontal(intensity=0.6, smooth=True, loop=True, phase=0.25, steady=0.15, isometric=0.3),
    # lambda: Components.Sine(target=Target.OffsetX, amplitude=random.uniform(0.3, 0.7), cycles=random.uniform(0.5, 1.5), phase=random.uniform(0, 1)),
    # lambda: Components.Cosine(target=Target.OffsetY, amplitude=random.uniform(0.3, 0.7), cycles=random.uniform(0.5, 1.5), phase=random.uniform(0, 1)),
    # lambda: Components.Triangle(target=Target.OffsetX, amplitude=random.uniform(0.3, 0.7), cycles=random.uniform(0.5, 1.5), phase=random.uniform(0, 1)),
    # lambda: Components.Triangle(target=Target.OffsetY, amplitude=random.uniform(0.3, 0.7), cycles=random.uniform(0.5, 1.5), phase=random.uniform(0, 1)),
    # lambda: Components.Sine(target=Target.Isometric, amplitude=random.uniform(0.3, 0.7), cycles=random.uniform(0.5, 1.5), phase=random.uniform(0, 1)),
    # lambda: Components.Cosine(target=Target.Zoom, amplitude=random.uniform(0.3, 0.7), cycles=random.uniform(0.5, 1.5), phase=random.uniform(0, 1)),
    lambda: Presets.Zoom(intensity=0.8, smooth=True, loop=True, phase=0.3),
    # lambda: Presets.Circle(intensity=random.uniform(0.5, 1.5), smooth=True, loop=True, phase=(random.uniform(0, 1), random.uniform(0, 1), random.uniform(0, 1))),
]

class MyAnimationScene(DepthScene):
    def __init__(self, animation=None, **kwargs):
        super().__init__(**kwargs)
        if animation:
            self.add_animation(animation)

# Flask app
app = Flask(__name__)

@app.route('/process_images', methods=['POST'])
def process_images():
    # Receive image paths from the request
    payload = request.get_json()
    image_path = payload.get('image_path', '')
    duration = float(payload.get('duration', 0))
    project_folder = payload.get('project_folder', '')
    
    # Ensure the temp videos folder exists
    videos_folder  = os.path.join(project_folder, 'videos')
    if not os.path.exists(videos_folder):
        os.makedirs(videos_folder)
    
    # Create a unique output video file name
    image_name = os.path.basename(image_path)
    video_name = os.path.join(videos_folder, f"{os.path.splitext(image_name)[0]}.mp4")

    
    # Randomly select an animation
    selected_animation = random.choice(animation_options)()
    
    # Create scene instance
    scene = MyAnimationScene(animation=selected_animation, backend="headless")
    scene.input(image=image_path)
    scene.main(
        output=video_name,
        fps=30,
        time=duration
    )
    print(f"Processed {image_path} with animation {type(selected_animation).__name__} and saved to {video_name}")
    
    
    return jsonify({'video_url': video_name })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=6000)
