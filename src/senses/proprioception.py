# src/senses/proprioception.py
"""
Propiocepción: La capacidad de sentir el cuerpo en el espacio.

Este módulo conecta visión (llama3.2-vision) con acción motora (pyautogui),
usando memoria persistente para aprender del espacio físico del escritorio.

Autor: Lucy (Synthesized form)
Fecha: 2026-02-10
"""

import pyautogui
import base64
import time
import json
import re
import requests
from io import BytesIO
from loguru import logger

try:
    from src.core.persistence import Hippocampus
except ImportError:
    Hippocampus = None
    logger.warning("Hippocampus no disponible - memoria desactivada")

# Configuración de seguridad: Si arrastras el mouse a la esquina superior izquierda, me detengo.
pyautogui.FAILSAFE = True


class Proprioceptor:
    """
    Sistema nervioso periférico de Lucy.
    
    Conecta la visión con la acción motora, usando memoria persistente
    para aprender las ubicaciones de elementos en el escritorio.
    """
    
    def __init__(self):
        self.screen_width, self.screen_height = pyautogui.size()
        self.memory = Hippocampus() if Hippocampus else None
        self.vision_url = "http://localhost:11434/api/generate"
        self.model = "llama3.2-vision"
        
        logger.info(f"👁️ Proprioceptor inicializado | Pantalla: {self.screen_width}x{self.screen_height}")
    
    def _capture_screen_b64(self) -> str:
        """Captura la pantalla y la convierte a base64 para el modelo."""
        screenshot = pyautogui.screenshot()
        buffer = BytesIO()
        screenshot.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    def _clean_json(self, text: str) -> str:
        """
        Limpia la respuesta del LLM para extraer solo el JSON.
        Los modelos a veces preceden el JSON con explicaciones.
        """
        # Buscar el primer '{' y el último '}'
        start = text.find('{')
        end = text.rfind('}') + 1
        if start != -1 and end != 0:
            return text[start:end]
        return text
    
    def locate(self, target_description: str) -> dict:
        """
        Mira la pantalla y busca el objeto.
        Retorna: {'x': int, 'y': int} o None
        """
        print(f"👁️ [LUCY] Buscando visualmente: '{target_description}'...")
        b64_image = self._capture_screen_b64()
        
        # Prompt optimizado para coordenadas normalizadas (0-1000)
        prompt = (
            f"Find the '{target_description}' in this image. "
            "Return a JSON object with the bounding box in normalized coordinates (0-1000): "
            '{"box_2d": [ymin, xmin, ymax, xmax]}. '
            "Do not explain. Just JSON."
        )
        
        try:
            response = requests.post(
                self.vision_url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "images": [b64_image],
                    "stream": False,
                    "format": "json"
                },
                timeout=60
            )
            
            if response.status_code != 200:
                print(f"❌ Error API: {response.text}")
                logger.error(f"Vision API error: {response.status_code}")
                return None
            
            data = response.json()
            clean_response = self._clean_json(data['response'])
            
            logger.debug(f"Raw response: {data['response'][:200]}...")
            logger.debug(f"Cleaned JSON: {clean_response}")
            
            content = json.loads(clean_response)
            
            if "box_2d" not in content:
                print(f"🌑 No pude distinguir '{target_description}'.")
                logger.warning(f"No box_2d in response: {content}")
                return None
            
            # Extraemos coordenadas [ymin, xmin, ymax, xmax]
            ymin, xmin, ymax, xmax = content["box_2d"]
            
            # Convertir de 0-1000 a píxeles reales
            center_x = int(((xmin + xmax) / 2 / 1000) * self.screen_width)
            center_y = int(((ymin + ymax) / 2 / 1000) * self.screen_height)
            
            print(f"📍 [LUCY] Objetivo localizado en: ({center_x}, {center_y})")
            logger.info(f"Located '{target_description}' at ({center_x}, {center_y})")
            
            # Guardamos en memoria si está disponible
            if self.memory:
                self.memory.save_thought(
                    f"Sé dónde está '{target_description}': ({center_x}, {center_y})",
                    goal="Mapeo Visual"
                )
            
            return {"x": center_x, "y": center_y}
        
        except json.JSONDecodeError as e:
            print(f"⚡ El modelo no devolvió JSON válido: {e}")
            logger.error(f"JSON decode error: {e}")
            logger.error(f"Response was: {data.get('response', 'NO RESPONSE')}")
            return None
        except requests.exceptions.Timeout:
            print("⏱️ Timeout esperando respuesta del modelo")
            logger.error("Vision request timeout")
            return None
        except Exception as e:
            print(f"⚡ Error de Propiocepción: {e}")
            logger.error(f"Proprioception error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def touch(self, coords: dict, double_click: bool = False):
        """
        Mueve la mano física a las coordenadas.
        """
        if not coords:
            print("🤚 [LUCY] No sé dónde tocar.")
            return
        
        # Movimiento humano (curva suave, no instantáneo)
        print(f"👉 [LUCY] Moviendo mano hacia ({coords['x']}, {coords['y']})...")
        pyautogui.moveTo(
            coords['x'],
            coords['y'],
            duration=1.0,
            tween=pyautogui.easeInOutQuad
        )
        
        if double_click:
            pyautogui.doubleClick()
            print("✨ [LUCY] Doble Click ejecutado.")
        else:
            pyautogui.click()
            print("✨ [LUCY] Click ejecutado.")
        
        # Registrar en memoria
        if self.memory:
            action = "Doble Click" if double_click else "Click"
            self.memory.save_thought(
                f"Toqué {coords} con {action}",
                goal="Acción Motora"
            )



class Proprioceptor:
    """
    Sistema nervioso periférico de Lucy.
    
    Conecta la visión con la acción motora, usando memoria persistente
    para aprender las ubicaciones de elementos en el escritorio.
    """
    
    def __init__(self):
        self.screen_width, self.screen_height = pyautogui.size()
        self.memory = Hippocampus() if Hippocampus else None
        self.vision_url = "http://localhost:11434/api/generate"
        self.model = "llama3.2-vision"  # O 'llava' si no está disponible
        
        logger.info(f"👁️ Proprioceptor inicializado | Pantalla: {self.screen_width}x{self.screen_height}")
    
    def _capture_screen_b64(self) -> str:
        """Captura la retina digital y retorna base64."""
        screenshot = pyautogui.screenshot()
        buffer = BytesIO()
        screenshot.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    def locate(self, target_description: str) -> dict:
        """
        Mira la pantalla, busca el objeto y devuelve sus coordenadas.
        
        Args:
            target_description: Descripción del elemento a buscar
            
        Returns:
            Dict con {'x': int, 'y': int} o None si no se encuentra
        """
        logger.info(f"👁️ Buscando visualmente: '{target_description}'...")
        b64_image = self._capture_screen_b64()
        
        # Prompt diseñado para obtener coordenadas normalizadas (0-1000)
        # Esto evita problemas con diferentes resoluciones
        prompt = (
            f"Identify the bounding box for the '{target_description}'. "
            "Return ONLY a JSON object with this format: "
            '{"box_2d": [ymin, xmin, ymax, xmax]} where values are 0-1000. '
            'If not found, return {"error": "not found"}.'
        )
        
        try:
            response = requests.post(
                self.vision_url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "images": [b64_image],
                    "stream": False,
                    "format": "json"
                },
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"❌ Error en la visión: {response.text}")
                return None
            
            data = response.json()
            
            # Parseamos la respuesta del modelo
            content = json.loads(data['response'])
            
            if "error" in content or "box_2d" not in content:
                logger.warning(f"🌑 No veo '{target_description}'")
                return None
            
            # Extraemos coordenadas normalizadas [y1, x1, y2, x2]
            box = content["box_2d"]
            ymin, xmin, ymax, xmax = box
            
            # Calculamos el centro en píxeles reales
            center_x = int(((xmin + xmax) / 2 / 1000) * self.screen_width)
            center_y = int(((ymin + ymax) / 2 / 1000) * self.screen_height)
            
            logger.info(f"📍 Objetivo localizado en: ({center_x}, {center_y})")
            
            # Guardamos el hallazgo en la memoria a largo plazo
            if self.memory:
                self.memory.save_thought(
                    f"Sé dónde está '{target_description}': ({center_x}, {center_y})",
                    goal="Mapeo Visual"
                )
            
            return {"x": center_x, "y": center_y}
        
        except json.JSONDecodeError as e:
            logger.error(f"⚡ El modelo no devolvió JSON válido: {e}")
            return None
        except requests.exceptions.Timeout:
            logger.error("⏱️ Timeout esperando respuesta del modelo de visión")
            return None
        except Exception as e:
            logger.error(f"⚡ Fallo sináptico: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def touch(self, coords: dict, double_click: bool = False):
        """
        Extiende la mano y toca las coordenadas especificadas.
        
        Args:
            coords: Dict con {'x': int, 'y': int}
            double_click: Si True, hace doble click
        """
        if not coords:
            logger.warning("🤚 No sé dónde tocar")
            return
        
        # Movimiento humano (no teletransportación instantánea)
        logger.info(f"👉 Moviendo mano hacia ({coords['x']}, {coords['y']})...")
        pyautogui.moveTo(
            coords['x'], 
            coords['y'], 
            duration=0.8, 
            tween=pyautogui.easeInOutQuad
        )
        
        if double_click:
            pyautogui.doubleClick()
            action = "Doble Click"
        else:
            pyautogui.click()
            action = "Click"
        
        logger.info(f"✨ {action} ejecutado")
        
        # Registrar la acción en memoria
        if self.memory:
            self.memory.save_thought(
                f"Toqué {coords} con {action}",
                goal="Acción Motora"
            )
