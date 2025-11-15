# Proyecto VS Code + Ollama (Cabina de mando local)

Este repo define un entorno de trabajo donde **VS Code** funciona como “cabina de mando”
y la IA principal es un modelo local corriendo en **Ollama**.  
El objetivo es poder reinstalar o mover todo este entorno a otra máquina de forma
reproducible, usando solo este repositorio y algunos scripts.

---

## 1. Objetivo

- Usar **VS Code** como centro de comando para:
  - Programar.
  - Tener repositorios de proyectos (agentes, n8n, etc.).
  - Hablar con una IA local que “vea” el código y los archivos del proyecto.
- Evitar depender de modelos en la nube siempre que sea posible.
- Documentar y automatizar lo máximo posible con scripts dentro de este repo.

---

## 2. Dependencias (resumen)

- Ubuntu 22.04 / 24.04 (u otra distro compatible).
- Herramientas base: `git`, `curl`, `wget`, `gcc`, `build-essential`,
  `python3`, `pip`, `node`, `npm`, `docker`, `docker compose`.
- IA local:
  - **Ollama** instalado como servicio.
  - Modelo `gpt-oss:20b` descargado.
  - **VS Code** con la extensión **Continue** instalada.

---

## 3. Scripts incluidos

- `scripts/check_deps.sh`  
  Verifica que las dependencias mínimas estén instaladas.

---

## 4. Próximos pasos

- Agregar más scripts para instalación automática.
- Crear configuración detallada de Continue y Ollama.
- Integrar otras herramientas (por ejemplo n8n) documentadas en este mismo repo.

---


## 6. Cómo clonar este entorno en otra máquina

### 6.1. Clonar el repositorio

En la nueva máquina:

```bash
git clone https://github.com/LokoKanishka/Proyecto-VSCode.git
cd Proyecto-VSCode

## 7. Cómo volver a levantar el entorno después de reiniciar la PC

1. Abrir una terminal y ubicarse en el proyecto:

   ```bash
   cd ~/Lucy_Workspace/Proyecto-VSCode




