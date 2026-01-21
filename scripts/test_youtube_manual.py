#!/usr/bin/env python3
import os
import sys
import time

# Configurar path para encontrar el modulo lucy_agents
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

try:
    from lucy_agents.voice_actions import _run_youtube_action, _youtube_action_from_command
except ImportError as e:
    print(f"ERROR IMPORTANDO: {e}")
    print(
        "Asegurate de estar ejecutando esto desde la raiz del proyecto o que lucy_agents sea un paquete valido."
    )
    if "." not in sys.path:
        sys.path.append(".")
    try:
        from lucy_agents.voice_actions import _run_youtube_action, _youtube_action_from_command
    except ImportError:
        print("Fallo critico de importacion. Verifica la estructura de carpetas.")
        sys.exit(1)


def print_menu() -> None:
    print("\n--- SIMULADOR MANUAL DE LUCY (A37) ---")
    print("1. Simular accion directa (LLM dice: tool='youtube')")
    print("2. Simular intercepcion legacy (LLM dice: xdg-open ...)")
    print("3. Salir")


def test_direct() -> None:
    """Prueba la logica nueva pura."""
    cmd = input("  -> Tipo de comando (search / play): ").strip().lower()
    payload = input(f"  -> Argumento para '{cmd}' (query o ID/URL): ").strip()

    print(f"\n[TEST] Ejecutando _run_youtube_action('{cmd}', '{payload}')...")
    result = _run_youtube_action(cmd, payload)
    print(f"[RESULT] {result}")


def test_legacy() -> None:
    """Prueba que el sistema atrapa los xdg-open viejos."""
    print("  -> Escribe una URL de YouTube como si fueras el web_agent.")
    print("     Ejemplo: https://www.youtube.com/results?search_query=jazz")
    url = input("  -> URL: ").strip()

    dummy_command = f"xdg-open {url}"
    print(f"\n[TEST] Analizando comando legacy: '{dummy_command}'")

    action = _youtube_action_from_command(dummy_command)
    if action:
        yt_cmd, yt_payload = action
        print(
            f"[DETECTADO] Intercepcion exitosa -> Action: {yt_cmd}, Payload: {yt_payload}"
        )
        print("[TEST] Ejecutando accion interceptada...")
        result = _run_youtube_action(yt_cmd, yt_payload)
        print(f"[RESULT] {result}")
    else:
        print("[FALLO] No se detecto como accion de YouTube (URL invalida).")


def main() -> None:
    while True:
        print_menu()
        choice = input("Elige una opcion: ").strip()

        if choice == "1":
            test_direct()
        elif choice == "2":
            test_legacy()
        elif choice == "3":
            print("Cerrando simulador.")
            break
        else:
            print("Opcion invalida.")

        time.sleep(1)


if __name__ == "__main__":
    main()
