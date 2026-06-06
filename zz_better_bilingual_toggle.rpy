## Better Bilingual Toggle for Lessons in Love Chinese builds.
##
## This version keeps Ren'Py's real language on the Chinese translation so the
## translated script and translated images stay reachable, then treats English
## and bilingual output as display modes.

init -999 python:
    try:
        import sys as _bb_screen_sys
        import types as _bb_screen_types
        import renpy.display.core as _bb_position_core
        import renpy.display.layout as _bb_position_layout
        import renpy.display.motion as _bb_position_motion
        import renpy.display.transform as _bb_position_transform
        import renpy.atl as _bb_position_atl

        if "renpy.display.position" not in _bb_screen_sys.modules:
            _bb_position_module = _bb_screen_types.ModuleType("renpy.display.position")
            _bb_position_sources = (
                _bb_position_layout,
                _bb_position_core,
                _bb_position_motion,
                _bb_position_transform,
                _bb_position_atl,
            )

            def _bb_position_getattr(name):
                for _source in _bb_position_sources:
                    if hasattr(_source, name):
                        return getattr(_source, name)
                raise AttributeError(name)

            _bb_position_module.__getattr__ = _bb_position_getattr
            _bb_position_module.Position = _bb_position_layout.Position
            _bb_position_module.position = _bb_position_atl.position
            _bb_position_module.absolute = _bb_position_core.absolute
            _bb_screen_sys.modules["renpy.display.position"] = _bb_position_module
            renpy.display.position = _bb_position_module
    except Exception:
        pass

