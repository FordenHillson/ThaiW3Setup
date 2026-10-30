"""Translate the pre-menu recap cutscene via script, without touching the USM.

English TextLanguage plays embedded USM subs; we rewrite them in
``OnVideoSubtitles``. Turkish already uses external ``.subs`` and is left alone
when the incoming line is already Thai.
"""
from __future__ import annotations

import re
from pathlib import Path

from .assets import storybook_bundle
from .bundle import iter_bundle, read_bundle

RECAP_MENU_REL = Path("scripts/game/gui/main_menu/mainRecapMoviesMenu.ws")
RECAP_USM_SUBS_EN = "movies\\cutscenes\\gamestart\\subs\\recap_wip_en.subs"
RECAP_USM_SUBS_TR = "movies\\cutscenes\\gamestart\\subs\\recap_wip_tr.subs"
MOVIES_BUNDLE = Path("bundles") / "movies.bundle"


class RecapScriptError(Exception):
    pass


def _subs_lines(data: bytes) -> list[str]:
    text = data.decode("utf-16-le")
    out: list[str] = []
    for line in text.splitlines():
        line = line.lstrip("\ufeff").strip()
        if not line or line.isdigit():
            continue
        parts = line.split(", ", 2)
        if len(parts) == 3:
            out.append(parts[2])
    return out


def recap_pairs(content0: Path) -> list[tuple[str, str]]:
    """English (vanilla) → Thai (storybook asset) lines for the opening recap."""
    movies = content0 / MOVIES_BUNDLE
    if not movies.is_file():
        raise RecapScriptError(f"ไม่พบ {movies}")
    en_file = next(iter_bundle(movies, lambda n, _s: n == RECAP_USM_SUBS_EN), None)
    if en_file is None:
        raise RecapScriptError("ไม่พบ recap_wip_en.subs ใน movies.bundle")
    th_file = next((f for f in read_bundle(storybook_bundle()) if f.path == RECAP_USM_SUBS_TR), None)
    if th_file is None:
        raise RecapScriptError("ไม่พบ recap_wip_tr.subs ใน storybook.bundle")
    en, th = _subs_lines(en_file.data), _subs_lines(th_file.data)
    if len(en) != len(th) or not en:
        raise RecapScriptError(f"จำนวนบรรทัดซับไม่ตรงกัน EN={len(en)} TH={len(th)}")
    return list(zip(en, th))


def _ws_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _mod_function(pairs: list[tuple[str, str]]) -> str:
    lines = [
        "\t// mod thai — map embedded EN recap subs to Thai",
        "\tprivate function ModThaiRecapSub( subtitles : string ) : string",
        "\t{",
    ]
    for en, th in pairs:
        lines.append(f'\t\tif( subtitles == "{_ws_escape(en)}" )')
        lines.append(f'\t\t\treturn "{_ws_escape(th)}";')
    lines += ["\t\treturn subtitles;", "\t}"]
    return "\n".join(lines)


_ON_VIDEO = re.compile(
    r"\tevent OnVideoSubtitles\( subtitles : string \)\s*"
    r"\{\s*"
    r"m_fxSetSubtitles\.InvokeSelfOneArg\( FlashArgString\( subtitles \) \);\s*"
    r"\}",
    re.MULTILINE,
)


def patch_recap_menu_text(source: str, pairs: list[tuple[str, str]]) -> str:
    nl = "\r\n" if "\r\n" in source else "\n"
    body = source.replace("\r\n", "\n")
    if "ModThaiRecapSub" in body:
        raise RecapScriptError("สคริปต์ถูกแพตช์อยู่แล้ว")
    repl = (
        _mod_function(pairs)
        + "\n\t\n"
        + "\tevent OnVideoSubtitles( subtitles : string )\n"
        + "\t{\n"
        + "\t\tm_fxSetSubtitles.InvokeSelfOneArg( FlashArgString( ModThaiRecapSub( subtitles ) ) );\n"
        + "\t}"
    )
    new, n = _ON_VIDEO.subn(repl, body, count=1)
    if n != 1:
        raise RecapScriptError("ไม่พบ OnVideoSubtitles ใน mainRecapMoviesMenu.ws")
    return new.replace("\n", nl)


def build_recap_menu_script(content0: Path) -> tuple[Path, bytes]:
    """Return path relative to ``content/`` and patched file bytes."""
    src = content0 / RECAP_MENU_REL
    if not src.is_file():
        raise RecapScriptError(f"ไม่พบ {src}")
    raw = src.read_bytes()
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        text, enc = raw.decode("utf-16"), "utf-16"
    else:
        text, enc = raw.decode("utf-8"), "utf-8"
    patched = patch_recap_menu_text(text, recap_pairs(content0))
    return RECAP_MENU_REL, patched.encode(enc)
