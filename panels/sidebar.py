"""Sidebar panel for VSE_Transcribe in the VSE N-panel."""

from __future__ import annotations

try:
    import bpy
    from bpy.types import Panel, Context
    _HAS_BPY = True
except ImportError:
    class Panel:
        pass
    class Context:
        pass
    _HAS_BPY = False


class VSETRANSCRIBE_PT_sidebar(Panel):
    """VSE_Transcribe panel in the VSE Sidebar (N-panel)."""

    bl_label = "VSE_Transcribe"
    bl_idname = "VSETRANSCRIBE_PT_sidebar"
    bl_space_type = "SEQUENCE_EDITOR"
    bl_region_type = "UI"
    bl_category = "VSE_Transcribe"

    @classmethod
    def poll(cls, context: Context) -> bool:
        """Show panel only in VSE."""
        return _HAS_BPY and context.scene.sequence_editor is not None

    def draw(self, context: Context) -> None:
        """Draw the panel UI."""
        if not _HAS_BPY:
            return

        layout = self.layout
        settings = context.scene.vse_transcribe

        # --- ENGINE SECTION ---
        box = layout.box()
        box.label(text="Engine", icon="MODIFIER")

        row = box.row()
        row.prop(settings, "engine_type", expand=True)

        engine = settings.engine_type
        if engine == "local_whisper":
            self._draw_local_whisper_settings(box, settings)
        elif engine == "external_api":
            self._draw_external_api_settings(box, settings)

        # --- AUDIO SOURCE ---
        box = layout.box()
        box.label(text="Audio Source", icon="SPEAKER")

        row = box.row()
        row.prop(settings, "audio_source", text="")

        # Show active strip info
        active_strip = self._get_active_sound_strip(context)
        if active_strip:
            info_row = box.row()
            info_row.enabled = False
            info_row.label(text=f"Active: {active_strip.name}", icon="INFO")

        # --- TRANSCRIPTION ---
        box = layout.box()
        box.label(text="Transcription", icon="REC")

        # Language (common to both engines)
        if engine == "local_whisper":
            row = box.row()
            row.prop(settings.local_whisper, "language", text="Language")
        elif engine == "external_api":
            row = box.row()
            row.prop(settings.external_api, "language", text="Language")

        # Transcribe button
        row = box.row()
        row.scale_y = 1.3
        row.operator("vse_transcribe.transcribe", icon="FILE_TICK")

        # Show transcript status
        if settings.transcript_storage:
            try:
                import json
                data = json.loads(settings.transcript_storage)
                seg_count = len(data.get("segments", []))
                lang = data.get("language", "?")
                box.label(text=f"Ready: {seg_count} segments ({lang})", icon="CHECKMARK")
            except Exception:
                box.label(text="Transcript stored (parse error)", icon="ERROR")

        if settings.is_transcribing:
            row = box.row()
            row.label(text="Transcribing...", icon="TIME")

        # --- SUBTITLES ---
        box = layout.box()
        box.label(text="Subtitles", icon="FILE_TEXT")

        # Subtitle settings
        sub = settings.subtitle
        row = box.row()
        row.prop(sub, "max_chars_per_line")
        row = box.row()
        row.prop(sub, "max_lines")
        row = box.row()
        row.prop(sub, "min_duration")
        row = box.row()
        row.prop(sub, "gap_threshold")

        # Generate/Clear buttons
        row = box.row()
        row.scale_y = 1.2
        op = row.operator("vse_transcribe.generate_subtitles", icon="PLUS")
        op.enabled = bool(settings.transcript_storage)

        row = box.row()
        op = row.operator("vse_transcribe.clear_subtitles", icon="TRASH")
        op.enabled = bool(settings.generated_strips or context.scene.sequence_editor)

        # --- EXPORT ---
        box = layout.box()
        box.label(text="Export", icon="EXPORT")

        row = box.row()
        row.operator("vse_transcribe.export_subtitles", icon="FILE_TICK")

    def _draw_local_whisper_settings(self, box, settings):
        """Draw Local Whisper specific settings."""
        lw = settings.local_whisper

        row = box.row()
        row.prop(lw, "model_size")
        row = box.row()
        row.prop(lw, "device")
        row = box.row()
        row.prop(lw, "compute_type")
        row = box.row()
        row.prop(lw, "word_timestamps")

    def _draw_external_api_settings(self, box, settings):
        """Draw External API specific settings."""
        ea = settings.external_api

        row = box.row()
        row.prop(ea, "endpoint")
        row = box.row()
        row.prop(ea, "api_key")
        row = box.row()
        row.prop(ea, "model")
        row = box.row()
        row.prop(ea, "timeout")

    def _get_active_sound_strip(self, context: Context):
        """Get the active sound strip."""
        if not _HAS_BPY:
            return None

        seq_editor = context.scene.sequence_editor
        if not seq_editor:
            return None

        for strip in context.selected_sequences:
            if strip.type == "SOUND":
                return strip

        active = seq_editor.active_strip
        if active and active.type == "SOUND":
            return active

        return None


# Registration handled by __init__.py