import os
import math
from PIL import Image

def generate_figurita_loop_fixed(input_path, output_dir, num_frames=120):
    print(f"Procesando: {input_path}...")
    if not os.path.exists(output_dir): os.makedirs(output_dir)
    
    try:
        img = Image.open(input_path).convert("RGBA")
    except FileNotFoundError:
        print(f"ERROR: No se encontró la imagen base: {input_path}")
        return

    width, height = img.size
    pixels = img.load()
    
    # --- CONFIGURACIÓN DE ZONAS (Ajusta estos porcentajes si es necesario) ---
    # Define dónde termina el pelo y empieza la frente
    HAIR_END_Y_PCT = 0.35  # El 35% superior es pelo
    # Define dónde terminan los pies y empieza solo el remolino base
    FEET_END_Y_PCT = 0.85  # El 15% inferior es remolino puro

    hair_threshold_y = height * HAIR_END_Y_PCT
    feet_threshold_y = height * FEET_END_Y_PCT

    print(f"Dimensiones: {width}x{height}")
    print(f"Zona Pelo hasta Y={int(hair_threshold_y)}")
    print(f"Zona Cuerpo Firme entre Y={int(hair_threshold_y)} y Y={int(feet_threshold_y)}")
    print(f"Zona Tornado debajo de Y={int(feet_threshold_y)}")

    for f in range(num_frames):
        # Crear lienzo transparente para este frame
        new_img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        new_pixels = new_img.load()
        
        # Fase de la animación (0 a 2pi para un ciclo completo)
        phase = (f / num_frames) * 2 * math.pi
        
        # Recorremos cada píxel de la imagen DESTINO (x, y)
        # y calculamos de dónde tomar el color de la imagen ORIGEN (src_x, src_y)
        for y in range(height):
            # --- LÓGICA DE MOVIMIENTO POR ZONAS ---
            shift_x = 0.0
            shift_y = 0.0

            if y < hair_threshold_y:
                # ZONA SUPERIOR: PELO (Movimiento orgánico suave)
                # La intensidad aumenta cuanto más arriba estamos
                intensity = (1.0 - (y / hair_threshold_y)) * 6.0
                # Ondulación horizontal lenta
                shift_x = math.sin(y * 0.03 + phase) * intensity
                # Ligero movimiento vertical tipo "flotar"
                shift_y = math.cos(phase * 0.7) * 1.5

            elif y > feet_threshold_y:
                # ZONA INFERIOR: TORNADO/REMOLINO (Movimiento intenso y rápido)
                # La intensidad aumenta drásticamente hacia abajo
                ratio_tornado = (y - feet_threshold_y) / (height - feet_threshold_y)
                intensity = ratio_tornado * 12.0 
                # Frecuencia alta para efecto turbulento
                shift_x = math.sin(y * 0.15 + phase * 3) * intensity
                # Compresión/expansión vertical
                shift_y = math.sin(y * 0.1 + phase * 2) * 3.0
                
            else:
                # ZONA CENTRAL: ROSTRO, CUERPO, PIERNAS
                # CRUCIAL: Forzamos el desplazamiento a cero. FIRMEZA TOTAL.
                shift_x = 0.0
                shift_y = 0.0
            
            # --- APLICACIÓN DEL DESPLAZAMIENTO ---
            for x in range(width):
                # Calculamos la coordenada origen inversa
                src_x = int(x - shift_x)
                src_y = int(y - shift_y)
                
                # Verificamos que la coordenada origen esté dentro de la imagen
                if 0 <= src_x < width and 0 <= src_y < height:
                    r, g, b, a = pixels[src_x, src_y]
                    
                    # --- CORRECCIÓN 3: ELIMINAR ZONA NEGRA INFERIOR ---
                    # Si el píxel origen es totalmente opaco (a>250) Y es casi negro (rgb < 15)
                    # Lo consideramos fondo indeseado y NO lo copiamos.
                    is_near_black = (r < 15 and g < 15 and b < 15)
                    if a > 250 and is_near_black:
                        # Al no hacer nada aquí, el píxel (x,y) de new_pixels 
                        # permanece transparente (0,0,0,0) como se inicializó.
                        continue 

                    # Si no es fondo negro y tiene algo de opacidad, lo copiamos
                    if a > 0:
                        # Opcional: Añadir un ligero pulso de color solo a las partes móviles
                        pulse = 1.0
                        if shift_x != 0 or shift_y != 0:
                             pulse = 1.0 + math.sin(phase + y * 0.05) * 0.04

                        new_pixels[x, y] = (
                            min(255, int(r * pulse)),
                            min(255, int(r * pulse)), # Gemini suggested pulse on all channels
                            min(255, int(r * pulse)), # Fixing the user provided code which had r*pulse for g and b too
                            a
                        )
                        # Correction: The user script had `min(255, int(r * pulse))` for all channels. 
                        # I will use the original r, g, b but pulsing them.
                        new_pixels[x, y] = (
                            min(255, int(r * pulse)),
                            min(255, int(g * pulse)),
                            min(255, int(b * pulse)),
                            a
                        )
        
        # Guardar frame
        output_path = os.path.join(output_dir, f"alt_fig_{f}.png")
        new_img.save(output_path, "PNG")
        if f % 20 == 0: print(f"Generado frame {f}/{num_frames}")

    print("¡Generación de bucle corregido completada!")

if __name__ == "__main__":
    project_dir = "/home/xdie/Proyecto-VSCode"
    input_file = os.path.join(project_dir, "alt_figurita_base.png") 
    output_folder = os.path.join(project_dir, "assets/figurita_loop_fixed")
    
    generate_figurita_loop_fixed(input_file, output_folder, num_frames=120)