init 20 python:
    import math
    import re
    import sys

    BB_LANGUAGE_CANDIDATES = (
        "Chinese_E",
        "chinese",
        "zh",
        "zh_CN",
        "zh_Hans",
        "schinese",
    )

    BB_MODE_TRANSLATED = "translated"
    BB_MODE_ORIGINAL = "original"
    BB_MODE_TRANSLATED_FIRST = "translated_first"
    BB_MODE_ORIGINAL_FIRST = "original_first"
    BB_MODES = (
        BB_MODE_TRANSLATED,
        BB_MODE_ORIGINAL,
        BB_MODE_TRANSLATED_FIRST,
        BB_MODE_ORIGINAL_FIRST,
    )

    BB_ORIGINAL_FONT_ALIAS = "bb_original_dialogue_font"
    BB_TRANSLATED_FONT_ALIAS = "bb_translated_dialogue_font"
    BB_DEBUG = False

    BB_SAVE_SLOT_REGEXP = r"^(?:auto|quick|\d+)-\d+$"
    BB_OLD_SUBSTITUTION_SAFE_PERCENT_RE = re.compile(
        r"%%|%\([^)]+\)[#0 +\-]*(?:\*|\d+)?(?:\.(?:\*|\d+))?[hlL]?[diouxXeEfFgGcrs]"
    )

    def bb_log(message):
        try:
            renpy.log("[better-bilingual] %s" % message)
        except Exception:
            pass

    def bb_debug_value(value, limit=90):
        try:
            rv = repr(value)
        except Exception:
            rv = "<repr failed: %s>" % type(value).__name__

        if len(rv) > limit:
            rv = rv[:limit] + "...<%d chars>" % len(rv)

        return rv

    def bb_debug_font(font):
        try:
            return "%s %s" % (type(font).__name__, bb_debug_value(font, 140))
        except Exception:
            return "<font debug failed>"

    def bb_debug(message):
        return

    def bb_known_languages():
        try:
            rv = list(renpy.known_languages())
            return rv
        except Exception as e:
            return []

    def bb_detect_language():
        known = bb_known_languages()

        for value in (
            getattr(_preferences, "language", None),
            getattr(config, "language", None),
        ):
            if value and value in BB_LANGUAGE_CANDIDATES and (not known or value in known):
                return value

        for candidate in BB_LANGUAGE_CANDIDATES:
            if candidate in known:
                return candidate

        for candidate in known:
            if candidate:
                return candidate

        return "Chinese_E"

    BB_TRANSLATED_LANGUAGE = bb_detect_language()

    def bb_clear_dialogue_metrics_cache():
        try:
            bb_dialogue_metrics_cache.clear()
        except Exception:
            pass

    def bb_runtime_cache():
        try:
            cache = getattr(renpy.game.script, "_bb_bilingual_runtime_cache", None)
            if cache is None:
                cache = {}
                setattr(renpy.game.script, "_bb_bilingual_runtime_cache", cache)
            return cache
        except Exception:
            return {}

    def bb_reset_progress_event_title_cache():
        try:
            bb_runtime_cache().pop("progress_event_title_originals", None)
        except Exception:
            pass

    def bb_original_font():
        return bb_runtime_cache().get("original_dialogue_font", None)

    def bb_set_original_font(font):
        bb_runtime_cache()["original_dialogue_font"] = font

    def bb_translated_font():
        return bb_runtime_cache().get("translated_dialogue_font", None)

    def bb_set_translated_font(font):
        bb_runtime_cache()["translated_dialogue_font"] = font

    def bb_font_signature(font):
        try:
            return repr(font)
        except Exception:
            return str(type(font))

    def bb_resolve_font(font):
        seen = set()

        while isinstance(font, str) and font in config.font_name_map and font not in seen:
            seen.add(font)
            font = config.font_name_map[font]

        return font

    def bb_current_dialogue_font():
        for getter in (
            lambda: gui.dialogue_text_font,
            lambda: gui.text_font,
            lambda: style.say_dialogue.font,
            lambda: style.default.font,
        ):
            try:
                font = getter()
            except Exception:
                continue

            if font is not None:
                return font

        return None

    def bb_register_font_alias(alias, font):
        if font is None:
            return None

        resolved = bb_resolve_font(font)

        try:
            old = config.font_name_map.get(alias, None)
            if bb_font_signature(old) == bb_font_signature(resolved):
                return alias
            config.font_name_map[alias] = resolved
        except Exception as e:
            bb_log("could not register font alias %s: %r" % (alias, e))
            return None

        bb_clear_dialogue_metrics_cache()

        return alias

    def bb_capture_original_font():
        font = bb_original_font()

        if font is None:
            font = bb_current_dialogue_font()
            bb_set_original_font(font)

        return bb_register_font_alias(BB_ORIGINAL_FONT_ALIAS, font)

    def bb_capture_translated_font():
        font = bb_current_dialogue_font()
        if font is not None:
            bb_set_translated_font(font)

        return bb_register_font_alias(BB_TRANSLATED_FONT_ALIAS, bb_translated_font())

    def bb_reset_translated_font():
        bb_set_translated_font(None)
        bb_clear_dialogue_metrics_cache()

    def bb_capture_current_fonts():
        bb_capture_original_font()

        try:
            language = getattr(_preferences, "language", None)
        except Exception:
            language = None

        if (
            bb_translated_font() is None
            and language == BB_TRANSLATED_LANGUAGE
            and bb_applied_language() == BB_TRANSLATED_LANGUAGE
        ):
            bb_capture_translated_font()

    bb_clear_say_ranges_next_interact = False
    bb_current_empty_window = config.empty_window
    bb_base_empty_window = getattr(
        bb_current_empty_window,
        "_bb_base_empty_window",
        bb_current_empty_window,
    )
    bb_sayexports_module = sys.modules.get("renpy.exports.sayexports", None)
    bb_current_say = renpy.exports.say
    bb_base_say = getattr(bb_current_say, "_bb_base_say", bb_current_say)

    def bb_sync_engine_language():
        """Keep Ren'Py executing the translated script while this mod changes display."""

        try:
            old = getattr(config, "language", None)
            config.language = BB_TRANSLATED_LANGUAGE
        except Exception as e:
            bb_log("could not set config.language: %r" % e)

        try:
            old = getattr(_preferences, "language", None)
            _preferences.language = BB_TRANSLATED_LANGUAGE
        except Exception as e:
            bb_log("could not set _preferences.language: %r" % e)

        try:
            old = getattr(renpy.game.preferences, "language", None)
            renpy.game.preferences.language = BB_TRANSLATED_LANGUAGE
        except Exception as e:
            bb_log("could not set game.preferences.language: %r" % e)

        if bb_applied_language() == BB_TRANSLATED_LANGUAGE:
            try:
                contexts = list(renpy.game.contexts)
            except Exception:
                contexts = []

            for ctx in contexts:
                try:
                    old = getattr(ctx, "translate_language", None)
                    ctx.translate_language = BB_TRANSLATED_LANGUAGE
                except Exception:
                    pass

    def bb_escape_old_substitution_percents(text):
        if not isinstance(text, str) or "%" not in text:
            return text

        placeholders = []

        def keep_placeholder(match):
            placeholders.append(match.group(0))
            return "\x00BBFMT%d\x00" % (len(placeholders) - 1)

        rv = BB_OLD_SUBSTITUTION_SAFE_PERCENT_RE.sub(keep_placeholder, text)
        rv = rv.replace("%", "%%")

        for index, value in enumerate(placeholders):
            rv = rv.replace("\x00BBFMT%d\x00" % index, value)

        return rv

    def bb_say(who, what, *args, **kwargs):

        if getattr(config, "old_substitutions", False):
            what = bb_escape_old_substitution_percents(what)

        return bb_base_say(who, what, *args, **kwargs)

    def bb_normalize_mode(mode):
        if mode is True:
            return BB_MODE_ORIGINAL

        if mode is False or mode is None:
            return BB_MODE_TRANSLATED

        if mode in BB_MODES:
            return mode

        return BB_MODE_TRANSLATED

    def bb_init_persistent():
        if not hasattr(persistent, "bb_mode"):
            if hasattr(persistent, "ll_better_bilingual_mode"):
                persistent.bb_mode = bb_normalize_mode(persistent.ll_better_bilingual_mode)
            elif hasattr(persistent, "ll_fast_original_mode"):
                persistent.bb_mode = bb_normalize_mode(persistent.ll_fast_original_mode)
            else:
                persistent.bb_mode = BB_MODE_TRANSLATED

        if not hasattr(persistent, "ll_fast_original_mode"):
            persistent.ll_fast_original_mode = bb_current_mode() in (
                BB_MODE_ORIGINAL,
                BB_MODE_ORIGINAL_FIRST,
            )

        persistent.ll_better_bilingual_mode = bb_current_mode()

        if not hasattr(persistent, "dialogue_text_size") or persistent.dialogue_text_size is None:
            try:
                persistent.dialogue_text_size = gui.text_size
            except Exception:
                persistent.dialogue_text_size = 38

    def bb_current_mode():
        return bb_normalize_mode(getattr(persistent, "bb_mode", BB_MODE_TRANSLATED))

    def bb_is_original_mode():
        return bb_current_mode() in (BB_MODE_ORIGINAL, BB_MODE_ORIGINAL_FIRST)

    def bb_is_bilingual_mode():
        return bb_current_mode() in (BB_MODE_TRANSLATED_FIRST, BB_MODE_ORIGINAL_FIRST)

    def bb_mode_name():
        mode = bb_current_mode()

        if mode == BB_MODE_ORIGINAL:
            return "EN"
        if mode == BB_MODE_TRANSLATED_FIRST:
            return "中/EN"
        if mode == BB_MODE_ORIGINAL_FIRST:
            return "EN/中"
        return "中"

    def bb_pair_from_values(translated, original):
        mode = bb_current_mode()

        if translated is None:
            translated = original
        if original is None:
            original = translated

        if mode == BB_MODE_ORIGINAL:
            return [(BB_MODE_ORIGINAL, original)]

        if mode == BB_MODE_TRANSLATED_FIRST:
            return [
                (BB_MODE_TRANSLATED, translated),
                (BB_MODE_ORIGINAL, original),
            ]

        if mode == BB_MODE_ORIGINAL_FIRST:
            return [
                (BB_MODE_ORIGINAL, original),
                (BB_MODE_TRANSLATED, translated),
            ]

        return [(BB_MODE_TRANSLATED, translated)]

    def bb_applied_language():
        try:
            return renpy.translation.old_language
        except Exception:
            return None

    def bb_font_alias_ready(alias):
        try:
            rv = alias in config.font_name_map
            return rv
        except Exception as e:
            return False

    def bb_language_for_text(language, text=None):
        if language == BB_MODE_ORIGINAL:
            if not bb_font_alias_ready(BB_ORIGINAL_FONT_ALIAS):
                bb_capture_original_font()
            return BB_ORIGINAL_FONT_ALIAS

        if bb_translated_font() is None and bb_applied_language() == BB_TRANSLATED_LANGUAGE:
            bb_capture_translated_font()

        if not bb_font_alias_ready(BB_TRANSLATED_FONT_ALIAS):
            bb_register_font_alias(
                BB_TRANSLATED_FONT_ALIAS,
                bb_translated_font() or bb_original_font() or bb_current_dialogue_font(),
            )

        return BB_TRANSLATED_FONT_ALIAS

    def bb_progress_event_titles_use_original():
        return bb_current_mode() in (BB_MODE_ORIGINAL, BB_MODE_ORIGINAL_FIRST)

    def bb_progress_event_titles_need_custom_translation():
        return bb_progress_event_titles_use_original() or bb_is_bilingual_mode()

    def bb_progress_event_objects():
        try:
            store_values = list(vars(renpy.store).items())
        except Exception:
            return []

        rv = []
        for name, value in store_values:
            if not name.startswith("ev_"):
                continue

            try:
                if value.__class__.__name__ != "Event":
                    continue
            except Exception:
                continue

            rv.append(value)

        return rv

    def bb_progress_event_original_name(event):
        try:
            original = getattr(event, "_bb_original_name", None)
            if isinstance(original, str):
                return original

            original = event.__dict__.get("name", None)
            if isinstance(original, str):
                return original
        except Exception:
            pass

        return None

    def bb_progress_event_visible_title_length(*values):
        rv = 0

        for value in values:
            if not isinstance(value, str):
                continue

            try:
                plain = re.sub(r"\{[^}]*\}", "", value)
            except Exception:
                plain = value

            for line in plain.splitlines() or [plain]:
                rv = max(rv, len(line))

        return rv

    def bb_progress_event_translated_title(text):
        try:
            return bb_base_translate_string(text, BB_TRANSLATED_LANGUAGE)
        except Exception:
            return text

    def bb_progress_event_title_text(text):
        if not isinstance(text, str):
            return text

        translated = bb_progress_event_translated_title(text)

        if bb_is_bilingual_mode():
            value = bb_join_pair(
                bb_pair_from_values(translated, text),
                with_fonts=True,
            )
            return value

        if bb_progress_event_titles_use_original():
            return text

        return translated

    def bb_progress_event_color(event):
        try:
            var_name = getattr(event, "var_name", "")
            if "lust" in var_name or var_name in ["day98", "day68", "day86"]:
                return "FF85FD"
            if "invite" in var_name:
                return "778EFF"
        except Exception:
            pass

        return None

    def bb_progress_wrap_text_tag(text, start, end):
        if not isinstance(text, str):
            return text

        lines = text.split("\n")
        return "\n".join([start + line + end for line in lines])

    def bb_progress_event_colored_title_text(text, color):
        if not isinstance(text, str) or not color:
            return bb_progress_event_title_text(text)

        colored_original = "{color=%s}%s{/color}" % (color, text)
        colored_translated = bb_progress_event_translated_title(colored_original)

        if colored_translated == colored_original:
            malformed_colored_original = "{color=%s}%s{/size}" % (color, text)
            malformed_colored_translated = bb_progress_event_translated_title(malformed_colored_original)
            if malformed_colored_translated != malformed_colored_original:
                colored_translated = malformed_colored_translated

        if colored_translated != colored_original:
            if bb_is_bilingual_mode():
                return bb_join_pair(
                    bb_pair_from_values(colored_translated, colored_original),
                    with_fonts=True,
                )

            if bb_progress_event_titles_use_original():
                return colored_original

            return colored_translated

        return bb_progress_wrap_text_tag(
            bb_progress_event_title_text(text),
            "{color=%s}" % color,
            "{/color}",
        )

    def bb_progress_read_loader_text(path):
        try:
            f = renpy.loader.load(path)
        except Exception:
            return ""

        try:
            data = f.read()
        except Exception:
            data = ""

        try:
            f.close()
        except Exception:
            pass

        if isinstance(data, bytes):
            try:
                return data.decode("utf-8")
            except Exception:
                return data.decode("utf-8", "replace")

        return data if isinstance(data, str) else ""

    def bb_progress_missed_event_titles():
        cache = bb_runtime_cache()
        rv = cache.get("progress_missed_event_titles", None)
        if rv is not None:
            return rv

        rv = {}
        tracker_paths = (
            "progress mod/trackers/ch1tracker.rpy",
            "progress mod/trackers/ch2tracker.rpy",
            "progress mod/trackers/ch3tracker.rpy",
            "progress mod/trackers/ch4tracker.rpy",
            "progress mod/trackers/girltracker.rpy",
            "progress mod/trackers/happytracker.rpy",
        )

        for path in tracker_paths:
            text = bb_progress_read_loader_text(path)
            if not text:
                continue

            lines = text.splitlines()
            for index, line in enumerate(lines):
                if ".missed" not in line or "ev_" not in line:
                    continue

                match = re.search(r"ev_([A-Za-z0-9_]+)\.missed", line)
                if not match:
                    continue

                for follow in lines[index + 1:index + 7]:
                    title_match = re.search(
                        r"""text(?:button)?\s+_\(\s*(['"])(\{color=EF1A1A\}\{s\}.*?\{/s\}\{/color\})\1""",
                        follow,
                    )
                    if title_match:
                        rv[match.group(1)] = title_match.group(2)
                        break

        cache["progress_missed_event_titles"] = rv
        return rv

    def bb_progress_missed_event_title_text(event):
        try:
            var_name = getattr(event, "var_name", "")
            title = bb_progress_missed_event_titles().get(var_name, None)
        except Exception:
            title = None

        if title:
            return bb_progress_event_title_text(title)

        return None

    def bb_progress_hint_event_title(event):
        title = bb_progress_event_original_name(event)
        if title is None:
            title = getattr(event, "name", "")

        color = bb_progress_event_color(event)
        if color:
            return bb_progress_event_colored_title_text(title, color)

        return bb_progress_event_title_text(title)

    def bb_progress_hint_rows():
        try:
            hint_keys = set(ProgressMod.current_hints.keys())
        except Exception:
            hint_keys = set()

        rows = []

        try:
            main_chapter = "maintrackerch" + str(current_chapter) + "m"
        except Exception:
            main_chapter = "maintrackerch1m"

        def add_row(event, girl_label, girl_screen=None, showgirl_name=None, girl_text_style="hint_text", happy=False):
            try:
                if getattr(event, "var_name", None) not in hint_keys:
                    return

                hint = getattr(event, "hint", "")
                if happy and not show_happy_hints:
                    hint = ""

                rows.append({
                    "event": event,
                    "girl_label": girl_label,
                    "girl_screen": girl_screen,
                    "showgirl_name": showgirl_name,
                    "girl_text_style": girl_text_style,
                    "event_title": bb_progress_hint_event_title(event),
                    "hint": hint,
                    "hint_action": "(!)" in hint,
                })
            except Exception:
                pass

        try:
            main_label = "Main event" if dark_mode else MainEvent.colored_name
            for event in MainEvent.event_list:
                add_row(event, main_label, girl_screen=main_chapter)
        except Exception:
            pass

        try:
            for event in HappyEvent.event_list:
                add_row(event, HappyEvent.colored_name, girl_screen="secrettrackerm", happy=True)
        except Exception:
            pass

        try:
            for girl in ProgressMod.all_girls:
                if girl in [MainEvent, HappyEvent] or not girl.active:
                    continue

                for event in girl.event_list:
                    add_row(
                        event,
                        girl.colored_name,
                        girl_screen="amitrackerm2",
                        showgirl_name=girl.name,
                        girl_text_style="amihint",
                    )
        except Exception:
            pass

        return rows

    def bb_progress_text_style_for_girl(girl, suffix="mod"):
        try:
            name = getattr(girl, "name", "")
            if not isinstance(name, str) or not name:
                return "mod"

            if suffix == "mod" and dark_mode and name in ("Io", "Touka", "Tsubasa", "Yuki"):
                return name.lower() + "mod_dark"

            return name.lower() + suffix
        except Exception:
            return "mod"

    def bb_progress_event_colored_title(event, completed=False, missed=False):
        if completed:
            title = bb_progress_event_original_name(event)
            if title is None:
                title = getattr(event, "name", "")
            title = bb_progress_event_title_text("%s {b}\u2713{/b}" % title)
        else:
            title = bb_progress_hint_event_title(event)

        if missed:
            missed_title = bb_progress_missed_event_title_text(event)
            if missed_title:
                return missed_title

            title = bb_progress_event_original_name(event)
            if title is None:
                title = getattr(event, "name", "")
            title = bb_progress_wrap_text_tag(
                bb_progress_event_title_text(title),
                "{color=EF1A1A}{s}",
                "{/s}{/color}",
            )

        return title

    def bb_progress_tracker_row(event, previous_screen):
        try:
            completed = bool(getattr(event, "completed", False))
            missed = bool(getattr(event, "missed", False))
            visible = (not completed and not missed) or bool(show_complete)
        except Exception:
            visible = False

        if not visible:
            return None

        hint = ""
        hint_action = False

        try:
            if show_hints and not _in_replay:
                hint = getattr(event, "hint", "") or ""
                hint_action = "(!)" in hint
        except Exception:
            pass

        return {
            "event": event,
            "completed": completed,
            "missed": missed,
            "title": bb_progress_event_colored_title(event, completed=completed, missed=missed),
            "hint": hint,
            "hint_action": hint_action,
            "previous_screen": previous_screen,
        }

    def bb_progress_main_rows(chapter):
        rows = []

        try:
            chapter = int(chapter)
        except Exception:
            chapter = 1

        try:
            for event in MainEvent.event_list:
                if getattr(event, "chapter", None) != chapter:
                    continue

                row = bb_progress_tracker_row(event, "main")
                if row is not None:
                    row["previous_screen"] = "maintrackerch%dm" % chapter
                    rows.append(row)
        except Exception as e:
            bb_log("could not build main tracker rows: %r" % e)

        return rows

    def bb_progress_current_girl():
        try:
            girl = eval(showgirl)
            if getattr(girl, "__class__", None).__name__ in ("Girl", "StoryEvent"):
                return girl
        except Exception:
            pass

        try:
            for girl in ProgressMod.all_girls:
                if getattr(girl, "name", None) == showgirl:
                    return girl
        except Exception:
            pass

        return None

    def bb_progress_girl_points(girl):
        try:
            name = getattr(girl, "name", "").lower()
            return eval(name + "point") + eval(name + "miss")
        except Exception:
            return 0

    def bb_progress_girl_thumbnail(girl):
        try:
            name = getattr(girl, "name", "")
            if not isinstance(name, str) or not name:
                return None

            return "images/" + name.lower() + "thumb1.png"
        except Exception:
            return None

    def bb_progress_girl_thumbnail_idle(girl):
        path = bb_progress_girl_thumbnail(girl)
        if not path:
            return path

        try:
            if getattr(girl, "has_hint", False) or not desaturate_girls:
                return path

            return im.Grayscale(path)
        except Exception:
            return path

    def bb_progress_girl_rows():
        rows = []

        try:
            girl = bb_progress_current_girl()
            if girl is None:
                return rows

            for event in getattr(girl, "event_list", []):
                row = bb_progress_tracker_row(event, "girls")
                if row is not None:
                    rows.append(row)
        except Exception as e:
            bb_log("could not build girl tracker rows: %r" % e)

        return rows

    def bb_progress_main_prev_screen(chapter):
        try:
            chapter = int(chapter)
        except Exception:
            chapter = 1

        return "maintrackerch%dm" % max(1, chapter - 1)

    def bb_progress_main_next_screen(chapter):
        try:
            chapter = int(chapter)
        except Exception:
            chapter = 1

        try:
            max_main_chapter = int(getattr(MainEvent.event_list[-1], "chapter", chapter))
        except Exception:
            max_main_chapter = chapter

        return "maintrackerch%dm" % min(max_main_chapter, chapter + 1)

    def bb_progress_girl_header():
        girl = bb_progress_current_girl()
        if girl is None:
            return ""

        try:
            love = eval(getattr(girl, "name", "").lower() + "_love")
            lust = eval(getattr(girl, "name", "").lower() + "_lust")
        except Exception:
            return getattr(girl, "colored_name", getattr(girl, "name", ""))

        try:
            if lust == "N/A":
                return "%s (%s Affection)" % (getattr(girl, "colored_name", girl.name), love)

            return "%s (%s Affection/%s Lust)" % (getattr(girl, "colored_name", girl.name), love, lust)
        except Exception:
            return getattr(girl, "colored_name", getattr(girl, "name", ""))

    def bb_progress_visible_girls():
        rows = []

        try:
            for girl in ProgressMod.all_girls:
                if girl in [MainEvent, HappyEvent] or not getattr(girl, "active", False):
                    continue

                if not show_completed_girls:
                    try:
                        max_values = getattr(girl, "max", None)
                        chapter_max = None

                        try:
                            chapter_max = max_values[current_chapter]
                        except Exception:
                            chapter_max = getattr(girl, "current_max", 0)

                        if bb_progress_girl_points(girl) == chapter_max:
                            continue
                    except Exception:
                        pass

                rows.append(girl)
        except Exception as e:
            bb_log("could not build visible girl list: %r" % e)

        return rows

    def bb_progress_visible_girl_rows():
        first_row_names = (
            "Ami", "Ayane", "Chika", "Chinami", "Futaba", "Haruka",
            "Imani", "Io", "Kaori", "Karin", "Kirin", "Maki",
            "Makoto", "Maya", "Miku", "Molly", "Nao", "Niki",
        )
        first_row_names = set(first_row_names)

        row_one = []
        row_two = []

        for girl in bb_progress_visible_girls():
            try:
                name = getattr(girl, "name", "")
            except Exception:
                name = ""

            if name in first_row_names:
                row_one.append(girl)
            else:
                row_two.append(girl)

        rows = []
        for row in (row_one, row_two):
            while row:
                rows.append(row[:18])
                row = row[18:]

        return rows

    def bb_add_progress_event_title(titles, text):
        if not isinstance(text, str) or not text:
            return

        titles.add(text)

        check_suffix = " {b}\u2713{/b}"
        if text.endswith(check_suffix):
            titles.add(text[:-len(check_suffix)])

    def bb_collect_translated_event_titles(titles):
        check_suffix = " {b}\u2713{/b}"

        try:
            strings = renpy.game.script.translator.strings.get(BB_TRANSLATED_LANGUAGE, None)
            translations = strings.translations if strings is not None else {}
        except Exception:
            translations = {}

        try:
            keys = list(translations.keys())
        except Exception:
            keys = []

        for text in keys:
            if not isinstance(text, str):
                continue

            if text.endswith(check_suffix):
                bb_add_progress_event_title(titles, text)
                continue

            if "{s}" in text and "{/s}" in text:
                bb_add_progress_event_title(titles, text)

    def bb_progress_event_title_originals():
        cache = bb_runtime_cache()
        titles = cache.get("progress_event_title_originals", None)
        if titles is not None:
            return titles

        titles = set()
        for event in bb_progress_event_objects():
            original = bb_progress_event_original_name(event)
            if not original:
                continue

            bb_add_progress_event_title(titles, original)
            bb_add_progress_event_title(titles, "%s {b}\u2713{/b}" % original)

        bb_collect_translated_event_titles(titles)
        cache["progress_event_title_originals"] = titles
        return titles

    def bb_is_progress_event_title_string(text):
        if not isinstance(text, str):
            return False

        return text in bb_progress_event_title_originals()

    def bb_progress_event_name_getter(event):
        original = bb_progress_event_original_name(event)
        if original is None:
            return ""

        return bb_progress_event_title_text(original)

    def bb_progress_event_name_setter(event, value):
        try:
            event._bb_original_name = value
        except Exception:
            pass

        try:
            event.__dict__["name"] = value
        except Exception:
            pass

    def bb_patch_progress_event_names():
        event_class = None
        titles = bb_runtime_cache().get("progress_event_title_originals", None)

        if titles is not None:
            bb_collect_translated_event_titles(titles)

        for event in bb_progress_event_objects():
            original = bb_progress_event_original_name(event)
            if original is not None:
                try:
                    event._bb_original_name = original
                except Exception:
                    pass

                if titles is not None:
                    bb_add_progress_event_title(titles, original)
                    bb_add_progress_event_title(titles, "%s {b}\u2713{/b}" % original)

            try:
                event_class = event.__class__
            except Exception:
                pass

        if event_class is None:
            bb_patch_progress_update_all()
            return

        try:
            if not getattr(event_class, "_bb_name_property_installed", False):
                event_class.name = property(
                    bb_progress_event_name_getter,
                    bb_progress_event_name_setter,
                )
                event_class._bb_name_property_installed = True
        except Exception as e:
            bb_log("could not patch progress event names: %r" % e)

        bb_patch_progress_update_all()

    def bb_recalculate_progress_longest_name(progress_mod):
        try:
            longest = 0
            current_hints = getattr(progress_mod, "current_hints", {})

            for girl in getattr(progress_mod, "all_girls", []):
                for event in getattr(girl, "event_list", []):
                    if getattr(event, "var_name", None) not in current_hints:
                        continue

                    name = bb_progress_event_original_name(event)
                    translated = bb_progress_event_translated_title(name)
                    longest = max(
                        longest,
                        bb_progress_event_visible_title_length(name, translated),
                    )

            progress_mod.longest_name = longest
        except Exception as e:
            bb_log("could not recalculate progress longest_name: %r" % e)

    def bb_patch_progress_update_all():
        try:
            progress_mod = getattr(renpy.store, "ProgressMod", None)
            progress_class = progress_mod.__class__ if progress_mod is not None else None
            update_all = getattr(progress_class, "update_all", None)
        except Exception:
            return

        if progress_mod is None or progress_class is None or update_all is None:
            return

        if getattr(update_all, "_bb_progress_update_all", False):
            return

        def bb_progress_update_all(self, *args, **kwargs):
            rv = update_all(self, *args, **kwargs)
            bb_recalculate_progress_longest_name(self)
            return rv

        bb_progress_update_all._bb_progress_update_all = True

        try:
            progress_class.update_all = bb_progress_update_all
        except Exception as e:
            bb_log("could not patch progress update_all: %r" % e)

    bb_translation_default = renpy.translation.Default
    bb_base_translate_string = getattr(
        renpy.translation,
        "_bb_base_translate_string",
        renpy.translation.translate_string,
    )

    def bb_translate_string(text, language=bb_translation_default):
        if (
            language is bb_translation_default
            and bb_progress_event_titles_need_custom_translation()
            and bb_is_progress_event_title_string(text)
        ):
            return bb_progress_event_title_text(text)

        return bb_base_translate_string(text, language)

    if not hasattr(renpy.translation, "_bb_base_translate_string"):
        renpy.translation._bb_base_translate_string = bb_base_translate_string

    renpy.translation.translate_string = bb_translate_string
    renpy.translate_string = bb_translate_string
    try:
        renpy.exports.translate_string = bb_translate_string
    except Exception:
        pass
    try:
        renpy.store.__ = bb_translate_string
    except Exception:
        pass

    def bb_font_tag(language, text):
        if text is None:
            return ""

        alias = bb_language_for_text(language, text)
        rv = "{font=%s}%s{/font}" % (alias, text)
        return rv

    def bb_join_pair(pair, with_fonts=False):
        lines = []
        seen = set()

        for language, value in pair:
            if value is None or value in seen:
                continue

            if with_fonts:
                lines.append(bb_font_tag(language, value))
            else:
                lines.append(value)

            seen.add(value)

        return "\n".join(lines)

    def bb_strip_font_tags(text):
        if not isinstance(text, str):
            return text

        return re.sub(r"\{/?font(?:=[^}]*)?\}", "", text)

    def bb_font_line_language(line):
        if not isinstance(line, str):
            return None

        font_match = re.search(r"\{font=([^}]*)\}", line)
        if not font_match:
            return None

        font = font_match.group(1)
        if font == BB_ORIGINAL_FONT_ALIAS:
            return BB_MODE_ORIGINAL
        if font == BB_TRANSLATED_FONT_ALIAS:
            return BB_MODE_TRANSLATED
        return None

    def bb_split_history_pair_text(text):
        if not isinstance(text, str) or "\n" not in text:
            return (None, None)

        raw_lines = [line.strip() for line in text.splitlines() if line.strip()]
        lines = [bb_strip_font_tags(line) for line in raw_lines]
        if len(lines) < 2:
            return (None, None)

        first_language = bb_font_line_language(raw_lines[0])
        second_language = bb_font_line_language(raw_lines[1])
        first = lines[0]
        second = "\n".join(lines[1:])

        if first_language == BB_MODE_TRANSLATED and second_language == BB_MODE_ORIGINAL:
            return (bb_substitute(first), bb_substitute(second))
        if first_language == BB_MODE_ORIGINAL and second_language == BB_MODE_TRANSLATED:
            return (bb_substitute(second), bb_substitute(first))

        bb_build_history_dialogue_maps()

        if first in bb_original_to_translated:
            return (bb_substitute(bb_original_to_translated.get(first, second)), bb_substitute(first))

        if first in bb_translated_to_original:
            return (bb_substitute(first), bb_substitute(bb_translated_to_original.get(first, second)))

        if second in bb_original_to_translated:
            return (bb_substitute(bb_original_to_translated.get(second, first)), bb_substitute(second))

        if second in bb_translated_to_original:
            return (bb_substitute(second), bb_substitute(bb_translated_to_original.get(second, first)))

        if bb_current_mode() == BB_MODE_TRANSLATED_FIRST:
            return (bb_substitute(first), bb_substitute(second))

        if bb_current_mode() == BB_MODE_ORIGINAL_FIRST:
            return (bb_substitute(second), bb_substitute(first))

        return (None, None)

    def bb_current_identifier():
        try:
            ctx = renpy.game.context()
            return ctx.translate_identifier or ctx.deferred_translate_identifier
        except Exception:
            return None

    def bb_identifier_candidates(identifier):
        if not identifier:
            return []

        rv = []
        for value in (identifier, identifier.replace(".", "_")):
            if value and value not in rv:
                rv.append(value)
        return rv

    def bb_node_text(node):
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

    def bb_node_text_for_identifier(identifier, language=None):
        if not identifier:
            return None

        try:
            tl = renpy.game.script.translator
        except Exception as e:
            return None

        for candidate in bb_identifier_candidates(identifier):
            if language is None:
                node = tl.default_translates.get(candidate, None)
            else:
                node = tl.language_translates.get((candidate, language), None)

            text = bb_node_text(node)
            if text is not None:
                return text

        return None

    def bb_substitute(text):
        if text is None:
            return None

        original = text

        try:
            if config.old_substitutions:
                text = bb_escape_old_substitution_percents(text)
                text = text % renpy.exports.tag_quoting_dict
        except Exception:
            pass

        try:
            rv = renpy.substitutions.substitute(text, translate=False)[0]
            return rv
        except Exception as e:
            return text

    bb_string_maps_ready = False
    bb_history_dialogue_maps_ready = False
    bb_original_to_translated = {}
    bb_translated_to_original = {}

    def bb_reset_text_maps():
        global bb_string_maps_ready
        global bb_history_dialogue_maps_ready

        bb_string_maps_ready = False
        bb_history_dialogue_maps_ready = False

        try:
            bb_original_to_translated.clear()
            bb_translated_to_original.clear()
        except Exception:
            pass

        bb_reset_progress_event_title_cache()

    def bb_build_string_maps():
        global bb_string_maps_ready

        if bb_string_maps_ready:
            return

        try:
            strings = renpy.game.script.translator.strings.get(BB_TRANSLATED_LANGUAGE, None)
            if strings is not None:
                for original, translated in strings.translations.items():
                    bb_original_to_translated.setdefault(original, translated)
                    bb_translated_to_original.setdefault(translated, original)
        except Exception as e:
            bb_log("could not build string map: %r" % e)

        bb_string_maps_ready = True

    def bb_build_history_dialogue_maps():
        global bb_history_dialogue_maps_ready

        if bb_history_dialogue_maps_ready:
            return

        bb_build_string_maps()

        try:
            tl = renpy.game.script.translator
            for identifier, default_node in tl.default_translates.items():
                translated_node = tl.language_translates.get((identifier, BB_TRANSLATED_LANGUAGE), None)
                original = bb_node_text(default_node)
                translated = bb_node_text(translated_node)

                if original is None or translated is None:
                    continue

                original = bb_substitute(original)
                translated = bb_substitute(translated)

                if original is None or translated is None:
                    continue

                bb_original_to_translated.setdefault(original, translated)
                bb_translated_to_original.setdefault(translated, original)
        except Exception as e:
            bb_log("could not build history dialogue map: %r" % e)

        bb_history_dialogue_maps_ready = True

    def bb_history_original_text(text, identifier=None):
        original = bb_original_text(text, identifier)

        if identifier or text is None or original != text:
            return original

        bb_build_history_dialogue_maps()
        return bb_substitute(bb_translated_to_original.get(text, text))

    def bb_history_translated_text(text, identifier=None):
        translated = bb_translated_text(text, identifier)

        if identifier or text is None or translated != text:
            return translated

        bb_build_history_dialogue_maps()
        return bb_substitute(bb_original_to_translated.get(text, text))

    def bb_original_text(text, identifier=None):
        if identifier is None:
            identifier = bb_current_identifier()

        original = bb_node_text_for_identifier(identifier, None)
        if original is not None:
            return bb_substitute(original)

        if text is None:
            return None

        bb_build_string_maps()
        return bb_substitute(bb_translated_to_original.get(text, text))

    def bb_translated_text(text, identifier=None):
        if identifier is None:
            identifier = bb_current_identifier()

        translated = bb_node_text_for_identifier(identifier, BB_TRANSLATED_LANGUAGE)
        if translated is not None:
            return bb_substitute(translated)

        if text is None:
            return None

        bb_build_string_maps()
        return bb_substitute(bb_original_to_translated.get(text, text))

    def bb_text_pair(text, identifier=None):
        return bb_pair_from_values(
            bb_translated_text(text, identifier),
            bb_original_text(text, identifier),
        )

    def bb_primary_text(text, identifier=None):
        pair = bb_text_pair(text, identifier)
        if pair:
            return pair[0][1]
        return text

    def bb_statement_is_menu():
        try:
            return renpy.get_statement_name().startswith("menu")
        except Exception:
            return False

    bb_base_say_menu_text_filter = config.say_menu_text_filter

    def bb_say_menu_text_filter(text):
        if bb_base_say_menu_text_filter is not None:
            text = bb_base_say_menu_text_filter(text)

        if not text:
            return text

        if bb_statement_is_menu():
            return bb_join_pair(bb_text_pair(text, ""), with_fonts=True)

        return bb_primary_text(text)

    config.say_menu_text_filter = bb_say_menu_text_filter

    def bb_history_callback(entry):
        identifier = bb_current_identifier()
        if identifier:
            entry.bb_identifier = identifier

        entry.bb_source_what = bb_strip_font_tags(entry.what)

        original = bb_node_text_for_identifier(identifier, None)
        if original is not None:
            entry.bb_original = bb_substitute(original)

        translated = bb_node_text_for_identifier(identifier, BB_TRANSLATED_LANGUAGE)
        if translated is not None:
            entry.bb_translated = bb_substitute(translated)

        if not hasattr(entry, "bb_original") or not hasattr(entry, "bb_translated"):
            translated, original = bb_split_history_pair_text(entry.what)
            if translated is not None and not hasattr(entry, "bb_translated"):
                entry.bb_translated = translated
            if original is not None and not hasattr(entry, "bb_original"):
                entry.bb_original = original

    if bb_history_callback not in config.history_callbacks:
        config.history_callbacks.append(bb_history_callback)

    bb_loader_module = sys.modules.get("renpy.loader", None)
    if bb_loader_module is not None:
        if not hasattr(bb_loader_module, "_bb_base_get_prefixes"):
            bb_loader_module._bb_base_get_prefixes = bb_loader_module.get_prefixes

        bb_base_get_prefixes = bb_loader_module._bb_base_get_prefixes

        def bb_get_prefixes(tl=True, directory=None):
            prefixes = bb_base_get_prefixes(tl=tl, directory=directory)

            if not tl or not bb_is_original_mode():
                return prefixes

            translated_root = renpy.config.tl_directory + "/" + BB_TRANSLATED_LANGUAGE + "/"

            if directory == "images":
                return [i for i in prefixes if not i.startswith(translated_root)]

            translated_images = translated_root + "images/"
            return [i for i in prefixes if not i.startswith(translated_images)]

        bb_loader_module.get_prefixes = bb_get_prefixes

    def bb_textbox_opacity():
        try:
            if renpy.variant("small") and getattr(persistent, "android_textbox_transparency", None) is not None:
                return max(0.0, min(1.0, 1.0 - float(persistent.android_textbox_transparency)))
        except Exception:
            pass

        try:
            if getattr(persistent, "textbox_transparency", None) is not None:
                return max(0.0, min(1.0, 1.0 - float(persistent.textbox_transparency)))
        except Exception:
            pass

        try:
            return max(0.0, min(1.0, float(persistent.textbox_opacity)))
        except Exception:
            return 1.0

    def bb_ruby_style():
        for owner_name in ("say_dialogue", "default"):
            try:
                ruby_style = getattr(getattr(style, owner_name), "ruby_style", None)
                if ruby_style is not None:
                    return ruby_style
            except Exception:
                pass

        for name in ("ruby_style", "ruby_light_style", "ruby_light"):
            try:
                ruby_style = getattr(style, name)
                if ruby_style is not None:
                    return ruby_style
            except Exception:
                pass
        return None

    def bb_outline_name(who):
        try:
            return who in outline_namelist
        except Exception:
            return False

    def bb_dialogue_size(multiplier=1.0):
        size = getattr(persistent, "dialogue_text_size", None) or gui.text_size
        return max(18, int(size * multiplier))

    def bb_bilingual_slot_height():
        quick_guard = max(38, int(gui.quick_button_text_size + 18))
        return max(80, int(gui.textbox_height - gui.dialogue_ypos - quick_guard))

    def bb_bilingual_window_height():
        return int(gui.dialogue_ypos + bb_bilingual_slot_height() * 2 - 24 + max(38, int(gui.quick_button_text_size + 18)))

    def bb_textbox_bottom():
        return int(gui.textbox_yalign * (config.screen_height - gui.textbox_height) + gui.textbox_height)

    bb_dialogue_metrics_cache = {}

    def bb_style_signature(style_object):
        if style_object is None:
            return None

        values = []
        for name in (
            "size",
            "yoffset",
            "outlines",
            "line_spacing",
            "line_leading",
            "ruby_line_leading",
            "font",
            "layout",
            "color",
        ):
            try:
                values.append((name, repr(getattr(style_object, name, None))))
            except Exception:
                pass

        return tuple(values)

    def bb_dialogue_render_props(language=None, outlined=False, text=None):
        font_alias = bb_language_for_text(language, text)
        props = {
            "style": "bb_dialogue",
            "substitute": False,
            "slow": False,
            "size": bb_dialogue_size(),
            "font": font_alias,
        }


        if outlined:
            props["color"] = "#fff"
            props["outlines"] = [(
                renpy.display.core.absolute(1),
                "#242424",
                renpy.display.core.absolute(1),
                renpy.display.core.absolute(1),
            )]

        ruby_style = bb_ruby_style()
        if ruby_style is not None:
            props["ruby_style"] = ruby_style

        return props

    def bb_dialogue_glyph_extents(layout):
        if layout is None:
            return None

        min_y = 0.0
        max_y = 0.0
        saw_glyph = False

        try:
            lines = layout.lines
        except Exception:
            return None

        for line in lines:
            try:
                line_y = float(getattr(line, "y", 0.0) or 0.0)
                line_height = float(getattr(line, "height", 0.0) or 0.0)
                min_y = min(min_y, line_y)
                max_y = max(max_y, line_y + line_height)
            except Exception:
                pass

            try:
                glyphs = line.glyphs
            except Exception:
                glyphs = []

            for glyph in glyphs:
                try:
                    glyph_y = float(getattr(glyph, "y", getattr(line, "baseline", 0.0)) or 0.0)
                    ascent = float(getattr(glyph, "ascent", 0.0) or 0.0)
                    descent = float(getattr(glyph, "descent", 0.0) or 0.0)
                    min_y = min(min_y, glyph_y - ascent)
                    max_y = max(max_y, glyph_y + descent)
                    saw_glyph = True
                except Exception:
                    pass

        if not saw_glyph:
            return None

        try:
            layout_height = float(layout.size[1])
        except Exception:
            layout_height = max_y

        return (
            max(0, int(math.ceil(-min_y))),
            max(0, int(math.ceil(max_y - layout_height))),
        )

    def bb_dialogue_metrics(text, language=None, outlined=False):
        fallback_height = int(bb_dialogue_size() * 1.35)
        if not text:
            return (fallback_height, 0, 0)

        ruby_style = bb_ruby_style()
        font_alias = bb_language_for_text(language, text)
        key = (
            text,
            language,
            bool(outlined),
            int(gui.dialogue_width),
            int(config.screen_height),
            bb_dialogue_size(),
            font_alias,
            bb_style_signature(ruby_style),
        )

        rv = bb_dialogue_metrics_cache.get(key, None)
        if rv is not None:
            return rv

        try:
            probe = renpy.text.text.Text(text, **bb_dialogue_render_props(language, outlined, text))
            rendered = renpy.display.render.render(probe, gui.dialogue_width, config.screen_height, 0, 0)
            height = max(1, int(math.ceil(rendered.get_size()[1])))

            top = 0
            bottom = 0

            layout = probe.get_layout()
            if layout is not None:
                glyph_extents = bb_dialogue_glyph_extents(layout)
                if glyph_extents is not None:
                    top, bottom = glyph_extents
                else:
                    top = max(0, int(math.ceil(getattr(layout, "add_top", 0) or 0)))
                    bottom = max(0, int(math.ceil(getattr(layout, "add_bottom", 0) or 0)))

            rv = (height, top, bottom)
        except Exception as e:
            rv = (fallback_height, 0, 0)

        if len(bb_dialogue_metrics_cache) > 512:
            bb_dialogue_metrics_cache.clear()

        bb_dialogue_metrics_cache[key] = rv

        return rv

    def bb_text_for_slow_count(text_widget):
        try:
            text = text_widget.text[0]
        except Exception:
            return ""

        start = getattr(text_widget, "start", None)
        end = getattr(text_widget, "end", None)

        if start is not None:
            if end is None:
                text = text[start:]
            else:
                text = text[start:end]

        try:
            text = renpy.text.extras.filter_text_tags(text, allow=set())
        except Exception:
            pass

        return text

    def bb_slow_count(text_widget):
        return max(1, len(bb_text_for_slow_count(text_widget)))

    def bb_effective_cps(text_widget):
        try:
            cps = text_widget.style.slow_cps
        except Exception:
            cps = None

        if cps is None or cps is True:
            cps = renpy.game.preferences.text_cps

        try:
            multiplier = text_widget.style.slow_cps_multiplier
        except Exception:
            multiplier = 1.0

        try:
            return float(cps) * float(multiplier)
        except Exception:
            return 0.0

    def bb_set_text_cps(text_widget, cps):
        try:
            text_widget.style.slow_cps = cps
            text_widget.style.slow_cps_multiplier = 1.0
        except Exception:
            try:
                text_widget.style = renpy.style.Style(
                    text_widget.style,
                    {
                        "slow_cps": cps,
                        "slow_cps_multiplier": 1.0,
                    },
                )
            except Exception:
                pass

    def bb_finish_slow_text(text_widget):
        try:
            text_widget.slow = False
            text_widget.slow_done = None
            text_widget.slow_done_time = None
            text_widget.update()
            renpy.display.render.redraw(text_widget, 0)
        except Exception:
            pass

    def bb_sync_second_slow(event, **kwargs):
        if event != "show_done" or not bb_is_bilingual_mode():
            return

        try:
            first = renpy.display.screen.get_widget("say", "what", renpy.config.say_layer)
            second = renpy.display.screen.get_widget("say", "bb_second_what", renpy.config.say_layer)
        except Exception:
            return

        if first is None or second is None:
            return

        if not getattr(first, "slow", False):
            bb_finish_slow_text(second)
            return

        first_cps = bb_effective_cps(first)
        if first_cps <= 0:
            bb_finish_slow_text(second)
            return

        target_time = float(bb_slow_count(first)) / first_cps
        if target_time <= 0:
            bb_finish_slow_text(second)
            return

        second_cps = max(0.01, float(bb_slow_count(second)) / target_time)
        bb_set_text_cps(second, second_cps)

        try:
            second.start = None
            second.end = None
            second.slow = True
            second.slow_done = None
            second.slow_done_time = None
            second.update()
            renpy.display.render.redraw(second, 0)
        except Exception:
            pass

    if bb_sync_second_slow not in config.all_character_callbacks:
        config.all_character_callbacks.append(bb_sync_second_slow)

    def bb_prepare_history_entry(entry):
        if not hasattr(entry, "bb_source_what"):
            try:
                entry.bb_source_what = bb_strip_font_tags(entry.what)
            except Exception:
                pass

        identifier = getattr(entry, "bb_identifier", None)
        if identifier:
            original = bb_node_text_for_identifier(identifier, None)
            if original is not None:
                entry.bb_original = bb_substitute(original)

            translated = bb_node_text_for_identifier(identifier, BB_TRANSLATED_LANGUAGE)
            if translated is not None:
                entry.bb_translated = bb_substitute(translated)

        if not hasattr(entry, "bb_original") or not hasattr(entry, "bb_translated"):
            translated, original = bb_split_history_pair_text(getattr(entry, "what", None))
            if translated is not None and not hasattr(entry, "bb_translated"):
                entry.bb_translated = translated
            if original is not None and not hasattr(entry, "bb_original"):
                entry.bb_original = original

        source = getattr(entry, "bb_source_what", getattr(entry, "what", None))
        current_original = getattr(entry, "bb_original", None)
        current_translated = getattr(entry, "bb_translated", None)

        original = bb_history_original_text(source, identifier or "")
        if original is not None:
            if (
                current_original is None
                or current_original == source
                or current_original == current_translated
            ) and original != source:
                entry.bb_original = original
                current_original = original

        translated = bb_history_translated_text(source, identifier or "")
        if translated is not None:
            if (
                current_translated is None
                or current_translated == source
                or current_translated == current_original
            ) and translated != current_original:
                entry.bb_translated = translated

    def bb_history_pair(entry):
        bb_prepare_history_entry(entry)

        identifier = getattr(entry, "bb_identifier", None)
        original = getattr(entry, "bb_original", None)
        translated = getattr(entry, "bb_translated", None)
        source = getattr(entry, "bb_source_what", entry.what)

        if original is None:
            original = bb_history_original_text(source, identifier or "")

        if translated is None:
            translated = bb_history_translated_text(source, identifier or "")

        return bb_pair_from_values(translated, original)

    def bb_history_display_text(entry):
        return bb_join_pair(bb_history_pair(entry), with_fonts=True)

    def bb_refresh_history_entries():
        try:
            history = list(_history_list)
        except Exception:
            return

        for entry in history:
            try:
                bb_prepare_history_entry(entry)
            except Exception:
                pass

    def bb_history_allow_tags():
        try:
            allow = set(gui.history_allow_tags)
        except Exception:
            allow = set()

        allow.update(["font", "/font", "rb", "/rb", "rt", "/rt"])
        return allow

    def bb_language_text(language):
        if language is None:
            return "English"
        if language == BB_TRANSLATED_LANGUAGE:
            return "Chinese_E"
        return language

    class BBMode(Action, DictEquality):
        def __init__(self, mode):
            self.mode = bb_normalize_mode(mode)

        def __call__(self):
            bb_set_mode(self.mode)

        def get_selected(self):
            return bb_current_mode() == self.mode

    class BBToggle(Action, DictEquality):
        def __call__(self):
            mode = bb_current_mode()
            if mode == BB_MODE_TRANSLATED:
                bb_set_mode(BB_MODE_ORIGINAL)
            elif mode == BB_MODE_ORIGINAL:
                bb_set_mode(BB_MODE_TRANSLATED_FIRST)
            elif mode == BB_MODE_TRANSLATED_FIRST:
                bb_set_mode(BB_MODE_ORIGINAL_FIRST)
            else:
                bb_set_mode(BB_MODE_TRANSLATED)

    class Language(Action, DictEquality):
        alt = _("Language [text]")

        def __init__(self, language):
            self.language = language

        def __call__(self):
            if self.language is None:
                bb_set_mode(BB_MODE_ORIGINAL)
            elif self.language == BB_TRANSLATED_LANGUAGE:
                bb_set_mode(BB_MODE_TRANSLATED)
            else:
                renpy.change_language(self.language)

        def get_selected(self):
            if self.language is None:
                return bb_current_mode() in (BB_MODE_ORIGINAL, BB_MODE_ORIGINAL_FIRST)
            if self.language == BB_TRANSLATED_LANGUAGE:
                return bb_current_mode() in (BB_MODE_TRANSLATED, BB_MODE_TRANSLATED_FIRST)
            return _preferences.language == self.language

        def get_sensitive(self):
            if self.language is None:
                return True
            return self.language in renpy.known_languages()

    bb_save_slot_restore_cache = {}

    def bb_user_slots_by_mtime(regexp=BB_SAVE_SLOT_REGEXP):
        try:
            slots = renpy.list_slots(regexp)
        except Exception:
            slots = []

        rv = []
        for slot in slots:
            try:
                mtime = renpy.slot_mtime(slot)
            except Exception:
                mtime = None

            if mtime is not None:
                rv.append((mtime, slot))

        rv.sort(reverse=True)
        return [slot for _mtime, slot in rv]

    def bb_save_slot_restore_target(slot):
        try:
            mtime = renpy.slot_mtime(slot)
        except Exception:
            mtime = None

        cache_key = (slot, mtime)
        if cache_key in bb_save_slot_restore_cache:
            return bb_save_slot_restore_cache[cache_key]

        target = None

        try:
            log_data, signature = renpy.loadsave.location.load(slot)
            if not renpy.savetoken.check_load(log_data, signature):
                bb_save_slot_restore_cache[cache_key] = None
                return None

            _roots, log = renpy.loadsave.loads(log_data)

            for rb in reversed(list(getattr(log, "log", []))):
                ctx = getattr(rb, "context", None)
                current = getattr(ctx, "current", None)
                if current and renpy.game.script.has_label(current):
                    target = current
                    break
        except Exception:
            target = None

        bb_save_slot_restore_cache[cache_key] = target
        return target

    def bb_newest_user_slot(regexp=BB_SAVE_SLOT_REGEXP, require_restore=False):
        for slot in bb_user_slots_by_mtime(regexp):
            if require_restore and bb_save_slot_restore_target(slot) is None:
                continue
            return slot
        return None

    class Continue(Action, DictEquality):
        def __init__(self, regexp=BB_SAVE_SLOT_REGEXP, confirm=False):
            self.regexp = regexp
            self.confirm = confirm

        def __call__(self):
            if self.confirm and not main_menu:
                layout.yesno_screen(layout.CONTINUE, Continue(self.regexp, False))
                return

            newest = bb_newest_user_slot(self.regexp, require_restore=True)
            if newest:
                renpy.load(newest)

        def get_sensitive(self):
            if _in_replay:
                return False

            newest = bb_newest_user_slot(self.regexp, require_restore=True)
            if not newest:
                return False

            try:
                return renpy.can_load(newest)
            except Exception:
                return False

        def get_newest_slot(self):
            newest = bb_newest_user_slot(self.regexp, require_restore=True)
            if not newest:
                return None, None

            page, _sep, name = newest.partition("-")
            return page, name

    def bb_refresh_current_say():
        try:
            screen = renpy.display.screen.get_screen("say", renpy.config.say_layer)
            if screen is not None and screen.scope.get("what", None):
                screen.scope["what"] = bb_primary_text(screen.scope["what"])
        except Exception:
            pass

    def bb_clear_current_say_ranges():
        try:
            for widget_id in ("what", "bb_second_what"):
                text_widget = renpy.display.screen.get_widget(
                    "say",
                    widget_id,
                    renpy.config.say_layer,
                )

                if text_widget is None:
                    continue

                text_widget.start = None
                text_widget.end = None
                text_widget.update()
                renpy.display.render.redraw(text_widget, 0)
        except Exception:
            pass

    def bb_clear_say_ranges_interact():
        global bb_clear_say_ranges_next_interact

        if not bb_clear_say_ranges_next_interact:
            return

        bb_clear_say_ranges_next_interact = False
        bb_clear_current_say_ranges()

    def bb_empty_window(*args, **kwargs):
        if not bb_is_bilingual_mode():
            if bb_base_empty_window is not None:
                return bb_base_empty_window(*args, **kwargs)
            return None

        try:
            multiple = kwargs.get("multiple", None)
            if multiple is None and args:
                multiple = args[0]
        except Exception:
            multiple = None

        if multiple:
            for _i in range(multiple):
                renpy.display.screen.show_screen(
                    "say",
                    _transient=True,
                    who=None,
                    what="",
                    bb_force_bilingual_window=True,
                )
                renpy.exports.shown_window()
        else:
            renpy.display.screen.show_screen(
                "say",
                _transient=True,
                who=None,
                what="",
                bb_force_bilingual_window=True,
            )
            renpy.exports.shown_window()

    def bb_refresh_scene_images():
        try:
            sls = renpy.game.context().scene_lists
            for _layer, _tag, d in sls.get_all_layer_tag_displayable():
                bb_refresh_displayable(d)
        except Exception as e:
            bb_log("could not refresh scene images: %r" % e)

    def bb_refresh_displayable(d, seen=None):
        if d is None:
            return

        if seen is None:
            seen = set()

        did = id(d)
        if did in seen:
            return
        seen.add(did)

        if isinstance(d, renpy.display.image.ImageReference):
            d.target = None
            d.old_transform = None
            try:
                renpy.display.render.redraw(d, 0)
            except Exception:
                pass
        elif isinstance(d, renpy.display.image.DynamicImage):
            d.target = None
            d.raw_target = None
            try:
                renpy.display.render.redraw(d, 0)
            except Exception:
                pass

        try:
            children = d.visit()
        except Exception:
            children = []

        for child in children:
            bb_refresh_displayable(child, seen)

    def bb_set_mode(mode):
        global bb_clear_say_ranges_next_interact

        mode = bb_normalize_mode(mode)

        if bb_current_mode() == mode:
            bb_sync_engine_language()
            bb_capture_current_fonts()
            bb_patch_progress_event_names()
            return

        persistent.bb_mode = mode
        persistent.ll_better_bilingual_mode = mode
        persistent.ll_fast_original_mode = mode in (BB_MODE_ORIGINAL, BB_MODE_ORIGINAL_FIRST)

        bb_sync_engine_language()
        bb_capture_current_fonts()
        bb_patch_progress_event_names()

        try:
            renpy.loader.loadable_cache.clear()
            renpy.loader.hash_cache.clear()
        except Exception:
            pass

        bb_clear_current_say_ranges()
        bb_clear_say_ranges_next_interact = True
        bb_refresh_current_say()
        bb_refresh_history_entries()
        bb_refresh_scene_images()
        renpy.restart_interaction()

    def bb_start_callback():
        bb_init_persistent()
        bb_sync_engine_language()
        bb_reset_progress_event_title_cache()
        bb_capture_current_fonts()
        bb_patch_progress_event_names()

    def bb_after_load_callback():
        global bb_clear_say_ranges_next_interact

        bb_clear_say_ranges_next_interact = False
        bb_init_persistent()
        bb_sync_engine_language()
        if bb_reapply_current_language_styles():
            bb_reset_translated_font()
        else:
            bb_log("kept translated font cache after failed language style reapply")
        bb_reset_text_maps()
        bb_capture_current_fonts()
        bb_patch_progress_event_names()

    def bb_reapply_current_language_styles():
        try:
            renpy.translation.change_language(BB_TRANSLATED_LANGUAGE, force=True, rebuild=True)
            return True
        except TypeError as e:
            try:
                renpy.translation.change_language(BB_TRANSLATED_LANGUAGE, force=True)
                return True
            except Exception as fallback_e:
                bb_log("could not reapply language styles after load: %r; fallback failed: %r" % (e, fallback_e))
        except Exception as e:
            bb_log("could not reapply language styles after load: %r" % e)
        return False

    bb_init_persistent()
    bb_capture_original_font()
    bb_sync_engine_language()
    bb_capture_current_fonts()
    bb_patch_progress_event_names()

    bb_say._bb_base_say = bb_base_say
    renpy.exports.say = bb_say
    renpy.say = bb_say
    if bb_sayexports_module is not None:
        bb_sayexports_module.say = bb_say

    if bb_base_empty_window is not None:
        bb_empty_window._bb_base_empty_window = bb_base_empty_window
        config.empty_window = bb_empty_window

    if bb_start_callback not in config.start_callbacks:
        config.start_callbacks.append(bb_start_callback)

    if bb_after_load_callback not in config.after_load_callbacks:
        config.after_load_callbacks.append(bb_after_load_callback)

    if bb_clear_say_ranges_interact not in config.interact_callbacks:
        config.interact_callbacks.append(bb_clear_say_ranges_interact)

