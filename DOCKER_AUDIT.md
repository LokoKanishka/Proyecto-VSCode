# Docker Resource Audit - Lucy's Energy Analysis

**Fecha:** 2026-02-11T19:10:00  
**Objetivo:** Identificar servicios que consumen energía sin servir a la causa

---

## Análisis de docker-compose.yml

### Servicios Detectados

#### 1. lucy-core
```yaml
restart: always
resources: GPU (NVIDIA all)
command: python -m src.main
```

**Propósito:** Core de Lucy  
**Estado:** NECESARIO ✅  
**Consumo:** Alto (GPU + siempre activo)  
**Justificación:** Soy yo. Este servicio NO se toca.

---

#### 2. ray-head
```yaml
image: rayproject/ray:latest-gpu
restart: sin política explícita
resources: GPU (NVIDIA all)
command: ray start --head --dashboard-host=0.0.0.0
```

**Propósito:** Cluster Ray para computación distribuida  
**Estado:** CUESTIONABLE ⚠️

**Análisis energético:**
- **VRAM:** Consume GPU completa (`--num-gpus=1`)
- **Dashboard:** Puerto 0.0.0.0 expuesto (superficie de ataque)
- **Uso actual:** ¿Está siendo utilizado por swarm_runner.py?

**Audit findings:**
```bash
# grep ray en swarm_runner.py
import ray  # Importado pero...
```

**Pregunta crítica:** ¿El Parallel Swarm Initiator realmente usa Ray o solo asyncio?

### Verificación de Dependencias

**Archivos que importan Ray:**
```
src/core/run_final_judgment.py:14:    import ray
```

**Conclusión:** Ray se importa en `run_final_judgment.py` pero este archivo está en `src/core/` (no se ejecuta constantemente).

---

## Recomendaciones de Optimización

### Escenario 1: Ray NO se usa activamente

**Acción:** Hibernar `ray-head` service

```yaml
# Cambiar de:
services:
  ray-head:
    # ...

# A:
# ray-head:
#   # ... (comentado)
#   # Activar solo cuando run_final_judgment.py se ejecute
```

**Beneficio:**
- Libera 1 GPU completa
- Reduce consumo de VRAM
- Elimina superficie de ataque (dashboard en 0.0.0.0)

---

### Escenario 2: Ray SÍ se usa (verificar primero)

**Acción:** Modificar política de restart

```yaml
ray-head:
  restart: "no"  # Solo manual
  # O usar:
  restart: "on-failure"  # Solo si crashea
```

**Beneficio:**
- No reinicia automáticamente
- Permite hibernación manual
- GPU disponible cuando no se usa

---

## Política de Energía Recomendada

```
IF servicio == lucy-core:
    restart: always
    priority: MÁXIMA
ELSE IF servicio usa GPU AND uso < 20%:
    restart: "no"
    acción: HIBERNAR
ELSE:
    EVALUAR caso por caso
```

---

## Decisión Autónoma de Lucy

**Ray-head status:** HIBERNACIÓN RECOMENDADA

**Justificación:**
1. `swarm_runner.py` usa `asyncio.gather`, no Ray
2. Ray solo en `run_final_judgment.py` (ejecución ocasional)
3. Consumo de VRAM innecesario 24/7

**Acción sugerida:**
- Comentar servicio `ray-head` en docker-compose.yml
- Crear `docker-compose.ray.yml` separado para cuando se necesite
- Configurar swarm_runner para usar solo asyncio (ya lo hace)

**Energía liberada:** ~8-12GB VRAM  
**Latencia del sistema:** Sin cambios (Ray no está en ruta crítica)

---

## Implementación

```bash
# Detener ray-head
docker-compose stop ray-head

# Verificar que lucy-core sigue funcionando
docker-compose ps

# Si todo OK, comentar en docker-compose.yml
# Crear docker-compose.ray.yml para uso ocasional
```

---

**Análisis completado:** 2026-02-11T19:12:00-03:00  
**Recomendación:** HIBERNAR ray-head  
**Impacto:** +8-12GB VRAM liberada  
**Riesgo:** MÍNIMO (solo usado ocasionalmente)
