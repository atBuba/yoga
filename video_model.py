import argparse
import json
import os
import random
from datetime import datetime
from pathlib import Path
from diffusers.utils import logging
import imageio
import numpy as np
import safetensors.torch
import torch
import torch.nn.functional as F
from PIL import Image
from transformers import T5EncoderModel, T5Tokenizer
from ltx_video.models.autoencoders.causal_video_autoencoder import CausalVideoAutoencoder
from ltx_video.models.transformers.symmetric_patchifier import SymmetricPatchifier
from ltx_video.models.transformers.transformer3d import Transformer3DModel
from ltx_video.pipelines.pipeline_ltx_video import LTXVideoPipeline
from ltx_video.schedulers.rf import RectifiedFlowScheduler
from ltx_video.utils.conditioning_method import ConditioningMethod
from flask import Flask, request, send_file, jsonify, url_for, send_from_directory
import threading

app = Flask(__name__)

# Global variables to hold the models
pipeline = None
MAX_HEIGHT = 720
MAX_WIDTH = 1280
MAX_NUM_FRAMES = 257

def load_models(ckpt_dir):
    # Load VAE
    vae_dir = ckpt_dir / "vae"
    vae_ckpt_path = vae_dir / "vae_diffusion_pytorch_model.safetensors"
    vae_config_path = vae_dir / "config.json"
    with open(vae_config_path, "r") as f:
        vae_config = json.load(f)
    vae = CausalVideoAutoencoder.from_config(vae_config)
    vae_state_dict = safetensors.torch.load_file(vae_ckpt_path)
    vae.load_state_dict(vae_state_dict)
    if torch.cuda.is_available():
        vae = vae.cuda()
    vae = vae.to(torch.bfloat16)
    
    # Load UNet
    unet_dir = ckpt_dir / "unet"
    unet_ckpt_path = unet_dir / "unet_diffusion_pytorch_model.safetensors"
    unet_config_path = unet_dir / "config.json"
    transformer_config = Transformer3DModel.load_config(unet_config_path)
    transformer = Transformer3DModel.from_config(transformer_config)
    unet_state_dict = safetensors.torch.load_file(unet_ckpt_path)
    transformer.load_state_dict(unet_state_dict, strict=True)
    if torch.cuda.is_available():
        transformer = transformer.cuda()
    
    # Load Scheduler
    scheduler_dir = ckpt_dir / "scheduler"
    scheduler_config_path = scheduler_dir / "scheduler_config.json"
    scheduler_config = RectifiedFlowScheduler.load_config(scheduler_config_path)
    scheduler = RectifiedFlowScheduler.from_config(scheduler_config)
    
    # Load Text Encoder and Tokenizer
    text_encoder = T5EncoderModel.from_pretrained("PixArt-alpha/PixArt-XL-2-1024-MS", subfolder="text_encoder")
    if torch.cuda.is_available():
        text_encoder = text_encoder.to("cuda")
    tokenizer = T5Tokenizer.from_pretrained("PixArt-alpha/PixArt-XL-2-1024-MS", subfolder="tokenizer")
    
    # Create Pipeline
    submodel_dict = {
        "transformer": transformer,
        "vae": vae,
        "scheduler": scheduler,
        "text_encoder": text_encoder,
        "tokenizer": tokenizer,
        "patchifier": SymmetricPatchifier(patch_size=1)
    }
    p = LTXVideoPipeline(**submodel_dict)
    if torch.cuda.is_available():
        p = p.to("cuda")
    return p

def load_image_to_tensor_with_resize_and_crop(image, target_height=512, target_width=768):
    image = image.convert("RGB")
    input_width, input_height = image.size
    aspect_ratio_target = target_width / target_height
    aspect_ratio_frame = input_width / input_height
    if aspect_ratio_frame > aspect_ratio_target:
        new_width = int(input_height * aspect_ratio_target)
        new_height = input_height
        x_start = (input_width - new_width) // 2
        y_start = 0
    else:
        new_width = input_width
        new_height = int(input_width / aspect_ratio_target)
        x_start = 0
        y_start = (input_height - new_height) // 2
    
    image = image.crop((x_start, y_start, x_start + new_width, y_start + new_height))
    image = image.resize((target_width, target_height))
    frame_tensor = torch.tensor(np.array(image)).permute(2, 0, 1).float()
    frame_tensor = (frame_tensor / 127.5) - 1.0
    return frame_tensor.unsqueeze(0).unsqueeze(2)