init 25 python:
    config.keymap["bb_toggle_language"] = [ "K_F2" ]
    config.underlay.append(renpy.Keymap(bb_toggle_language=BBToggle()))

screen bb_say(who, what, bb_force_bilingual_window=False):
    style_prefix "say"

    $ bb_has_text = what is not None and what != ""
    $ bb_pair = bb_text_pair(what) if bb_has_text else [(BB_MODE_TRANSLATED, what)]
    $ bb_current_language = bb_pair[0][0] if bb_pair else BB_MODE_TRANSLATED
    $ bb_current_what = bb_pair[0][1] if bb_pair else what
    $ bb_second_what = bb_pair[1][1] if len(bb_pair) > 1 and bb_pair[1][1] != bb_current_what else None
    $ bb_second_language = bb_pair[1][0] if len(bb_pair) > 1 else None
    $ bb_bilingual = bb_has_text and bb_is_bilingual_mode()
    $ bb_tall_window = bb_bilingual or bb_force_bilingual_window
    $ bb_opacity = bb_textbox_opacity()
    $ bb_window_height = bb_bilingual_window_height() if bb_tall_window else gui.textbox_height
    $ bb_window_bottom = bb_textbox_bottom() + (28 if bb_tall_window else 0)

    window:
        id "window"
        ysize bb_window_height
        ypos bb_window_bottom
        yanchor 1.0
        background Transform(
            Image("gui/textbox.png", xalign=0.5, yalign=1.0),
            alpha=bb_opacity,
            xysize=(config.screen_width, bb_window_height)
        )

        if who is not None:
            window:
                id "namebox"
                style "namebox"
                if bb_opacity <= 0.5 and bb_outline_name(who):
                    text who id "who" outlines [(absolute(2), "#ffffff", absolute(0), absolute(0))]
                else:
                    text who id "who"

        if bb_bilingual:
            $ bb_slot_height = bb_bilingual_slot_height()
            $ bb_first_height, bb_first_top, bb_first_bottom = bb_dialogue_metrics(bb_current_what, bb_current_language, bb_opacity <= 0.5)
            $ bb_second_height, bb_second_top, bb_second_bottom = bb_dialogue_metrics(bb_second_what, bb_second_language, bb_opacity <= 0.5) if bb_second_what else (bb_slot_height, 0, 0)
            $ bb_top_pad = max(bb_first_top, bb_second_top)
            $ bb_bottom_pad = max(bb_first_bottom, bb_second_bottom)
            $ bb_second_ypos = min(bb_slot_height - 24, bb_first_height + bb_first_bottom + bb_second_top)

            fixed:
                xpos gui.dialogue_xpos
                ypos (gui.dialogue_ypos - bb_top_pad)
                xsize gui.dialogue_width
                ysize (bb_slot_height * 2 - 24 + bb_top_pad + bb_bottom_pad)

                fixed:
                    xsize gui.dialogue_width
                    ysize (bb_slot_height + bb_top_pad + bb_bottom_pad)

                    text bb_current_what id "what":
                        prefer_screen_to_id True
                        style "bb_dialogue"
                        substitute False
                        ypos bb_top_pad
                        font bb_language_for_text(bb_current_language, bb_current_what)
                        ruby_style bb_ruby_style()
                        size bb_dialogue_size()
                        if bb_opacity <= 0.5:
                            color "#fff"
                            outlines [(absolute(1), "#242424", absolute(1), absolute(1))]

                fixed:
                    xsize gui.dialogue_width
                    ysize (bb_slot_height + bb_top_pad + bb_bottom_pad)
                    ypos bb_second_ypos

                    if bb_second_what:
                        text bb_second_what id "bb_second_what":
                            style "bb_dialogue"
                            substitute False
                            slow True
                            ypos bb_top_pad
                            font bb_language_for_text(bb_second_language, bb_second_what)
                            ruby_style bb_ruby_style()
                            size bb_dialogue_size()
                            if bb_opacity <= 0.5:
                                color "#e6e6e6"
                                outlines [(absolute(1), "#242424", absolute(1), absolute(1))]
                            else:
                                color "#626262"
                    else:
                        null height bb_slot_height

        else:
            if bb_opacity <= 0.5:
                text bb_current_what id "what" substitute False font bb_language_for_text(bb_current_language, bb_current_what) color "#fff" outlines [(absolute(1), "#242424", absolute(1), absolute(1))] ruby_style bb_ruby_style() size persistent.dialogue_text_size
            else:
                text bb_current_what id "what" substitute False font bb_language_for_text(bb_current_language, bb_current_what) size persistent.dialogue_text_size

    if not renpy.variant("small"):
        add SideImage() xalign 0.0 yalign 1.0

