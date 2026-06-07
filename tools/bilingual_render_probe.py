#!/usr/bin/env python3
"""Run a headless Ren'Py probe that exercises Better Bilingual text output.

This script does not start gameplay. It can temporarily install the current
plugin plus a Ren'Py command inside the target game, lets Ren'Py load the game
and run init code, then enumerates the loaded translator/script text and
simulates the plugin's display paths with Ren'Py's own substitution and Text
machinery.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path


PROBE_RPY = r'''
init 999999 python:
    import collections
    import json
    import os
    import sys
    import time
    import traceback

    def _bb_probe_output_path():
        value = os.environ.get("BB_RENDER_PROBE_OUTPUT")
        if value:
            return value
        return os.path.join(config.gamedir, "bb_render_probe_report.jsonl")

    def _bb_probe_limit():
        try:
            return int(os.environ.get("BB_RENDER_PROBE_LIMIT", "0") or "0")
        except Exception:
            return 0

    def _bb_probe_truthy_env(name):
        return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")

    def _bb_probe_text(value):
        if value is None:
            return None
        try:
            if isinstance(value, str):
                return value
            return str(value)
        except Exception:
            return repr(value)

    def _bb_probe_node_text(node):
        if node is None:
            return None

        value = getattr(node, "what", None)
        if value is not None:
            return value

        block = getattr(node, "block", None)
        if block:
            for child in block:
                value = getattr(child, "what", None)
                if value is not None:
                    return value

        return None

    def _bb_probe_loc(node):
        try:
            filename = getattr(node, "filename", None)
            linenumber = getattr(node, "linenumber", None)
            if filename is not None and linenumber is not None:
                return "%s:%s" % (filename, linenumber)
        except Exception:
            pass
        return None

    def _bb_probe_short(text, limit=220):
        text = _bb_probe_text(text)
        if text is None:
            return None
        text = text.replace("\n", "\\n")
        if len(text) > limit:
            return text[:limit] + "...<%d chars>" % len(text)
        return text

    def _bb_probe_exception(stage, exc):
        return {
            "stage": stage,
            "exception_type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }

    def _bb_probe_default_modes():
        return [
            "translated",
            "original",
            "translated_first",
            "original_first",
        ]

    def _bb_probe_mode_names():
        value = os.environ.get("BB_RENDER_PROBE_MODES", "")
        if not value.strip():
            return _bb_probe_default_modes()

        rv = []
        for item in value.split(","):
            item = item.strip()
            if item:
                rv.append(item)
        return rv or _bb_probe_default_modes()

    def _bb_probe_set_mode(mode):
        try:
            persistent.bb_mode = mode
            persistent.ll_fast_original_mode = mode in ("original", "original_first")
            persistent.ll_better_bilingual_mode = mode
        except Exception:
            pass

    def _bb_probe_sync_start_path():
        for name in (
            "bb_init_persistent",
            "bb_sync_engine_language",
            "bb_reset_progress_event_title_cache",
            "bb_capture_current_fonts",
            "bb_patch_progress_event_names",
        ):
            func = globals().get(name, None)
            if func is None:
                continue
            try:
                func()
            except Exception:
                pass

    def _bb_probe_sync_load_path():
        func = globals().get("bb_after_load_callback", None)
        if func is not None:
            try:
                func()
                return
            except Exception:
                pass

        _bb_probe_sync_start_path()

    def _bb_probe_wrap_font(language, text):
        func = globals().get("bb_font_tag", None)
        if func is not None:
            return func(language, text)

        alias = "bb_original_dialogue_font" if language == "original" else "bb_translated_dialogue_font"
        return "{font=%s}%s{/font}" % (alias, text)

    def _bb_probe_pair_from_values(translated, original, mode):
        if translated is None:
            translated = original
        if original is None:
            original = translated

        if mode == "original":
            return [("original", original)]
        if mode == "translated_first":
            return [("translated", translated), ("original", original)]
        if mode == "original_first":
            return [("original", original), ("translated", translated)]
        return [("translated", translated)]

    def _bb_probe_join_pair(pair, with_fonts=False):
        lines = []
        seen = set()

        for language, value in pair:
            if value is None or value in seen:
                continue

            if with_fonts:
                lines.append(_bb_probe_wrap_font(language, value))
            else:
                lines.append(value)
            seen.add(value)

        return "\n".join(lines)

    def _bb_probe_substitute(text):
        func = globals().get("bb_substitute", None)
        if func is not None:
            return func(text)
        try:
            return renpy.substitutions.substitute(text, translate=False)[0]
        except Exception:
            return text

    def _bb_probe_call_say_menu_filter(text, is_menu, identifier=None):
        func = globals().get("bb_say_menu_text_filter", None)
        if func is None:
            func = getattr(config, "say_menu_text_filter", None)
        if func is None:
            return text

        missing = object()
        old_statement_is_menu = globals().get("bb_statement_is_menu", missing)
        old_current_identifier = globals().get("bb_current_identifier", missing)
        globals()["bb_statement_is_menu"] = lambda: is_menu
        if identifier is not None:
            globals()["bb_current_identifier"] = lambda: identifier
        try:
            return func(text)
        finally:
            if old_statement_is_menu is missing:
                try:
                    del globals()["bb_statement_is_menu"]
                except Exception:
                    pass
            else:
                globals()["bb_statement_is_menu"] = old_statement_is_menu

            if old_current_identifier is missing:
                try:
                    del globals()["bb_current_identifier"]
                except Exception:
                    pass
            else:
                globals()["bb_current_identifier"] = old_current_identifier

    def _bb_probe_say_substitution_input(entry):
        source = entry.get("translated")
        if source is None:
            source = entry.get("original")

        return _bb_probe_call_say_menu_filter(source, False, entry.get("identifier"))

    def _bb_probe_menu_substitution_input(entry):
        source = entry.get("translated")
        if source is None:
            source = entry.get("original")

        return _bb_probe_call_say_menu_filter(source, True)

    def _bb_probe_pair_from_identifier(identifier, original, translated, mode):
        # Prefer the plugin's lookup/substitution when it is available, so the
        # probe follows the real runtime mapping path instead of only raw AST.
        old_mode = getattr(persistent, "bb_mode", None)
        _bb_probe_set_mode(mode)
        try:
            pair_func = globals().get("bb_text_pair", None)
            if pair_func is not None and identifier:
                pair = pair_func(translated, identifier)
                if pair:
                    return pair
        except Exception:
            pass
        finally:
            if old_mode is not None:
                _bb_probe_set_mode(old_mode)

        return _bb_probe_pair_from_values(
            _bb_probe_substitute(translated),
            _bb_probe_substitute(original),
            mode,
        )

    def _bb_probe_build_display_cases(entry, mode):
        if entry.get("kind") == "dialogue":
            pair = _bb_probe_pair_from_identifier(
                entry.get("identifier"),
                entry.get("original"),
                entry.get("translated"),
                mode,
            )
            say_text = _bb_probe_join_pair(pair, with_fonts=False)
            say_substitution_input = _bb_probe_say_substitution_input(entry)
            return [
                (
                    "say_screen_text",
                    say_text,
                    pair,
                    say_substitution_input,
                    _bb_probe_expected_after_say_substitution(say_substitution_input),
                ),
                ("history_text", _bb_probe_join_pair(pair, with_fonts=True), pair, None, None),
            ]

        if entry.get("kind") == "string":
            pair = _bb_probe_pair_from_values(
                _bb_probe_substitute(entry.get("translated")),
                _bb_probe_substitute(entry.get("original")),
                mode,
            )
            return [
                ("string_screen_text", _bb_probe_join_pair(pair, with_fonts=False), pair, None, None),
                ("string_font_text", _bb_probe_join_pair(pair, with_fonts=True), pair, None, None),
            ]

        if entry.get("kind") == "menu":
            pair = _bb_probe_pair_from_values(
                _bb_probe_substitute(entry.get("translated")),
                _bb_probe_substitute(entry.get("original")),
                mode,
            )
            menu_text = _bb_probe_join_pair(pair, with_fonts=True)
            menu_substitution_input = _bb_probe_menu_substitution_input(entry)
            return [
                (
                    "menu_text",
                    menu_text,
                    pair,
                    menu_substitution_input,
                    _bb_probe_expected_after_say_substitution(menu_substitution_input),
                ),
            ]

        return []

    def _bb_probe_text_properties(case_name, language, text):
        props = {
            "substitute": False,
        }

        if case_name in ("history_text", "string_font_text", "menu_text"):
            props["style"] = "history_text"
        else:
            props["style"] = "say_dialogue"
            if language is not None:
                func = globals().get("bb_language_for_text", None)
                if func is not None:
                    try:
                        props["font"] = func(language, text)
                    except Exception:
                        pass

        return props

    def _bb_probe_check_say_substitution(text):
        # This mirrors the part of Character.prefix_suffix/Text that can fail
        # before the say screen's substitute False takes over.
        return renpy.substitutions.substitute(text, translate=False)[0]

    def _bb_probe_expected_after_say_substitution(text):
        if not getattr(config, "new_substitutions", True):
            return text
        if not isinstance(text, str) or "[[" not in text:
            return text
        return text.replace("[[", "[")

    def _bb_probe_init_headless_draw():
        if renpy.display.draw is not None:
            return True

        try:
            swdraw = __import__("renpy.display.swdraw", fromlist=["SWDraw"])
            draw = swdraw.SWDraw()
            virtual_size = (
                getattr(config, "screen_width", 1280),
                getattr(config, "screen_height", 720),
            )
            if draw.init(virtual_size):
                renpy.display.draw = draw
                return True
        except Exception:
            pass

        return False

    def _bb_probe_check_text_object(text, props, render):
        displayable = renpy.text.text.Text(text, **props)
        displayable.update()
        displayable.visit()

        if render:
            if not _bb_probe_init_headless_draw():
                raise Exception("Text.render requested, but no headless draw backend could be initialized.")

            displayable.render(
                getattr(config, "screen_width", 1280),
                getattr(config, "screen_height", 720),
                0,
                0,
            )

        return displayable

    def _bb_probe_collect_dialogue_entries(language):
        rv = []
        try:
            tl = renpy.game.script.translator
            default_translates = list(tl.default_translates.items())
        except Exception:
            return rv

        for identifier, default_node in default_translates:
            translated_node = None
            try:
                translated_node = tl.language_translates.get((identifier, language), None)
            except Exception:
                pass

            original = _bb_probe_node_text(default_node)
            translated = _bb_probe_node_text(translated_node)

            if original is None and translated is None:
                continue

            rv.append({
                "kind": "dialogue",
                "identifier": identifier,
                "original": _bb_probe_text(original),
                "translated": _bb_probe_text(translated),
                "location": _bb_probe_loc(translated_node) or _bb_probe_loc(default_node),
            })

        return rv

    def _bb_probe_collect_string_entries(language):
        rv = []

        try:
            strings = renpy.game.script.translator.strings.get(language, None)
            translations = list(strings.translations.items()) if strings is not None else []
        except Exception:
            translations = []

        for index, item in enumerate(translations):
            try:
                original, translated = item
            except Exception:
                continue

            rv.append({
                "kind": "string",
                "identifier": "string:%d" % index,
                "original": _bb_probe_text(original),
                "translated": _bb_probe_text(translated),
                "location": None,
            })

        return rv

    def _bb_probe_collect_menu_entries(language):
        rv = []
        try:
            all_stmts = list(renpy.game.script.all_stmts)
        except Exception:
            all_stmts = []

        index = 0
        for node in all_stmts:
            items = getattr(node, "items", None)
            if not items:
                continue

            for item in items:
                try:
                    label = item[0]
                except Exception:
                    continue
                if not label:
                    continue

                translated = label
                try:
                    translated = renpy.translation.translate_string(label, language)
                except TypeError:
                    try:
                        translated = renpy.translation.translate_string(label)
                    except Exception:
                        translated = label
                except Exception:
                    translated = label

                rv.append({
                    "kind": "menu",
                    "identifier": "menu:%d" % index,
                    "original": _bb_probe_text(label),
                    "translated": _bb_probe_text(translated),
                    "location": _bb_probe_loc(node),
                })
                index += 1

        return rv

    def _bb_probe_detect_language():
        value = os.environ.get("BB_RENDER_PROBE_LANGUAGE", "").strip()
        if value:
            return value

        for name in ("BB_TRANSLATED_LANGUAGE",):
            value = globals().get(name, None)
            if value:
                return value

        try:
            languages = list(renpy.known_languages())
        except Exception:
            languages = []

        for candidate in ("Chinese_E", "chinese", "zh", "zh_CN", "zh_Hans", "schinese"):
            if candidate in languages:
                return candidate

        for candidate in languages:
            if candidate:
                return candidate

        return "chinese"

    def _bb_probe_write_jsonl(handle, record):
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True, default=repr) + "\n")

    def _bb_probe_run():
        started = time.time()
        output = _bb_probe_output_path()
        limit = _bb_probe_limit()
        render = _bb_probe_truthy_env("BB_RENDER_PROBE_RENDER")
        path_mode = os.environ.get("BB_RENDER_PROBE_PATH", "start").strip().lower()
        modes = _bb_probe_mode_names()
        language = _bb_probe_detect_language()

        if path_mode == "load":
            _bb_probe_sync_load_path()
        else:
            _bb_probe_sync_start_path()

        entries = []
        entries.extend(_bb_probe_collect_dialogue_entries(language))
        entries.extend(_bb_probe_collect_string_entries(language))
        entries.extend(_bb_probe_collect_menu_entries(language))

        if limit > 0:
            entries = entries[:limit]

        stats = collections.Counter()
        failures = 0
        checked = 0

        with open(output, "w", encoding="utf-8") as handle:
            _bb_probe_write_jsonl(handle, {
                "type": "meta",
                "language": language,
                "path": path_mode,
                "modes": modes,
                "render": render,
                "entries": len(entries),
                "renpy_version": getattr(renpy, "version", None),
                "game_directory": config.gamedir,
            })

            for entry in entries:
                stats["entry.%s" % entry.get("kind")] += 1

                for mode in modes:
                    old_mode = getattr(persistent, "bb_mode", None)
                    _bb_probe_set_mode(mode)
                    try:
                        cases = _bb_probe_build_display_cases(entry, mode)
                    except Exception as exc:
                        failures += 1
                        _bb_probe_write_jsonl(handle, {
                            "type": "failure",
                            "mode": mode,
                            "case": "build_display_cases",
                            "entry": entry,
                            "error": _bb_probe_exception("build_display_cases", exc),
                        })
                        continue
                    finally:
                        if old_mode is not None:
                            _bb_probe_set_mode(old_mode)

                    for case_name, text, pair, substitution_input, substitution_expected in cases:
                        if text is None:
                            continue

                        checked += 1
                        stats["case.%s" % case_name] += 1

                        for language_name, line_text in pair:
                            if entry.get("kind") == "string" and "{}" in _bb_probe_text(line_text):
                                stats["skipped.string_format_template"] += 1
                                continue

                            try:
                                props = _bb_probe_text_properties(case_name, language_name, line_text)
                            except Exception as exc:
                                failures += 1
                                _bb_probe_write_jsonl(handle, {
                                    "type": "failure",
                                    "mode": mode,
                                    "case": case_name,
                                    "line_language": language_name,
                                    "stage": "text_properties",
                                    "entry": entry,
                                    "text": _bb_probe_short(line_text),
                                    "error": _bb_probe_exception("text_properties", exc),
                                })
                                continue

                            try:
                                _bb_probe_check_text_object(line_text, props, render)
                            except Exception as exc:
                                failures += 1
                                _bb_probe_write_jsonl(handle, {
                                    "type": "failure",
                                    "mode": mode,
                                    "case": case_name,
                                    "line_language": language_name,
                                    "stage": "screen_text_object",
                                    "entry": entry,
                                    "text": _bb_probe_short(line_text),
                                    "props": { k: repr(v) for k, v in props.items() },
                                    "error": _bb_probe_exception("screen_text_object", exc),
                                })

                        if substitution_input is not None:
                            try:
                                substituted_text = _bb_probe_check_say_substitution(substitution_input)
                            except Exception as exc:
                                failures += 1
                                _bb_probe_write_jsonl(handle, {
                                    "type": "failure",
                                    "mode": mode,
                                    "case": case_name,
                                    "stage": "renpy_substitution",
                                    "entry": entry,
                                    "text": _bb_probe_short(substitution_input),
                                    "unescaped_text": _bb_probe_short(text),
                                    "error": _bb_probe_exception("renpy_substitution", exc),
                                })
                            else:
                                if substituted_text != substitution_expected:
                                    failures += 1
                                    _bb_probe_write_jsonl(handle, {
                                        "type": "failure",
                                        "mode": mode,
                                        "case": case_name,
                                        "stage": "renpy_substitution_mismatch",
                                        "entry": entry,
                                        "text": _bb_probe_short(substitution_input),
                                        "expected": _bb_probe_short(substitution_expected),
                                        "actual": _bb_probe_short(substituted_text),
                                    })

            _bb_probe_write_jsonl(handle, {
                "type": "summary",
                "checked_cases": checked,
                "failures": failures,
                "seconds": round(time.time() - started, 3),
                "stats": dict(stats),
            })

        print("[bb-render-probe] wrote %s" % output)
        print("[bb-render-probe] checked_cases=%d failures=%d" % (checked, failures))
        return False

    renpy.arguments.register_command("bb-render-probe", _bb_probe_run, False)
'''


def find_python(game_root: Path) -> Path:
    candidates = sorted(game_root.glob("lib/py3-windows-*/python.exe"))
    if candidates:
        return candidates[0]

    candidates = sorted(game_root.glob("lib/py*-windows-*/python.exe"))
    if candidates:
        return candidates[0]

    raise FileNotFoundError(f"Could not find bundled python.exe under {game_root / 'lib'}")


def find_launcher(game_root: Path) -> Path:
    scripts = sorted(game_root.glob("*.py"))
    if scripts:
        return scripts[0]
    raise FileNotFoundError(f"Could not find Ren'Py launcher .py under {game_root}")


def game_root_from_arg(path: Path) -> Path:
    path = path.resolve()
    if path.name.lower() == "game":
        return path.parent
    if (path / "game").is_dir():
        return path
    raise FileNotFoundError(f"{path} is neither a Ren'Py game root nor a game directory")


def parse_jsonl_summary(report: Path) -> tuple[dict, list[dict]]:
    summary: dict = {}
    failures: list[dict] = []

    if not report.exists():
        return summary, failures

    with report.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if record.get("type") == "summary":
                summary = record
            elif record.get("type") == "failure":
                failures.append(record)

    return summary, failures


def backup_path_for(path: Path) -> Path:
    backup = path.with_name(path.name + ".bbprobe.bak")
    suffix = 0

    while backup.exists():
        suffix += 1
        backup = path.with_name(path.name + f".bbprobe.bak{suffix}")

    return backup


def stash_existing(path: Path) -> Path | None:
    if not path.exists():
        return None

    backup = backup_path_for(path)
    path.replace(backup)
    return backup


def restore_stashed(path: Path, backup: Path | None) -> None:
    if path.exists():
        path.unlink()

    if backup is not None and backup.exists():
        backup.replace(path)


def print_failure_sample(failures: list[dict], limit: int) -> None:
    for index, failure in enumerate(failures[:limit], 1):
        entry = failure.get("entry") or {}
        error = failure.get("error") or {}
        location = entry.get("location") or entry.get("identifier") or "<unknown>"
        print(
            f"{index}. {failure.get('stage')} {failure.get('case')} "
            f"{failure.get('mode')} {location}: "
            f"{error.get('exception_type')}: {error.get('message')}"
        )
        text = failure.get("text")
        if text:
            print(f"   text: {text}")


def run_probe(
    game_root: Path,
    output: Path,
    path_mode: str,
    modes: str,
    language: str | None,
    limit: int,
    render: bool,
    keep_probe: bool,
    plugin: Path | None,
) -> int:
    game_dir = game_root / "game"
    probe_path = game_dir / "zzzz_bb_render_probe.rpy"
    probe_rpyc = game_dir / "zzzz_bb_render_probe.rpyc"
    backup = None
    plugin_target = None
    plugin_rpyc = None
    plugin_backup = None
    plugin_rpyc_backup = None
    savedir = None

    if plugin is not None:
        plugin = plugin.resolve()
        if not plugin.exists():
            raise FileNotFoundError(f"Plugin file does not exist: {plugin}")

        plugin_target = game_dir / plugin.name
        plugin_rpyc = plugin_target.with_suffix(plugin_target.suffix + "c")

    output.parent.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["SDL_VIDEODRIVER"] = "dummy"
    env["SDL_AUDIODRIVER"] = "dummy"
    env["RENPY_DISABLE_JOYSTICK"] = "1"
    env["BB_RENDER_PROBE_OUTPUT"] = str(output)
    env["BB_RENDER_PROBE_PATH"] = path_mode
    env["BB_RENDER_PROBE_MODES"] = modes
    env["BB_RENDER_PROBE_LIMIT"] = str(limit)
    env["BB_RENDER_PROBE_RENDER"] = "1" if render else "0"
    if language:
        env["BB_RENDER_PROBE_LANGUAGE"] = language

    python_exe = find_python(game_root)
    launcher = find_launcher(game_root)
    savedir = Path(tempfile.mkdtemp(prefix="bb-render-probe-saves-"))

    try:
        if probe_path.exists():
            backup = backup_path_for(probe_path)
            probe_path.replace(backup)

        if plugin is not None and plugin_target is not None and plugin_rpyc is not None:
            if plugin.resolve() != plugin_target.resolve():
                plugin_backup = stash_existing(plugin_target)
                plugin_rpyc_backup = stash_existing(plugin_rpyc)
                shutil.copy2(plugin, plugin_target)
                print(f"[bb-render-probe] temporarily installed plugin {plugin} -> {plugin_target}")
            else:
                plugin_target = None
                plugin_rpyc = None

        probe_path.write_text(PROBE_RPY, encoding="utf-8")
        if probe_rpyc.exists():
            probe_rpyc.unlink()
        if plugin_rpyc is not None and plugin_rpyc.exists() and plugin_rpyc_backup is None:
            plugin_rpyc.unlink()

        cmd = [
            str(python_exe),
            str(launcher),
            str(game_root),
            "bb-render-probe",
            "--savedir",
            str(savedir),
        ]

        print(f"[bb-render-probe] running {game_root}")
        proc = subprocess.run(
            cmd,
            cwd=str(game_root),
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=600,
        )

        if proc.stdout:
            print(proc.stdout.rstrip())

        summary, failures = parse_jsonl_summary(output)
        if summary:
            print(
                "[bb-render-probe] summary: "
                f"checked_cases={summary.get('checked_cases')} "
                f"failures={summary.get('failures')} "
                f"seconds={summary.get('seconds')}"
            )
        else:
            print("[bb-render-probe] no summary record was written")

        if failures:
            print_failure_sample(failures, 12)

        if proc.returncode != 0:
            return proc.returncode
        if not summary:
            return 1
        if int(summary.get("failures") or 0) > 0:
            return 1
        return 0

    finally:
        if not keep_probe:
            try:
                if probe_path.exists():
                    probe_path.unlink()
                if probe_rpyc.exists():
                    probe_rpyc.unlink()
            finally:
                if backup is not None and backup.exists():
                    backup.replace(probe_path)
        if plugin_target is not None:
            restore_stashed(plugin_target, plugin_backup)
        if plugin_rpyc is not None:
            restore_stashed(plugin_rpyc, plugin_rpyc_backup)
        if savedir is not None:
            shutil.rmtree(savedir, ignore_errors=True)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Headlessly exercise Better Bilingual text output with Ren'Py itself."
    )
    parser.add_argument("game", type=Path, help="Ren'Py game root or its game directory")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Report JSONL path. Defaults to reports/<game>-<path>.jsonl",
    )
    parser.add_argument(
        "--path",
        choices=("start", "load"),
        default="start",
        help="Plugin lifecycle path to simulate before scanning.",
    )
    parser.add_argument(
        "--modes",
        default="translated,original,translated_first,original_first",
        help="Comma-separated display modes to test.",
    )
    parser.add_argument("--language", help="Translated language key override.")
    parser.add_argument("--limit", type=int, default=0, help="Limit source entries, for quick smoke tests.")
    parser.add_argument("--render", action="store_true", help="Also call Text.render, not just Text.update/visit.")
    parser.add_argument("--keep-probe", action="store_true", help="Leave the temporary .rpy probe in the game dir.")
    parser.add_argument(
        "--plugin",
        type=Path,
        default=Path("zz_better_bilingual_toggle.rpy") if Path("zz_better_bilingual_toggle.rpy").exists() else None,
        help="Plugin .rpy to temporarily install. Defaults to ./zz_better_bilingual_toggle.rpy when present.",
    )
    parser.add_argument(
        "--no-plugin",
        action="store_true",
        help="Do not temporarily copy a plugin into the target game.",
    )

    args = parser.parse_args(argv)
    game_root = game_root_from_arg(args.game)

    if args.output is None:
        safe_name = game_root.name.replace(" ", "_")
        args.output = Path("reports") / f"bb_render_probe_{safe_name}_{args.path}.jsonl"

    return run_probe(
        game_root=game_root,
        output=args.output.resolve(),
        path_mode=args.path,
        modes=args.modes,
        language=args.language,
        limit=args.limit,
        render=args.render,
        keep_probe=args.keep_probe,
        plugin=None if args.no_plugin else args.plugin,
    )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
