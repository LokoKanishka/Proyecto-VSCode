import os
import math
from PIL import Image

def generate_cinematic_pure_loop(input_path, output_dir, num_frames=120):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    img = Image.open(input_path).convert("RGBA")
    width, height = img.size
    pixels = img.load()
    
    # Cinematic Segments
    hair_region = height * 0.45
    tornado_region = height * 0.70
    
    for f in range(num_frames):
        new_img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        new_pixels = new_img.load()
        
        # Perfect Loop Phase (f/120)
        phase = (f / num_frames) * 2 * math.pi
        
        for y in range(height):
            # Complex Fluid Animation
            if y < hair_region:
                # Organic Hair Waves (Multi-frequency)
                intensity = (1.0 - (y / hair_region)) * 14.0
                shift_x = (math.sin(y * 0.04 + phase) * intensity + 
                           math.sin(y * 0.08 - phase * 0.5) * (intensity * 0.4))
                shift_y = math.sin(phase + y * 0.02) * 2.5
            elif y > tornado_region:
                # Bit Tornado Vortex
                intensity = ((y - tornado_region) / (height - tornado_region)) * 12.0
                shift_x = math.sin(y * 0.12 + phase * 2) * intensity
                shift_y = math.cos(phase) * 3.5
            else:
                # Core Displacement (Breathing)
                shift_x = math.sin(phase) * 0.6
                shift_y = math.cos(phase * 0.5) * 1.5
            
            for x in range(width):
                src_x = int(x - shift_x)
                src_y = int(y - shift_y)
                
                if 0 <= src_x < width and 0 <= src_y < height:
                    r, g, b, a = pixels[src_x, src_y]
                    if a > 0:
                        # Spectral Glow Pulse (Looped)
                        pulse = 1.0 + math.sin(phase + (x+y)*0.01) * 0.08
                        r = min(255, int(r * pulse))
                        g = min(255, int(g * pulse))
                        b = min(255, int(b * pulse))
                        new_pixels[x, y] = (r, g, b, a)
        
        frame_path = os.path.join(output_dir, f"alt_pure_{f}.png")
        new_img.save(frame_path, "PNG")
        if f % 20 == 0: print(f"Processing Pure Loop: {f}/{num_frames}")

    print(f"✅ 5-Second Pure Loop sequence ready: {output_dir}")

if __name__ == "__main__":
    project_dir = "/home/xdie/.gemini/antigravity/scratch/Proyecto-VSCode"
    target_dir = os.path.join(project_dir, "assets/pure_loop_alt")
    source_img = os.path.join(project_dir, "alt_pure_transparent.png")
    generate_cinematic_pure_loop(source_img, target_dir)