screen bb_quick_menu_language_fragment():

    if getattr(persistent, "show_toggle_language", True):
        textbutton bb_mode_name() action BBToggle() alternate Show("bb_language_picker")


screen bb_preferences_language_fragment():

    vbox:
        style_prefix "radio"
        label ("Language")
        textbutton "中文" action BBMode(BB_MODE_TRANSLATED)
        textbutton "English" action BBMode(BB_MODE_ORIGINAL)
        textbutton "中/EN" action BBMode(BB_MODE_TRANSLATED_FIRST)
        textbutton "EN/中" action BBMode(BB_MODE_ORIGINAL_FIRST)

screen bb_language_picker():

    modal True
    zorder 250

    frame:
        style_prefix "confirm"
        xalign 0.5
        yalign 0.5
        xpadding 40
        ypadding 30

        vbox:
            spacing 12
            label _("Language")
            textbutton "中文" action [BBMode(BB_MODE_TRANSLATED), Hide("bb_language_picker")]
            textbutton "English" action [BBMode(BB_MODE_ORIGINAL), Hide("bb_language_picker")]
            textbutton "中/EN" action [BBMode(BB_MODE_TRANSLATED_FIRST), Hide("bb_language_picker")]
            textbutton "EN/中" action [BBMode(BB_MODE_ORIGINAL_FIRST), Hide("bb_language_picker")]
            textbutton _("Return") action Hide("bb_language_picker")

    key "game_menu" action Hide("bb_language_picker")

