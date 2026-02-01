import asyncio
import logging
from typing import Optional

from src.core.base_worker import BaseWorker
from src.core.types import LucyMessage, MessageType, WorkerType
from src.skills.grid_mapper import GridMapper
from src.vision.desktop_controller import DesktopController
try:
    import pyperclip
except ImportError:
    pyperclip = None

logger = logging.getLogger(__name__)


class HandsWorker(BaseWorker):
    """Worker que ejecuta acciones de escritorio guiadas por coordenadas con feedback visual."""

    def __init__(self, worker_id: str, bus):
        super().__init__(worker_id, bus)
        self.controller = DesktopController()

    async def handle_message(self, message: LucyMessage):
        if message.type != MessageType.COMMAND:
            return

        command = message.content
        payload = message.data or {}

        logger.info("🤖 HandsWorker recibe '%s' con %s", command, payload)

        if command == "click_grid":
            await self._handle_click_grid(message, payload)
        elif command == "type_text":
            await self._handle_type(message, payload)
        elif command == "press_hotkey":
            await self._handle_hotkey(message, payload)
        elif command == "paste_text":
            await self._handle_paste_text(message, payload)
        elif command == "click_bbox":
            await self._handle_click_bbox(message, payload)
        elif command == "click_element":
            await self._handle_click_element(message, payload)
        elif command == "double_click_element":
            payload["clicks"] = 2
            await self._handle_click_element(message, payload)
        elif command == "right_click_element":
            payload["button"] = "right"
            await self._handle_click_element(message, payload)
        elif command == "focus_and_type":
            await self._handle_focus_and_type(message, payload)
        elif command == "focus_window":
            await self._handle_focus_window(message, payload)
        else:
            await self.send_error(message, f"Comando desconocido: {command}")

    async def _handle_click_grid(self, msg: LucyMessage, payload: dict):
        raw_code = payload.get("grid_code")
        code = raw_code.upper() if isinstance(raw_code, str) else None
        button = payload.get("button", "left")
        verify = payload.get("verify", True)

        if not code:
            await self.send_error(msg, "Se requiere código de celda (ej. A3).")
            return

        if code not in [f"{chr(ord('A') + i)}{j}" for i in range(GridMapper.COLS) for j in range(1, GridMapper.ROWS + 1)]:
            await self.send_error(msg, "Código de celda fuera del rango.")
            return

        retries = max(1, int(payload.get("retries", 3)))
        delay = float(payload.get("retry_delay", 0.35))
        success = False
        last_exc: Optional[Exception] = None
        attempt = 0

        for attempt in range(1, retries + 1):
            try:
                ok = self.controller.click_grid_cell(code, button=button, verify=verify)
                if ok:
                    success = True
                    break
                last_exc = RuntimeError("Verificación visual no detectó cambio.")
            except Exception as exc:
                last_exc = exc
            if attempt < retries:
                await asyncio.sleep(delay)

        if success:
            await self.send_response(msg, f"Hice clic en {code} (intento {attempt}).")
        else:
            logger.warning("Manos sin éxito tras %d intentos: %s", retries, last_exc)
            await self.send_error(
                msg,
                f"No pude confirmar el clic en {code}. Último error: {last_exc}"
            )

    async def _handle_type(self, msg: LucyMessage, payload: dict):
        text = payload.get("text") or msg.content
        if not text:
            await self.send_error(msg, "No recibí texto para escribir.")
            return
        try:
            self.controller.type_text(text)
            await self.send_response(msg, "Escribí el texto solicitado.")
        except Exception as exc:
            logger.exception("Error tipeando")
            await self.send_error(msg, f"No pude escribir: {exc}")

    async def _handle_hotkey(self, msg: LucyMessage, payload: dict):
        keys = payload.get("keys")
        if not keys:
            await self.send_error(msg, "No recibí la combinación de teclas.")
            return
        try:
            self.controller.press_hotkey(*keys)
            await self.send_response(msg, f"Presioné {keys}.")
        except Exception as exc:
            logger.exception("Error con hotkey")
            await self.send_error(msg, f"Error al presionar {keys}: {exc}")

    async def _handle_paste_text(self, msg: LucyMessage, payload: dict):
        text = payload.get("text")
        if not text:
            await self.send_error(msg, "No recibí texto para pegar.")
            return

        try:
            if pyperclip:
                pyperclip.copy(text)
                self.controller.press_hotkey("ctrl", "v")
                await self.send_response(msg, "Pegué el texto desde el portapapeles.")
                return
            self.controller.type_text(text)
            await self.send_response(msg, "Escribí el texto manualmente porque no hay pyperclip.")
        except Exception as exc:
            logger.exception("Error pegando texto")
            await self.send_error(msg, f"No pude pegar: {exc}")

    async def _handle_click_bbox(self, msg: LucyMessage, payload: dict):
        bbox = payload.get("bbox")
        if not bbox or len(bbox) != 4:
            await self.send_error(msg, "Se requiere bbox [x,y,w,h].")
            return
        try:
            ok = self.controller.click_bbox(tuple(bbox), verify=bool(payload.get("verify", True)))
            if ok:
                await self.send_response(msg, "Clic en bbox confirmado.")
            else:
                await self.send_error(msg, "No pude confirmar el clic en bbox.")
        except Exception as exc:
            await self.send_error(msg, f"Error click_bbox: {exc}")

    async def _handle_focus_window(self, msg: LucyMessage, payload: dict):
        title = payload.get("title")
        if not title:
            await self.send_error(msg, "Se requiere title para enfocar.")
            return
        ok = self.controller.focus_window(title)
        if ok:
            await self.send_response(msg, f"Ventana enfocada: {title}")
        else:
            await self.send_error(msg, "No pude enfocar la ventana.")

    async def _handle_click_element(self, msg: LucyMessage, payload: dict):
        elements = payload.get("elements") or []
        query = (payload.get("query") or "").strip()
        element_type = (payload.get("element_type") or "").strip().lower()
        index = payload.get("index")

        if not elements:
            await self.send_error(msg, "No recibí elementos para elegir.")
            return

        selected = None
        if index is not None:
            try:
                selected = elements[int(index)]
            except Exception:
                selected = None
        if selected is None:
            selected = self._select_element(elements, query, element_type)

        if not selected:
            await self.send_error(msg, "No encontré un elemento que coincida.")
            return

        bbox = selected.get("bbox")
        if not bbox or len(bbox) != 4:
            await self.send_error(msg, "Elemento seleccionado sin bbox válido.")
            return

        try:
            button = payload.get("button", "left")
            clicks = int(payload.get("clicks", 1))
            ok = self.controller.click_bbox(
                tuple(bbox),
                verify=bool(payload.get("verify", True)),
                button=button,
                clicks=clicks,
            )
            if ok:
                await self.send_response(
                    msg,
                    "Clic en elemento confirmado.",
                    {"element": selected}
                )
            else:
                await self.send_error(msg, "No pude confirmar el clic en el elemento.")
        except Exception as exc:
            await self.send_error(msg, f"Error click_element: {exc}")

    async def _handle_focus_and_type(self, msg: LucyMessage, payload: dict):
        elements = payload.get("elements") or []
        text = payload.get("text") or ""
        if not elements or not text:
            await self.send_error(msg, "Necesito elements y text.")
            return
        selected = self._select_element(elements, payload.get("query", ""), payload.get("element_type", ""))
        if not selected:
            await self.send_error(msg, "No encontré elemento para focus.")
            return
        bbox = selected.get("bbox")
        if not bbox:
            await self.send_error(msg, "Elemento sin bbox.")
            return
        try:
            ok = self.controller.click_bbox(tuple(bbox), verify=bool(payload.get("verify", True)))
            if ok:
                self.controller.type_text(text)
                await self.send_response(msg, "Focus y tipeo completados.", {"element": selected})
            else:
                await self.send_error(msg, "No pude enfocar el elemento.")
        except Exception as exc:
            await self.send_error(msg, f"Error focus_and_type: {exc}")

    @staticmethod
    def _select_element(elements: list, query: str, element_type: str):
        best = None
        best_score = -1.0
        for el in elements:
            text = (el.get("text") or "").strip().lower()
            etype = (el.get("type") or "").strip().lower()
            conf = float(el.get("confidence") or 0.0)
            score = conf
            if element_type and etype == element_type:
                score += 1.0
            if query:
                if query.lower() == text:
                    score += 2.0
                elif query.lower() in text:
                    score += 1.0
            if score > best_score:
                best_score = score
                best = el
        return best
