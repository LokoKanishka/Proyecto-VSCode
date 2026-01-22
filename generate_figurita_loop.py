import os
import math
import random
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance

# --- CONFIGURACIÓN DE ALTA RESOLUCIÓN (TIGHT) ---
TARGET_HEIGHT = 900 

def resize_high_quality(img, target_h):
    aspect_ratio = img.width / img.height
    target_w = int(target_h * aspect_ratio)
    return img.resize((target_w, target_h), Image.Resampling.LANCZOS)

def generate_figurita_loop(input_path, output_dir, num_frames=120):
    if not os.path.exists(output_dir): os.makedirs(output_dir)
    
    print("👻 Iniciando Protocolo de Aislamiento Espectral...")
    
    # 1. Carga y Resize
    original = Image.open(input_path).convert("RGBA")
    img = resize_high_quality(original, TARGET_HEIGHT)
    
    # Convertir a Numpy
    base_arr = np.array(img)
    height, width, _ = base_arr.shape
    
    # --- MÁSCARA RADIAL DE AISLAMIENTO ---
    print("   >> Aplicando máscara de vacío...")
    Y_coords, X_coords = np.indices((height, width))
    cy, cx = height / 2, width / 2 # Centro
    
    dist_from_center = np.sqrt((X_coords - cx)**2 + (Y_coords - cy)**2)
    max_dist = np.sqrt(cx**2 + cy**2)
    
    tightness = 1.8 
    radial_mask = 1.0 - np.clip(dist_from_center / (max_dist / tightness), 0.0, 1.0)
    radial_mask = np.sin(radial_mask * math.pi / 2) 

    base_arr[:, :, 3] = (base_arr[:, :, 3] * radial_mask).astype(np.uint8)

    # --- PREPARACIÓN DE FÍSICA ---
    hair_region = height * 0.38
    tornado_region = height * 0.68
    
    print(f"🌊 Generando 120 cuadros espectrales ({width}x{height})...")

    for f in range(num_frames):
        phase = (f / num_frames) * 2 * math.pi
        
        intensity_map = np.zeros((height, width))
        mask_hair = Y_coords < hair_region
        mask_tornado = Y_coords > tornado_region
        
        intensity_map[mask_hair] = (1.0 - (Y_coords[mask_hair] / hair_region)) * 15.0
        dist_torso = (Y_coords[mask_tornado] - tornado_region) / (height - tornado_region)
        intensity_map[mask_tornado] = dist_torso * 8.0
        
        shift_x = np.zeros((height, width))
        shift_y = np.zeros((height, width))
        
        shift_x[mask_hair] = np.sin(Y_coords[mask_hair]*0.02 + phase) * intensity_map[mask_hair]
        shift_y[mask_hair] = np.cos(phase + Y_coords[mask_hair]*0.03) * 3.0
        
        shift_x[mask_tornado] = np.sin(Y_coords[mask_tornado]*0.05 + phase) * intensity_map[mask_tornado]
        shift_x[mask_tornado] += np.cos(Y_coords[mask_tornado]*0.1 - phase*2) * (intensity_map[mask_tornado]*0.5)
        shift_y[mask_tornado] = math.sin(phase) * 2.0
        
        mask_body = ~(mask_hair | mask_tornado)
        shift_x[mask_body] = math.cos(phase) * 0.8
        shift_y[mask_body] = math.sin(phase*0.5) * 1.5
        
        src_x = np.clip((X_coords - shift_x).astype(int), 0, width-1)
        src_y = np.clip((Y_coords - shift_y).astype(int), 0, height-1)
        
        new_frame = base_arr[src_y, src_x]
        
        alpha_mask = new_frame[:, :, 3] > 20
        if np.any(alpha_mask):
            new_frame[:, :, 0][alpha_mask] = (new_frame[:, :, 0][alpha_mask] * 0.8).astype(np.uint8)
            new_frame[:, :, 1][alpha_mask] = np.clip(new_frame[:, :, 1][alpha_mask] * 1.1, 0, 255)
            new_frame[:, :, 2][alpha_mask] = np.clip(new_frame[:, :, 2][alpha_mask] * 1.2, 0, 255)

        Image.fromarray(new_frame, 'RGBA').save(os.path.join(output_dir, f"alt_fig_{f}.png"))

def generate_hyper_burst_isolated(input_path, output_dir, frames=24):
    if not os.path.exists(output_dir): os.makedirs(output_dir)
    
    base_frame_path = os.path.join("assets/figurita_loop", "alt_fig_0.png")
    if not os.path.exists(base_frame_path):
        return
    
    bg_base = Image.open(base_frame_path).convert("RGBA")
    w, h = bg_base.size
    hand_x, hand_y = int(w * 0.3), int(h * 0.5)
    
    print(f"💥 Generando Burst Espectral ({frames} frames)...")
    
    particles = []
    num_particles = 250 
    for _ in range(num_particles):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(3.0, 20.0)
        life = random.uniform(0.4, 0.9)
        size = random.randint(3, 8)
        color = random.choice([(0, 255, 255), (0, 200, 255), (100, 255, 255)])
        particles.append({'x': hand_x, 'y': hand_y, 'vx': math.cos(angle) * speed, 'vy': math.sin(angle) * speed, 'vz': random.uniform(0.2, 0.6), 'life': life, 'max_life': life, 'size': size, 'color': color})

    for f in range(frames):
        overlay = Image.new("RGBA", (w, h), (0,0,0,0))
        draw = ImageDraw.Draw(overlay)
        progress = f / frames
        zoom = 1.0 + (progress**2 * 10.0)
        bg_dark = ImageEnhance.Brightness(bg_base).enhance(1.0 - progress*0.7)
        
        for p in particles:
            p['x'] += p['vx'] * zoom * 0.5
            p['y'] += p['vy'] * zoom * 0.5
            p['x'] += (p['x'] - w/2) * (p['vz'] * progress)
            p['y'] += (p['y'] - h/2) * (p['vz'] * progress)

            life_ratio = 1.0 - (f / (frames * p['max_life']))
            if life_ratio > 0:
                alpha = int(255 * life_ratio)
                draw_size = p['size'] * (1 + progress * 10)
                bbox = (p['x']-draw_size*1.5, p['y']-draw_size*1.5, p['x']+draw_size*1.5, p['y']+draw_size*1.5)
                if -50 < p['x'] < w+50 and -50 < p['y'] < h+50:
                    draw.ellipse((p['x']-draw_size/3, p['y']-draw_size/3, p['x']+draw_size/3, p['y']+draw_size/3), fill=(255,255,255,alpha))
                    draw.ellipse(bbox, fill=(p['color'][0], p['color'][1], p['color'][2], int(alpha*0.4)))

        final = Image.alpha_composite(bg_dark, overlay)
        final.save(os.path.join(output_dir, f"burst_{f}.png"), "PNG")

if __name__ == "__main__":
    input_img = "alt_figurita_base.png"
    if os.path.exists(input_img):
        generate_figurita_loop(input_img, "assets/figurita_loop")
        generate_hyper_burst_isolated(input_img, "assets/effect_bits")