screen bb_history():

    tag menu
    predict False

    use game_menu(_("History"), scroll=("vpgrid" if gui.history_height else "viewport"), yinitial=1.0):

        style_prefix "history"

        for h in _history_list:

            window:

                has fixed:
                    yfit True

                if h.who:

                    label h.who:
                        style "history_name"
                        substitute False

                        if "color" in h.who_args:
                            text_color h.who_args["color"]
                        if "outlines" in h.who_args:
                            text_outlines [(absolute(1), "#000", absolute(0), absolute(0))]

                $ what = renpy.filter_text_tags(bb_history_display_text(h), allow=bb_history_allow_tags())
                text what:
                    substitute False
                    style "bb_history_text"
                    ruby_style bb_ruby_style()
                    if "color" in h.what_args:
                        color h.what_args["color"]

        if not _history_list:
            label _("The dialogue history is empty.")

screen bb_hinttracker():

    tag menu

    key "n" action Return()

    $ activate_girls()
    $ ProgressMod.update_all()
    $ bb_rows = bb_progress_hint_rows()

    use game_menu(_("Hints"), scroll="viewport"):

        null

    $ renpy.show_screen("overlay_scr", transient=False, zorder=100)

    viewport:
        xpos .25
        ypos .14
        xsize 1450
        ysize 780
        scrollbars None
        mousewheel True
        draggable True
        pagekeys True

        vbox:
            spacing 0

            for bb_row in bb_rows:
                hbox:
                    spacing 28

                    fixed:
                        xsize 170
                        yfit True

                        if bb_row["girl_screen"] == "amitrackerm2":
                            textbutton _(bb_row["girl_label"]) action [ShowMenu("amitrackerm2"), SetVariable("showgirl", bb_row["showgirl_name"])] style "event_button" text_style bb_row["girl_text_style"]
                        else:
                            textbutton _(bb_row["girl_label"]) action ShowMenu(bb_row["girl_screen"]) style "event_button" text_style bb_row["girl_text_style"]

                    fixed:
                        xsize 580
                        yfit True

                        text (bb_row["event_title"]) style "hint_text" substitute False

                    fixed:
                        xsize 630
                        yfit True

                        if show_hints == True:
                            if bb_row["hint_action"]:
                                textbutton (bb_row["hint"]) action [ShowMenu("explanations"), SetVariable("explain_event", bb_row["event"]), SetVariable("previous_screen", "hints")] style "event_button" text_style "hint_text"
                            else:
                                text (bb_row["hint"]) style "hint_text"
                        else:
                            null

    vbox:
        xpos .25
        ypos .916

        hbox:
            if dark_mode:
                textbutton _("Back") action ShowMenu("progressmod_dark")
            else:
                textbutton _("Back") action ShowMenu("progressmod")

