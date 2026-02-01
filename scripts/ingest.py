import ray
import os
import argparse
from pathlib import Path
from pypdf import PdfReader
import asyncio
from loguru import logger

# Connect to Ray
if not ray.is_initialized():
    try:
        ray.init(address="auto", namespace="lucy")
    except:
        ray.init(namespace="lucy")

def get_memory_actor():
    try:
        return ray.get_actor("MemoryActor")
    except ValueError:
        logger.error("❌ MemoryActor not found! Is the Lucy Main App running?")
        return None

def extract_text_from_pdf(path: Path) -> str:
    try:
        reader = PdfReader(path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        logger.error(f"Error reading PDF {path}: {e}")
        return ""

def chunk_text(text: str, chunk_size: int = 500) -> list[str]:
    # Simple chunking
    return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

async def ingest_file(memory, path: Path):
    logger.info(f"📄 Processing: {path.name}...")
    text = ""
    
    if path.suffix.lower() == ".pdf":
        text = extract_text_from_pdf(path)
    elif path.suffix.lower() in [".txt", ".md", ".py"]:
        try:
            text = path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Error reading text file {path}: {e}")
            return

    if not text.strip():
        logger.warning(f"⚠️ No text found in {path.name}")
        return

    chunks = chunk_text(text)
    tasks = []
    for chunk in chunks:
        tasks.append(memory.add.remote(chunk, source=str(path)))
    
    await asyncio.gather(*tasks)
    logger.info(f"✅ Ingested {len(chunks)} chunks from {path.name}")

async def main():
    parser = argparse.ArgumentParser(description="Ingest documents into Lucy's Memory.")
    parser.add_argument("dir", type=str, help="Directory to scan")
    args = parser.parse_args()

    memory = get_memory_actor()
    if not memory:
        return

    root = Path(args.dir)
    if not root.exists():
        logger.error("Directory not found!")
        return

    files = [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in [".pdf", ".txt", ".md", ".py"]]
    
    logger.info(f"📚 Found {len(files)} docs in {root}. Starting ingestion...")
    
    for file_path in files:
        await ingest_file(memory, file_path)

    logger.info("🎉 Ingestion complete!")

if __name__ == "__main__":
    asyncio.run(main())
