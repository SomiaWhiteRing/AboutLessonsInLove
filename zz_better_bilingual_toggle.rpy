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

    BB_ORIGINAL_FONT = "YuGothM.ttc"
    BB_TRANSLATED_FONT_CANDIDATES = (
        "tl/Chinese_E/customfonts/NotoSansSC-VF.woff2",
        "tl/chinese/customfonts/NotoSansSC-VF.woff2",
        "MiSans-Regular.ttf",
        "NotoSansCJKsc-Regular.otf",
        "NotoSans-Regular.ttf",
    )

    BB_SAVE_SLOT_REGEXP = r"^(?:auto|quick|\d+)-\d+$"
    BB_OLD_SUBSTITUTION_SAFE_PERCENT_RE = re.compile(
        r"%%|%\([^)]+\)[#0 +\-]*(?:\*|\d+)?(?:\.(?:\*|\d+))?[hlL]?[diouxXeEfFgGcrs]"
    )

    def bb_log(message):
        try:
            renpy.log("[better-bilingual] %s" % message)
        except Exception:
            pass

    def bb_known_languages():
        try:
            return list(renpy.known_languages())
        except Exception:
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

    def bb_loadable(path):
        try:
            return renpy.loadable(path)
        except Exception:
            return False

    def bb_translated_font():
        for candidate in BB_TRANSLATED_FONT_CANDIDATES:
            if bb_loadable(candidate):
                return candidate

        try:
            if isinstance(gui.text_font, str):
                return gui.text_font
        except Exception:
            pass

        return "DejaVuSans.ttf"

    BB_TRANSLATED_FONT = bb_translated_font()
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
            config.language = BB_TRANSLATED_LANGUAGE
        except Exception as e:
            bb_log("could not set config.language: %r" % e)

        try:
            _preferences.language = BB_TRANSLATED_LANGUAGE
        except Exception as e:
            bb_log("could not set _preferences.language: %r" % e)

        try:
            renpy.game.preferences.language = BB_TRANSLATED_LANGUAGE
        except Exception as e:
            bb_log("could not set game.preferences.language: %r" % e)

        try:
            contexts = list(renpy.game.contexts)
        except Exception:
            contexts = []

        for ctx in contexts:
            try:
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

    def bb_language_for_text(language):
        if language == BB_MODE_ORIGINAL:
            return BB_ORIGINAL_FONT
        return BB_TRANSLATED_FONT

    def bb_font_tag(language, text):
        if text is None:
            return ""

        return "{font=%s}%s{/font}" % (bb_language_for_text(language), text)

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
        except Exception:
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

        try:
            if config.old_substitutions:
                text = bb_escape_old_substitution_percents(text)
                text = text % renpy.exports.tag_quoting_dict
        except Exception:
            pass

        try:
            return renpy.substitutions.substitute(text, translate=False)[0]
        except Exception:
            return text

    bb_string_maps_ready = False
    bb_original_to_translated = {}
    bb_translated_to_original = {}

    def bb_build_string_maps():
        global bb_string_maps_ready

        if bb_string_maps_ready:
            return

        try:
            strings = renpy.game.script.translator.strings.get(BB_TRANSLATED_LANGUAGE, None)
            if strings is not None:
                bb_original_to_translated.update(strings.translations)
        except Exception as e:
            bb_log("could not build string map: %r" % e)

        for original, translated in bb_original_to_translated.items():
            bb_translated_to_original.setdefault(translated, original)

        bb_string_maps_ready = True

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

        original = bb_node_text_for_identifier(identifier, None)
        if original is not None:
            entry.bb_original = bb_substitute(original)

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

    def bb_dialogue_render_props(language=None, outlined=False):
        props = {
            "style": "bb_dialogue",
            "substitute": False,
            "slow": False,
            "size": bb_dialogue_size(),
            "font": bb_language_for_text(language),
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
        key = (
            text,
            language,
            bool(outlined),
            int(gui.dialogue_width),
            int(config.screen_height),
            bb_dialogue_size(),
            bb_language_for_text(language),
            bb_style_signature(ruby_style),
        )

        rv = bb_dialogue_metrics_cache.get(key, None)
        if rv is not None:
            return rv

        try:
            probe = renpy.text.text.Text(text, **bb_dialogue_render_props(language, outlined))
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
        except Exception:
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

    def bb_history_pair(entry):
        identifier = getattr(entry, "bb_identifier", None)
        original = getattr(entry, "bb_original", None)

        if original is None:
            original = bb_original_text(entry.what, identifier or "")

        translated = bb_translated_text(entry.what, identifier or "")
        return bb_pair_from_values(translated, original)

    def bb_history_display_text(entry):
        return bb_join_pair(bb_history_pair(entry), with_fonts=True)

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
            return

        persistent.bb_mode = mode
        persistent.ll_better_bilingual_mode = mode
        persistent.ll_fast_original_mode = mode in (BB_MODE_ORIGINAL, BB_MODE_ORIGINAL_FIRST)

        bb_sync_engine_language()

        try:
            renpy.loader.loadable_cache.clear()
            renpy.loader.hash_cache.clear()
        except Exception:
            pass

        bb_clear_current_say_ranges()
        bb_clear_say_ranges_next_interact = True
        bb_refresh_current_say()
        bb_refresh_scene_images()
        renpy.restart_interaction()

    def bb_start_callback():
        bb_init_persistent()
        bb_sync_engine_language()

    def bb_after_load_callback():
        global bb_clear_say_ranges_next_interact

        bb_clear_say_ranges_next_interact = False
        bb_init_persistent()
        bb_sync_engine_language()

    bb_init_persistent()
    bb_sync_engine_language()

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
                        font bb_language_for_text(bb_current_language)
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
                            font bb_language_for_text(bb_second_language)
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
                text bb_current_what id "what" substitute False font bb_language_for_text(bb_current_language) color "#fff" outlines [(absolute(1), "#242424", absolute(1), absolute(1))] ruby_style bb_ruby_style() size persistent.dialogue_text_size
            else:
                text bb_current_what id "what" substitute False font bb_language_for_text(bb_current_language) size persistent.dialogue_text_size

    if not renpy.variant("small"):
        add SideImage() xalign 0.0 yalign 1.0

screen bb_quick_menu():
    variant "touch"

    zorder 100

    if quick_menu:
        hbox:
            style_prefix "quick"
            xalign 0.5
            yalign 1.0

            textbutton _("Back") action Rollback()
            textbutton _("Skip") action Skip() alternate Skip(fast=True, confirm=True)
            textbutton _("Auto") action Preference("auto-forward", "toggle")
            textbutton _("Progress") action ShowMenu('progressmod')
            textbutton _("Unlockables") action ShowMenu('unlockables')
            if show_hints:
                textbutton _("Hints") action ShowMenu('hinttracker')
            textbutton bb_mode_name() action BBToggle() alternate Show("bb_language_picker")
            textbutton _("Hide") action HideInterface()
            if persistent.show_console:
                textbutton _("Console") action QueueEvent("console")

screen bb_quick_menu():

    zorder 100

    if quick_menu:
        hbox:
            style_prefix "quick"
            xalign 0.5
            yalign 1.0

            textbutton _("History") action ShowMenu('history')
            textbutton _("Skip") action Skip() alternate Skip(fast=True, confirm=True)
            textbutton _("Auto") action Preference("auto-forward", "toggle")
            textbutton _("Girls") action ShowMenu('amitrackerm2')
            textbutton _("Progress") action ShowMenu('progressmod')
            textbutton _("Unlockables") action ShowMenu('unlockables')
            if show_hints:
                textbutton _("Hints") action ShowMenu('hinttracker')
            textbutton _("Save") action ShowMenu('save')
            textbutton _("Load") action ShowMenu('load')
            textbutton bb_mode_name() action BBToggle() alternate Show("bb_language_picker")
            textbutton _("Prefs") action ShowMenu('preferences')

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
    bb_install_screen_alias("quick_menu", "bb_quick_menu")
    bb_install_screen_alias("history", "bb_history", "menu")
    bb_patch_preferences_language_fragment(log_failure=False)
    if bb_patch_preferences_language_fragment_interact not in config.start_interact_callbacks:
        config.start_interact_callbacks.append(bb_patch_preferences_language_fragment_interact)