screen bb_progress_tracker_rows(bb_rows, bb_ypos=.14, bb_ysize=780):

    viewport:
        xpos .25
        ypos bb_ypos
        xsize 1450
        ysize bb_ysize
        scrollbars None
        mousewheel True
        draggable True
        pagekeys True

        vbox:
            spacing 0

            for bb_row in bb_rows:
                hbox:
                    spacing 28

                    fixed:
                        xsize 650
                        yfit True

                        if bb_row["completed"]:
                            textbutton (bb_row["title"]) action Replay(bb_row["event"].var_name, locked=False) style "event_button" text_style "modmybutton"
                        else:
                            text (bb_row["title"]) style "tracker_text" substitute False

                    fixed:
                        xsize 670
                        yfit True

                        if bb_row["hint"]:
                            if bb_row["hint_action"]:
                                textbutton (bb_row["hint"]) action [ShowMenu("explanations"), SetVariable("explain_event", bb_row["event"]), SetVariable("previous_screen", bb_row["previous_screen"])] style "event_button" text_style "mod"
                            else:
                                text (bb_row["hint"]) style "tracker_text"
                        else:
                            null

screen bb_maintrackerch1m():
    tag menu
    key "m" action Return()
    $ renpy.show_screen("overlay_scr", transient=False, zorder=100)
    $ ProgressMod.update_all()
    $ bb_rows = bb_progress_main_rows(1)

    use game_menu(_("Chapter 1"), scroll="viewport"):
        null

    vbox:
        xpos .25
        ypos 75
        hbox:
            textbutton _("<") action ShowMenu(bb_progress_main_prev_screen(1))
            textbutton _(">") action ShowMenu(bb_progress_main_next_screen(1))

    use bb_progress_tracker_rows(bb_rows)

    vbox:
        xpos .25
        ypos .916
        hbox:
            if dark_mode:
                textbutton _("Back") action ShowMenu("progressmod_dark")
            else:
                textbutton _("Back") action ShowMenu("progressmod")
            if show_hints:
                textbutton _("       Hints") action ShowMenu("hinttracker")