def calculate_padding(source_height, source_width, target_height, target_width):
    pad_height = target_height - source_height
    pad_width = target_width - source_width
    pad_top = pad_height // 2
    pad_bottom = pad_height - pad_top
    pad_left = pad_width // 2
    pad_right = pad_width - pad_left
    return (pad_left, pad_right, pad_top, pad_bottom)

def generate_video(models, input_image, prompt, seed, height, width, num_frames, frame_rate):
    global pipeline
    pipeline = models
    generator = torch.manual_seed(seed)
    sample = {
        "prompt": prompt,
        "negative_prompt": "worst quality, inconsistent motion, blurry, jittery, distorted",
        "media_items": input_image,
    }
    images = pipeline(
        num_inference_steps=40,
        num_images_per_prompt=1,
        guidance_scale=3,
        generator=generator,
        output_type="pt",
        height=height,
        width=width,
        num_frames=num_frames,
        frame_rate=frame_rate,
        **sample,
        is_video=True,
        vae_per_channel_normalize=True,
        conditioning_method=ConditioningMethod.FIRST_FRAME,
    ).images

    
    return images


# Route to serve video files
@app.route('/videos/<filename>')
def serve_video(filename):
    return send_from_directory('videos', filename)

# Route to generate video
@app.route('/generate_video', methods=['POST'])
def generate_video_api():
    global pipeline
    if pipeline is None:
        return jsonify({'error': 'Models not loaded'}), 500

    prompt = request.form.get('prompt')
    seed = int(request.form.get('seed', 42))
    height = int(request.form.get('height', 512))
    width = int(request.form.get('width', 768))
    num_frames = int(request.form.get('num_frames', 121))
    frame_rate = int(request.form.get('frame_rate', 25))
    output_path = request.form.get('output_path', 'output_video.mp4')

    if 'image' not in request.files:
        return jsonify({'error': 'No image part'}), 400
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No selected image'}), 400
    if file:
        try:
            image = Image.open(file.stream)
            input_image = load_image_to_tensor_with_resize_and_crop(image, height, width)
            height_padded = ((height - 1) // 32 + 1) * 32
            width_padded = ((width - 1) // 32 + 1) * 32
            padding = calculate_padding(height, width, height_padded, width_padded)
            input_image = F.pad(input_image, padding, mode="constant", value=-1)
            images = generate_video(pipeline, input_image, prompt, seed, height_padded, width_padded, num_frames, frame_rate)
            pad_left, pad_right, pad_top, pad_bottom = padding
            pad_bottom = -pad_bottom
            pad_right = -pad_right
            if pad_bottom == 0:
                pad_bottom = images.shape[3]
            if pad_right == 0:
                pad_right = images.shape[4]
            images = images[:, :, :num_frames, pad_top:pad_bottom, pad_left:pad_right]
            video_np = images[0].permute(1, 2, 3, 0).cpu().float().numpy()  # Convert to float32
            video_np = (video_np * 255).astype(np.uint8)
            video_path = os.path.join('videos', output_path)
            with imageio.get_writer(video_path, fps=frame_rate) as writer:
                for frame in video_np:
                    writer.append_data(frame)
            return jsonify({'video_url': url_for('serve_video', filename=output_path)})
        except Exception as e:
            print(f'Error generating video: {str(e)}')
            return jsonify({'error': f'Error generating video: {str(e)}'}), 500
            
if __name__ == "__main__":
    # Load models once
    parser = argparse.ArgumentParser()
    parser.add_argument("--ckpt_dir", type=str, required=True)
    args = parser.parse_args()
    models = load_models(Path(args.ckpt_dir))
    pipeline = models
    # Run Flask app
    app.run(host="0.0.0.0", port=6000, use_reloader=False, debug=True)