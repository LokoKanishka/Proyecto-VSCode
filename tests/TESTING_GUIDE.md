# Lucy Web - Testing & Deployment Guide

## Prerequisites

### System Dependencies
```bash
# Audio processing
sudo apt-get install ffmpeg alsa-utils

# Python dependencies
pip install watchdog flask-socketio ray loguru
pip install faster-whisper torch  # For ASR
```

### Lucy Dependencies
```bash
# Install Mimic3 TTS (if not already installed)
pip install mycroft-mimic3-tts

# Or use system mimic3
sudo apt-get install mimic3
```

---

## Starting Lucy Web

### 1. Start Lucy Core (Ray)
```bash
# Terminal 1: Start Ray cluster (optional, for distributed mode)
docker-compose -f docker-compose.yml -f docker-compose.ray.yml up

# Or start Lucy manager directly
python run_lucy_manager.py  # (if exists)
```

### 2. Start Web Server
```bash
# Terminal 2: Start Flask app
cd /home/lucy-ubuntu/Lucy_Workspace/Proyecto-VSCode
python lucy_web/app.py

# Expected output:
# ⬇️ [Engine] Cargando Sistemas...
# ✅ [Engine] SISTEMA FULL-DUPLEX LISTO.
# ✅ Voice bridge initialized
# Starting consciousness monitor...
# ✅ Consciousness monitor started
# 🚀 Starting Lucy Web on port 5000
```

### 3. Open Browser
```
http://localhost:5000
```

---

## Testing Checklist

### Test 1: Consciousness Visualization

**Manual test:**
1. Run test script:
   ```bash
   python tests/test_consciousness.py
   ```

2. Observe browser:
   - [ ] State icon changes (💤 → ⚙️ → 💠)
   - [ ] Border color changes (cyan variations)
   - [ ] Entropy bar animates (0.1 → 0.6 → 0.2)
   - [ ] Activity bar animates (0.0 → 0.8 → 0.9)
   - [ ] Log entries appear with timestamps
   - [ ] Pulse animation every 2s

**Expected:** Real-time updates without refresh

---

### Test 2: Voice Input (Browser → Server → Transcription)

**Manual test:**
1. Click microphone button 🎤
2. Speak clearly: "Hola Lucy, ¿cómo estás?"
3. Click microphone again to stop

**Expected console output:**
```
Received voice input (audio/webm, XXXXX bytes)
✅ Transcribed: Hola Lucy, ¿cómo estás?
Sending to Lucy core...
```

**Expected browser:**
- [ ] Status: "You said: 'Hola Lucy, ¿cómo estás?'"
- [ ] Transcription appears in chat
- [ ] Response from Lucy appears

---

### Test 3: Lucy Core Processing

**Prerequisites:** Ray cluster running

**Test:**
1. Send voice input (Test 2)
2. Wait for processing

**Expected console:**
```
Sending to Lucy core...
Lucy response: [Lucy's response text]
Generating TTS...
▶️ Hablando...
TTS audio sent to client
```

**Expected browser:**
- [ ] Chat message from assistant appears
- [ ] Status: "▶️ Lucy speaking..."

---

### Test 4: TTS Playback

**Test:**
1. After Lucy response (Test 3)
2. Audio should play automatically

**Expected browser:**
- [ ] Audio plays in browser
- [ ] Status: "▶️ Lucy speaking..."
- [ ] Status: "Ready" when audio ends

**Troubleshooting:**
- Check browser console for errors
- Verify audio permissions granted
- Test with headphones if speakers fail

---

### Test 5: Wake Word Mode (Continuous Listen)

**Test:**
1. Toggle "Wake Word Mode" ON
2. Speak → automatic recording
3. Wait for response → auto-rearme

**Expected behavior:**
- [ ] Automatic recording after each response
- [ ] No manual click needed
- [ ] Continuous conversation loop

---

### Test 6: Fallback (Ray Offline)

**Test:**
1. Stop Ray cluster
2. Send voice input

**Expected:**
```
Ray not available, using fallback response
```

**Browser shows:**
```
Entendí tu mensaje: '[text]'. (Lucy core no disponible en este momento)
```

---

## Troubleshooting

### Voice bridge not loading
```
⚠️ Voice bridge not available: [error]
```

**Fix:**
- Install faster-whisper: `pip install faster-whisper`
- Install torch: `pip install torch`
- Verify CUDA available: `python -c "import torch; print(torch.cuda.is_available())"`

---

### FFmpeg conversion fails
```
ffmpeg failed: [stderr]
```

**Fix:**
- Install ffmpeg: `sudo apt-get install ffmpeg`
- Check audio format in browser (should be webm or wav)

---

### Consciousness not updating
```
Consciousness file not found
```

**Fix:**
- File created automatically on first connect
- Check `lucy_consciousness.json` exists in project root
- Run `test_consciousness.py` to simulate updates

---

### TTS not playing
```
Audio playback failed
```

**Fix:**
- Check browser console for CORS errors
- Verify mimic3 installed: `which mimic3`
- Test TTS manually: `echo "test" | mimic3 > test.wav && aplay test.wav`
- Check browser audio permissions

---

### Ray connection fails
```
Ray Cluster NOT FOUND
```

**Fix:**
- Start Ray: `docker-compose -f docker-compose.ray.yml up`
- Or run locally: `ray start --head`
- Verify manager running: `ray list actors`

---

## Performance Metrics

### Expected Latencies

| Stage | Target | Actual |
|-------|--------|--------|
| Audio upload | <500ms | - |
| FFmpeg conversion | <1s | - |
| ASR transcription | <2s | - |
| Lucy processing | <5s | - |
| TTS generation | <3s | - |
| Total (voice → response) | <12s | - |

### Monitoring

Check logs for:
```python
log.info(f"Received voice input ({mime}, {len(audio_b64)} bytes)")
log.info(f"Transcribed: {text}")
log.info("Sending to Lucy core...")
log.info(f"Lucy response: {response}")
log.info("TTS audio sent to client")
```

---

## Production Deployment

### Security (TODO)
- [ ] Add authentication
- [ ] Enable HTTPS (TLS certificates)
- [ ] Rate limiting on voice_input
- [ ] Input sanitization

### Scalability
- [ ] Redis for session storage
- [ ] Load balancer for multiple instances
- [ ] Separate TTS worker queue
- [ ] CDN for static assets

### Monitoring
- [ ] Prometheus metrics
- [ ] Grafana dashboards
- [ ] Error tracking (Sentry)
- [ ] Audio quality metrics

---

## Quick Reference

### Start Everything
```bash
# Terminal 1: Ray (optional)
docker-compose -f docker-compose.ray.yml up

# Terminal 2: Lucy Web
python lucy_web/app.py

# Terminal 3: Test
python tests/test_consciousness.py
```

### Kill Everything
```bash
# Ctrl+C in each terminal, then:
docker-compose down
pkill -f lucy_web
```

### Check Status
```bash
# Ray
ray status

# Web server
curl http://localhost:5000/api/health

# Voice bridge
python -c "from src.engine.voice_bridge import LucyVoiceBridge; vb = LucyVoiceBridge()"
```

---

**Status:** Fase 1-3 COMPLETADAS ✅  
**Testing:** Manual validation required  
**Production:** Not ready (security pending)