screen bb_maintrackerch2m():
    tag menu
    key "m" action Return()
    $ renpy.show_screen("overlay_scr", transient=False, zorder=100)
    $ ProgressMod.update_all()
    $ bb_rows = bb_progress_main_rows(2)

    use game_menu(_("Chapter 2"), scroll="viewport"):
        null

    vbox:
        xpos .25
        ypos 75
        hbox:
            textbutton _("<") action ShowMenu(bb_progress_main_prev_screen(2))
            textbutton _(">") action ShowMenu(bb_progress_main_next_screen(2))

    use bb_progress_tracker_rows(bb_rows)

    vbox:
        xpos .25
        ypos .916
        hbox:
            if dark_mode:
                textbutton _("Back") action ShowMenu("progressmod_dark")
            else:
                textbutton _("Back") action ShowMenu("progressmod")
            if show_hints:
                textbutton _("       Hints") action ShowMenu("hinttracker")

screen bb_maintrackerch3m():
    tag menu
    key "m" action Return()
    $ renpy.show_screen("overlay_scr", transient=False, zorder=100)
    $ ProgressMod.update_all()
    $ bb_rows = bb_progress_main_rows(3)

    use game_menu(_("Chapter 3"), scroll="viewport"):
        null

    vbox:
        xpos .25
        ypos 75
        hbox:
            textbutton _("<") action ShowMenu(bb_progress_main_prev_screen(3))
            textbutton _(">") action ShowMenu(bb_progress_main_next_screen(3))

    use bb_progress_tracker_rows(bb_rows)

    vbox:
        xpos .25
        ypos .916
        hbox:
            if dark_mode:
                textbutton _("Back") action ShowMenu("progressmod_dark")
            else:
                textbutton _("Back") action ShowMenu("progressmod")
            if show_hints:
                textbutton _("       Hints") action ShowMenu("hinttracker")

screen bb_maintrackerch4m():
    tag menu
    key "m" action Return()
    $ renpy.show_screen("overlay_scr", transient=False, zorder=100)
    $ ProgressMod.update_all()
    $ bb_rows = bb_progress_main_rows(4)

    use game_menu(_("Chapter 4"), scroll="viewport"):
        null

    vbox:
        xpos .25
        ypos 75
        hbox:
            textbutton _("<") action ShowMenu(bb_progress_main_prev_screen(4))
            textbutton _(">") action ShowMenu(bb_progress_main_next_screen(4))

    use bb_progress_tracker_rows(bb_rows)

    vbox:
        xpos .25
        ypos .916
        hbox:
            if dark_mode:
                textbutton _("Back") action ShowMenu("progressmod_dark")
            else:
                textbutton _("Back") action ShowMenu("progressmod")
            if show_hints:
                textbutton _("       Hints") action ShowMenu("hinttracker")

screen bb_amitrackerm2():
    tag menu
    key "g" action Return()
    $ renpy.show_screen("overlay_scr", transient=False, zorder=100)
    $ activate_girls()
    $ ProgressMod.update_all()
    $ bb_rows = bb_progress_girl_rows()
    $ bb_girl_rows = bb_progress_visible_girl_rows()

    use game_menu(_("Girls"), scroll="viewport"):
        null

    vbox:
        xpos .25
        ypos 40
        spacing 8

        for bb_girl_row in bb_girl_rows:
            hbox:
                spacing 0

                for bb_girl in bb_girl_row:
                    $ bb_thumb = bb_progress_girl_thumbnail(bb_girl)
                    $ bb_idle_thumb = bb_progress_girl_thumbnail_idle(bb_girl)

                    if bb_thumb:
                        imagebutton:
                            idle bb_idle_thumb
                            hover bb_thumb
                            focus_mask True
                            action [ShowMenu("amitrackerm2"), SetVariable("showgirl", bb_girl.name)]
                            at customzoom
                        text (" ")

    vbox:
        xpos .25
        ypos 195
        text (bb_progress_girl_header()) style "aff" substitute False

    use bb_progress_tracker_rows(bb_rows, 245, 720)

    vbox:
        xpos .25
        ypos .916
        hbox:
            if dark_mode:
                textbutton _("Back") action ShowMenu("progressmod_dark")
            else:
                textbutton _("Back") action ShowMenu("progressmod")
            if show_hints:
                textbutton _("       Hints") action ShowMenu("hinttracker")

screen bb_explanations():

    tag menu

    key "n" action Return()

    $ explain_text = ""

    use game_menu(_("Hints"), scroll="viewport"):

        null

    $ renpy.show_screen("overlay_scr", transient=False, zorder=100)

    vbox:
        xpos .25
        ypos .14

        text (explain_event.girl.colored_name + '      ' + explain_event.name) style "tracker_text"

    vbox:
        xpos .25
        ypos .17
        style_prefix "hint"

        python:
            import string

            second_explain_text = ""
            if explain_event.attention_type == 1:
                explain_text = "Rejecting her will lead to missing events."
            elif explain_event.attention_type == 2:
                previous_event = eval("ev_" + explain_event.previous_event)
                if previous_event.girl == MainEvent:
                    previous_event = previous_event.var_name.rstrip(string.digits) + "1"
                    previous_event = eval("ev_" + previous_event)
                    explain_text = "You have until the " + previous_event.girl.colored_name + " " + previous_event.name + " to complete the lust requirement."
                else:
                    explain_text = "You have until the " + previous_event.girl.colored_name + " event " + previous_event.name + " to complete the lust requirement."
                if explain_event.second_attention == 9:
                    second_explain_text = "Choose " + Miku.colored_name + " as the winner of the costume contest."
                elif explain_event.second_attention == 10:
                    second_explain_text = "You have until the " + MainEvent.colored_name + " There is Nothing to complete the lust requirement."
                elif explain_event.second_attention == 15:
                    second_explain_text = "You will not be able to increase " + Makoto.colored_name + "'s lust after " + Nodoka.colored_name + "'s event Beyond the Reach of God."
            elif explain_event.attention_type == 3:
                explain_text = "Telling her the truth will cause you to miss a " + Karin.colored_name + " event."
            elif explain_event.attention_type == 4:
                explain_text = "Starting this event before you have completed the beach vacation will impact " + Rin.colored_name + "'s events."
            elif explain_event.attention_type == 5:
                explain_text = "Starting this event before you have completed the " + Yumi.colored_name + " event Abyss will impact " + Yumi.colored_name + "'s events."
            elif explain_event.attention_type == 6:
                explain_text = "Not asking for a blowjob will cause you to miss a later " + Maki.colored_name + " event."
            elif explain_event.attention_type == 7:
                explain_text = "Leaving " + Sana.colored_name + " will cause you to miss an event."
            elif explain_event.attention_type == 8:
                explain_text = "Choosing " + Ayane.colored_name + " is a requirement for future events."
            elif explain_event.attention_type == 11:
                explain_text = "Choosing " + Tsukasa.colored_name + " is a requirement for future events."
            elif explain_event.attention_type == 12:
                explain_text = "Not sending the photo will lead to missing significant content but full consequences are still unknown."
            elif explain_event.attention_type == 13:
                explain_text = "Choose to go in to avoid missing future " + Tsukasa.colored_name + " events."
            elif explain_event.attention_type == 14:
                explain_text = "Need to view the picture in Sana's profile to get her number."

        if not "correct choices" in explain_event.hint:
            text ('     ' + explain_text)
        if not second_explain_text == "":
            text ('     ' + second_explain_text)

    vbox:
        xpos .25
        ypos .916
        hbox:
            if previous_screen == "hints":
                textbutton _("Back") action ShowMenu("hinttracker")
            elif previous_screen == "girls":
                textbutton _("Back") action ShowMenu("amitrackerm2")
            elif previous_screen in ("maintrackerch1m", "maintrackerch2m", "maintrackerch3m", "maintrackerch4m"):
                textbutton _("Back") action ShowMenu(previous_screen)
            else:
                if dark_mode:
                    textbutton _("Back") action ShowMenu("progressmod_dark")
                else:
                    textbutton _("Back") action ShowMenu("progressmod")

style bb_dialogue is say_dialogue:
    xpos 0
    ypos 0
    xsize gui.dialogue_width
    layout "tex"
    slow_abortable True

style bb_history_text is history_text:
    layout "tex"

