import os
import math
from PIL import Image

def generate_figurita_loop(input_path, output_dir, num_frames=120):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    img = Image.open(input_path).convert("RGBA")
    width, height = img.size
    pixels = img.load()
    
    # The figure is now tightly cropped, so regions are relative to the final size
    hair_region = height * 0.40
    tornado_region = height * 0.70
    
    for f in range(num_frames):
        new_img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        new_pixels = new_img.load()
        phase = (f / num_frames) * 2 * math.pi
        
        for y in range(height):
            if y < hair_region:
                intensity = (1.0 - (y / hair_region)) * 10.0
                shift_x = (math.sin(y * 0.04 + phase) * intensity + 
                           math.sin(y * 0.08 - phase * 0.5) * (intensity * 0.3))
                shift_y = math.sin(phase + y * 0.02) * 2.0
            elif y > tornado_region:
                intensity = ((y - tornado_region) / (height - tornado_region)) * 8.0
                shift_x = math.sin(y * 0.12 + phase * 2) * intensity
                shift_y = math.cos(phase) * 3.0
            else:
                shift_x = math.sin(phase) * 0.4
                shift_y = math.cos(phase * 0.5) * 1.0
            
            for x in range(width):
                src_x = int(x - shift_x)
                src_y = int(y - shift_y)
                
                if 0 <= src_x < width and 0 <= src_y < height:
                    r, g, b, a = pixels[src_x, src_y]
                    if a > 0:
                        pulse = 1.0 + math.sin(phase + (x+y)*0.01) * 0.05
                        r = min(255, int(r * pulse))
                        g = min(255, int(g * pulse))
                        b = min(255, int(b * pulse))
                        new_pixels[x, y] = (r, g, b, a)
        
        frame_path = os.path.join(output_dir, f"alt_fig_{f}.png")
        new_img.save(frame_path, "PNG")
        if f % 20 == 0: print(f"Figurita Progress: {f}/{num_frames}")

    print(f"✅ Figurita loop ready: {output_dir}")

if __name__ == "__main__":
    project_dir = "/home/xdie/.gemini/antigravity/scratch/Proyecto-VSCode"
    target_dir = os.path.join(project_dir, "assets/figurita_loop")
    source_img = os.path.join(project_dir, "alt_figurita_base.png")
    generate_figurita_loop(source_img, target_dir)
