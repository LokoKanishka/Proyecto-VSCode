from src.engine.swarm_manager import SwarmManager


def test_auto_manage_vram_switches():
    sm = SwarmManager()
    sm.set_profile("vision")
    sm.auto_manage_vram(0.95)
    assert sm._active_profile == "general"