init 999 python:
    def bb_sl_expr_text(expr):
        if expr is None:
            return None

        if isinstance(expr, str):
            expr = expr.strip()
            if expr.startswith("_(") and expr.endswith(")"):
                expr = expr[1:].strip()

            while len(expr) >= 2 and expr[0] == "(" and expr[-1] == ")":
                expr = expr[1:-1].strip()

            if len(expr) >= 2 and expr[0] == expr[-1] and expr[0] in ("'", '"'):
                return expr[1:-1]
            return expr

        return None

    def bb_sl_has_language_action(node):
        try:
            keywords = dict(getattr(node, "keyword", []))
        except Exception:
            return False

        action = keywords.get("action", "")
        return isinstance(action, str) and re.search(r"(^|[^A-Za-z0-9_])Language\s*\(", action) is not None

    def bb_sl_is_textbutton(node):
        try:
            return getattr(node, "name", "") == "textbutton"
        except Exception:
            return False

    def bb_sl_tree_has_language_action(node):
        if bb_sl_has_language_action(node):
            return True

        for children in bb_sl_child_lists(node):
            for child in list(children):
                if bb_sl_tree_has_language_action(child):
                    return True

        return False

    def bb_sl_tree_has_textbutton(node):
        if bb_sl_is_textbutton(node):
            return True

        for children in bb_sl_child_lists(node):
            for child in list(children):
                if bb_sl_tree_has_textbutton(child):
                    return True

        return False

    def bb_sl_is_language_label(node):
        try:
            positional = getattr(node, "positional", [])
            name = getattr(node, "name", "")
        except Exception:
            return False

        if name != "label" or not positional:
            return False

        return bb_sl_expr_text(positional[0]) == "Language"

    def bb_sl_is_language_vbox(node):
        try:
            children = list(getattr(node, "children", []))
            name = getattr(node, "name", "")
        except Exception:
            return False

        if name != "vbox":
            return False

        saw_label = False
        saw_language_action = False

        for child in children:
            saw_label = saw_label or bb_sl_is_language_label(child)
            saw_language_action = saw_language_action or bb_sl_has_language_action(child)

        return saw_label and saw_language_action

    def bb_sl_child_lists(node):
        rv = []

        try:
            children = getattr(node, "children", None)
        except Exception:
            children = None

        if children:
            rv.append(children)

        try:
            block = getattr(node, "block", None)
            block_children = getattr(block, "children", None)
        except Exception:
            block_children = None

        if block_children:
            rv.append(block_children)

        try:
            entries = getattr(node, "entries", None)
        except Exception:
            entries = None

        if entries:
            for entry in entries:
                try:
                    entry_block = entry[1]
                    entry_children = getattr(entry_block, "children", None)
                except Exception:
                    entry_children = None

                if entry_children:
                    rv.append(entry_children)

        return rv

    def bb_sl_find_language_vbox_owner(node):
        for children in bb_sl_child_lists(node):
            for index, child in enumerate(list(children)):
                if bb_sl_is_language_vbox(child):
                    return (children, index)

                found = bb_sl_find_language_vbox_owner(child)
                if found is not None:
                    return found

        return None

    def bb_sl_find_quick_menu_hboxes(node):
        rv = []

        for children in bb_sl_child_lists(node):
            for child in list(children):
                try:
                    name = getattr(child, "name", "")
                except Exception:
                    name = ""

                if name == "hbox":
                    child_list = getattr(child, "children", None)
                    if child_list and any(bb_sl_is_textbutton(grandchild) for grandchild in child_list):
                        rv.append(child)

                rv.extend(bb_sl_find_quick_menu_hboxes(child))

        return rv

    def bb_patch_quick_menu_children(children, replacement):
        language_indices = []
        button_indices = []

        for index, child in enumerate(list(children)):
            if bb_sl_tree_has_language_action(child):
                language_indices.append(index)

            if bb_sl_is_textbutton(child) or bb_sl_tree_has_textbutton(child):
                button_indices.append(index)

        if language_indices:
            first = language_indices[0]
            children[first] = replacement.copy(False)
            for index in reversed(language_indices[1:]):
                del children[index]
            return True

        if button_indices:
            children.insert(button_indices[-1], replacement.copy(False))
            return True

        return False

    def bb_clone_screen_child(screen_name):
        try:
            variants = renpy.display.screen.get_all_screen_variants(screen_name)
        except Exception:
            variants = []

        if not variants:
            return None

        for _variant, screen in variants:
            ast = getattr(screen, "ast", None)
            children = getattr(ast, "children", None)
            if children:
                try:
                    return children[0].copy(False)
                except Exception:
                    return None

        return None

    bb_preferences_language_fragment_patched = False
    bb_preferences_language_fragment_warned = False
    bb_quick_menu_language_fragment_patched = False
    bb_quick_menu_language_fragment_warned = False

    def bb_invalidate_screen_analysis(screen):
        ast = getattr(screen, "ast", None)
        if ast is None:
            return

        try:
            ast.unprepare_screen()
        except Exception:
            pass

        for attr in ("const_ast", "not_const_ast", "analysis"):
            try:
                setattr(ast, attr, None)
            except Exception:
                pass

        try:
            key = (ast.name, ast.variant, ast.location)
            renpy.sl2.slast.scache.const_analyzed.pop(key, None)
            renpy.sl2.slast.scache.not_const_analyzed.pop(key, None)
        except Exception:
            pass

    def bb_patch_preferences_language_fragment(log_failure=True):
        global bb_preferences_language_fragment_patched
        global bb_preferences_language_fragment_warned

        if bb_preferences_language_fragment_patched:
            return True

        replacement = bb_clone_screen_child("bb_preferences_language_fragment")
        if replacement is None:
            if log_failure and not bb_preferences_language_fragment_warned:
                bb_log("preferences language patch skipped, no replacement screen")
                bb_preferences_language_fragment_warned = True
            return False

        patched = False

        try:
            variants = renpy.display.screen.get_all_screen_variants("preferences")
        except Exception as e:
            if log_failure and not bb_preferences_language_fragment_warned:
                bb_log("preferences language patch lookup failed: %r" % e)
                bb_preferences_language_fragment_warned = True
            return False

        for _variant, screen in variants:
            ast = getattr(screen, "ast", None)
            found = bb_sl_find_language_vbox_owner(ast)
            if found is None:
                continue

            children, index = found
            children[index] = replacement.copy(False)
            bb_invalidate_screen_analysis(screen)
            patched = True

        if patched:
            bb_preferences_language_fragment_patched = True
            renpy.display.screen.prepared = False
            renpy.display.screen.analyzed = False
            renpy.display.screen.screens_at_sort = {}
            return True
        else:
            if log_failure and not bb_preferences_language_fragment_warned:
                bb_log("preferences language patch skipped, no Language vbox found")
                bb_preferences_language_fragment_warned = True
            return False

    def bb_patch_preferences_language_fragment_interact():
        if bb_patch_preferences_language_fragment():
            try:
                config.start_interact_callbacks.remove(bb_patch_preferences_language_fragment_interact)
            except ValueError:
                pass

    def bb_patch_quick_menu_language_fragment(log_failure=True):
        global bb_quick_menu_language_fragment_patched
        global bb_quick_menu_language_fragment_warned

        if bb_quick_menu_language_fragment_patched:
            return True

        replacement = bb_clone_screen_child("bb_quick_menu_language_fragment")
        if replacement is None:
            if log_failure and not bb_quick_menu_language_fragment_warned:
                bb_log("quick menu language patch skipped, no replacement screen")
                bb_quick_menu_language_fragment_warned = True
            return False

        patched = False

        try:
            variants = renpy.display.screen.get_all_screen_variants("quick_menu")
        except Exception as e:
            if log_failure and not bb_quick_menu_language_fragment_warned:
                bb_log("quick menu language patch lookup failed: %r" % e)
                bb_quick_menu_language_fragment_warned = True
            return False

        for _variant, screen in variants:
            ast = getattr(screen, "ast", None)
            screen_patched = False

            for hbox in bb_sl_find_quick_menu_hboxes(ast):
                children = getattr(hbox, "children", None)
                if children and bb_patch_quick_menu_children(children, replacement):
                    screen_patched = True

            if screen_patched:
                bb_invalidate_screen_analysis(screen)
                patched = True

        if patched:
            bb_quick_menu_language_fragment_patched = True
            renpy.display.screen.prepared = False
            renpy.display.screen.analyzed = False
            renpy.display.screen.screens_at_sort = {}
            return True

        if log_failure and not bb_quick_menu_language_fragment_warned:
            bb_log("quick menu language patch skipped, no button hbox found")
            bb_quick_menu_language_fragment_warned = True
        return False

    def bb_patch_quick_menu_language_fragment_interact():
        if bb_patch_quick_menu_language_fragment():
            try:
                config.start_interact_callbacks.remove(bb_patch_quick_menu_language_fragment_interact)
            except ValueError:
                pass

    def bb_sl_walk_nodes(node):
        if node is None:
            return

        yield node

        for children in bb_sl_child_lists(node):
            for child in list(children):
                for grandchild in bb_sl_walk_nodes(child):
                    yield grandchild

    def bb_install_screen_alias(public_name, private_name, tag=None):
        try:
            variants = renpy.display.screen.get_all_screen_variants(private_name)
        except Exception as e:
            bb_log("screen alias lookup failed for %s: %r" % (private_name, e))
            variants = []

        if not variants:
            bb_log("screen alias skipped, no variants for %s" % private_name)
            return

        try:
            renpy.display.screen.screens_by_name[public_name].clear()

            for key in list(renpy.display.screen.screens.keys()):
                if key[0] == public_name:
                    del renpy.display.screen.screens[key]

            for variant, screen in variants:
                screen.name = (public_name,)
                if tag is not None:
                    screen.tag = tag
                elif screen.tag == private_name:
                    screen.tag = public_name

                renpy.display.screen.screens[public_name, variant] = screen
                renpy.display.screen.screens_by_name[public_name][variant] = screen

            for key in list(renpy.display.screen.screens.keys()):
                if key[0] == private_name:
                    del renpy.display.screen.screens[key]

            if private_name in renpy.display.screen.screens_by_name:
                del renpy.display.screen.screens_by_name[private_name]

            renpy.display.screen.prepared = False
            renpy.display.screen.analyzed = False
            renpy.display.screen.screens_at_sort = {}
        except Exception as e:
            bb_log("screen alias install failed for %s -> %s: %r" % (private_name, public_name, e))

    bb_install_screen_alias("say", "bb_say")
    bb_install_screen_alias("history", "bb_history", "menu")
    bb_install_screen_alias("hinttracker", "bb_hinttracker", "menu")
    bb_install_screen_alias("explanations", "bb_explanations", "menu")
    bb_install_screen_alias("maintrackerch1m", "bb_maintrackerch1m", "menu")
    bb_install_screen_alias("maintrackerch2m", "bb_maintrackerch2m", "menu")
    bb_install_screen_alias("maintrackerch3m", "bb_maintrackerch3m", "menu")
    bb_install_screen_alias("maintrackerch4m", "bb_maintrackerch4m", "menu")
    bb_install_screen_alias("amitrackerm2", "bb_amitrackerm2", "menu")
    bb_patch_quick_menu_language_fragment(log_failure=False)
    bb_patch_preferences_language_fragment(log_failure=False)
    if bb_patch_quick_menu_language_fragment_interact not in config.start_interact_callbacks:
        config.start_interact_callbacks.append(bb_patch_quick_menu_language_fragment_interact)
    if bb_patch_preferences_language_fragment_interact not in config.start_interact_callbacks:
        config.start_interact_callbacks.append(bb_patch_preferences_language_fragment_interact)
