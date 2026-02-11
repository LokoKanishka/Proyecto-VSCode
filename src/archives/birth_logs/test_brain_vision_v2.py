import ollama
import os


def test_spatial_intelligence() -> None:
    print("Probando vision espacial (modo navegacion)...")

    image_path = "/tmp/lucy_vision.jpg"
    if not os.path.exists(image_path):
        print("Error: no existe la captura. Ejecuta test_eyes.py primero.")
        return

    prompt = """
ACTUA COMO UN AGENTE DE NAVEGACION DE ESCRITORIO.
RESPONDE UNICAMENTE EN ESPANOL.

Analiza la imagen adjunta. Veras una GRILLA DE COORDENADAS (lineas rojas y cian) superpuesta sobre la pantalla.
- Las columnas estan marcadas con LETRAS (A, B, C...).
- Las filas estan marcadas con NUMEROS (1, 2, 3...).

TU MISION:
1. Ignora el contenido artistico. Centrate en la ubicacion.
2. Dime en que coordenadas (Ejemplo: A1, D4, F8) se encuentra la ventana activa o el cursor.
3. Si ves codigo Python, dime en que cuadrantes esta (ej: "El codigo ocupa desde B2 hasta E8").

Dame una lista de coordenadas clave para interactuar con esta pantalla.
"""

    try:
        print("Enviando imagen a Llava con instrucciones de navegacion...")
        response = ollama.chat(
            model="llava:latest",
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                    "images": [image_path],
                }
            ],
        )

        print("\nANALISIS ESPACIAL DE LUCY:")
        print("------------------------------------------------")
        print(response["message"]["content"])
        print("------------------------------------------------")

    except Exception as exc:
        print(f"Error: {exc}")


if __name__ == "__main__":
    test_spatial_intelligence()
