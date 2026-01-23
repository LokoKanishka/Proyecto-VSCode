import os
from PIL import Image

def tight_crop_image(input_path, output_path):
    img = Image.open(input_path).convert("RGBA")
    alpha = img.getchannel('A')
    
    # Even more aggressive: threshold at 50 to clear noise
    alpha_threshold = alpha.point(lambda p: 255 if p > 50 else 0)
    bbox = alpha_threshold.getbbox()
    
    if bbox:
        # Add a tiny 10px padding for safety unless it hits boundary
        bbox = (max(0, bbox[0]-10), max(0, bbox[1]-10), 
                min(img.width, bbox[2]+10), min(img.height, bbox[3]+10))
                
        cropped_img = img.crop(bbox)
        # Final cleanup of low alpha pixels in the crop
        cropped_alpha = alpha.crop(bbox).point(lambda p: p if p > 30 else 0)
        cropped_img.putalpha(cropped_alpha)
        
        cropped_img.save(output_path, "PNG")
        print(f"✅ Ultra-Aggressive Tight-cropped saved to {output_path}")
        print(f"Original size: {img.size}, New size: {cropped_img.size}")
        return cropped_img.size
    else:
        print("❌ Error: Could not find bounding box.")
        return None

if __name__ == "__main__":
    project_dir = "/home/xdie/.gemini/antigravity/scratch/Proyecto-VSCode"
    source = os.path.join(project_dir, "alt_pure_transparent.png")
    target = os.path.join(project_dir, "alt_figurita_base.png")
    tight_crop_image(source, target)
