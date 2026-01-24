import ollama


def test_vision_intelligence() -> None:
    print("Probando analisis visual con Llava...")

    image_path = "/tmp/lucy_vision.jpg"

    try:
        print(f"Enviando {image_path} a llava:latest...")
        response = ollama.chat(
            model="llava:latest",
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Describe brevemente que ves en esta captura de pantalla. "
                        "Si ves una grilla roja/cian, menciona en que cuadrante "
                        "(ej: A1, B2) hay ventanas abiertas."
                    ),
                    "images": [image_path],
                }
            ],
        )

        print("\nLUCY VE:")
        print(response["message"]["content"])

    except Exception as exc:
        print(f"Error visual: {exc}")


if __name__ == "__main__":
    test_vision_intelligence()
