import os
import math
from PIL import Image

def generate_ripple_frames(input_path, output_dir, num_frames=12):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    img = Image.open(input_path).convert("RGBA")
    width, height = img.size
    
    # We'll apply the ripple mostly to the hair (top 45% of the image)
    hair_limit = int(height * 0.45)
    
    for f in range(num_frames):
        new_img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        pixels = img.load()
        new_pixels = new_img.load()
        
        # Phase shift for the sine wave based on frame index
        phase = (f / num_frames) * 2 * math.pi
        
        for y in range(height):
            # Amplitude varies by height: 0 at the body, max at the tips of the hair
            if y < hair_limit:
                # Intensity increases as we go up
                intensity = (1.0 - (y / hair_limit)) * 8.0
                # Sine wave based on Y position and frame phase
                shift_x = math.sin(y * 0.05 + phase) * intensity
            else:
                shift_x = 0
                
            for x in range(width):
                source_x = int(x - shift_x)
                if 0 <= source_x < width:
                    new_pixels[x, y] = pixels[source_x, y]
        
        frame_path = os.path.join(output_dir, f"alt_frame_{f}.png")
        new_img.save(frame_path, "PNG")
        print(f"Generated frame {f}: {frame_path}")

if __name__ == "__main__":
    # Ensure directory exists in the project
    target_dir = os.path.expanduser("~/Proyecto-VSCode/assets/anim_alt")
    source_img = os.path.expanduser("~/Proyecto-VSCode/alt_real.png")
    generate_ripple_frames(source_img, target_dir)
