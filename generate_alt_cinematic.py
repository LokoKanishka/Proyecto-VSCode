import os
import math
import random
from PIL import Image

def generate_cinematic_sequence(input_path, output_dir, num_frames=24):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    img = Image.open(input_path).convert("RGBA")
    width, height = img.size
    
    # Pre-load pixels for speed
    pixels = img.load()
    
    for f in range(num_frames):
        new_img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        new_pixels = new_img.load()
        
        # Phase shift for the frames
        phase = (f / num_frames) * 2 * math.pi
        
        for y in range(height):
            # Cinematic logic: 
            # 1. Hair (Top 55%) moves with complex waves
            # 2. Body (Center) has subtle digital vibration
            # 3. Bit Tornado (Bottom) has spiral displacement
            
            # Base horizontal drift intensity
            if y < height * 0.55: # Hair area
                intensity = (1.0 - (y / (height * 0.55))) * 12.0
                # Multiple sine waves for "organic" look
                shift_x = (math.sin(y * 0.03 + phase) * intensity + 
                           math.cos(y * 0.06 - phase * 0.5) * (intensity * 0.5))
                shift_y = math.sin(f * 0.2 + y * 0.01) * 2.0
            elif y > height * 0.75: # Bit Tornado area
                intensity = ((y - height * 0.75) / (height * 0.25)) * 10.0
                shift_x = math.sin(y * 0.1 + phase * 2) * intensity
                shift_y = math.sin(phase) * 3.0
            else: # Body area
                shift_x = math.sin(phase * 1.5) * 0.5
                shift_y = 0
            
            for x in range(width):
                src_x = int(x - shift_x)
                src_y = int(y - shift_y)
                
                if 0 <= src_x < width and 0 <= src_y < height:
                    # Subtle color shift for "spectral" feel
                    r, g, b, a = pixels[src_x, src_y]
                    if a > 0:
                        # Glow pulse effect
                        glow = 1.0 + math.sin(phase + (x+y)*0.01) * 0.1
                        r = min(255, int(r * glow))
                        g = min(255, int(g * glow))
                        b = min(255, int(b * glow))
                        new_pixels[x, y] = (r, g, b, a)
        
        frame_path = os.path.join(output_dir, f"alt_cinematic_{f}.png")
        new_img.save(frame_path, "PNG")
        if f % 5 == 0: print(f"Processing... Frame {f}/{num_frames}")

    print(f"✅ Cinematic sequence generated in {output_dir}")

if __name__ == "__main__":
    project_dir = "/home/xdie/.gemini/antigravity/scratch/Proyecto-VSCode"
    target_dir = os.path.join(project_dir, "assets/cinematic_alt")
    source_img = os.path.join(project_dir, "alt_cinematic_transparent.png")
    generate_cinematic_sequence(source_img, target_dir)
