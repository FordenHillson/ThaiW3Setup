"""Recap menu script maps embedded EN lines to Thai without touching the USM."""
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.recap_script import RecapScriptError, build_recap_menu_script, patch_recap_menu_text, recap_pairs

try:
    from gamepath import game_path
    content0 = Path(game_path("content", "content0"))
except Exception:
    content0 = Path()
if not (content0 / "scripts/game/gui/main_menu/mainRecapMoviesMenu.ws").is_file():
    content0 = Path(r"C:\Program Files (x86)\Steam\steamapps\common\The Witcher 3\content\content0")

pairs = recap_pairs(content0)
assert len(pairs) == 25, len(pairs)
assert pairs[0][0].startswith("I see you gather")
assert "ข้าเห็น" in pairs[0][1]

rel, data = build_recap_menu_script(content0)
patched = data.decode("utf-8")
assert rel.as_posix().endswith("mainRecapMoviesMenu.ws")
assert "ModThaiRecapSub" in patched
assert "ModThaiRecapSub( subtitles )" in patched
assert "ข้าเห็น" in patched
assert '\\"Why have the gods forsaken us?\\"' in patched

try:
    patch_recap_menu_text(patched, pairs)
    raise AssertionError("expected already-patched error")
except RecapScriptError:
    pass

print("test_recap_script ok", len(pairs))
