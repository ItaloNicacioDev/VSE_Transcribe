"""Sidebar panel for VSE_Transcribe in the VSE N-panel.

Workflow:
1. User selects video/audio strip in VSE
2. Panel shows strip info + auto-detects language
3. User selects/confirms target language
4. Click "Transcribe" button
5. Addon transcribes and auto-creates Text Strips synced with strip timing
"""

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
        try:
            return _HAS_BPY and context.scene and context.scene.sequence_editor is not None
        except Exception:
            return False

    def draw(self, context: Context) -> None:
        """Draw the panel UI - with full error handling."""
        if not _HAS_BPY:
            return

        layout = self.layout
        
        # Always show something - defensive coding
        try:
            self._draw_content(context)
        except Exception as e:
            # If anything fails, show error in panel
            box = layout.box()
            box.alert = True
            box.label(text="VSE_Transcribe Error", icon="ERROR")
            box.label(text=str(e)[:100])
            import traceback
            for line in traceback.format_exc().split('\n')[:5]:
                if line.strip():
                    box.label(text=line[:100])

    def _draw_content(self, context: Context) -> None:
        """Main draw logic with proper error handling."""
        if not _HAS_BPY:
            return

        layout = self.layout
        
        # Get settings safely
        try:
            settings = context.scene.vse_transcribe
        except Exception:
            layout.box().label(text="Settings not loaded. Reinstall addon.", icon="ERROR")
            return

        # --- STRIP SELECTION ---
        strip = self._get_active_strip(context)

        box = layout.box()
        box.label(text="Source Strip", icon="SEQ_SEQUENCER")

        # DEBUG: Show all strips found in timeline
        debug_box = box.box()
        debug_box.label(text="Debug: All Strips in Timeline", icon="INFO")
        try:
            seq_editor = context.scene.sequence_editor
            if seq_editor:
                # Try sequences_all (Blender 5.2+) fallback to sequences
                strips = getattr(seq_editor, "sequences_all", None)
                if strips is None:
                    strips = getattr(seq_editor, "sequences", [])
                for i, s in enumerate(strips):
                    row = debug_box.row()
                    row.scale_y = 0.7
                    is_selected = getattr(s, "select_get", lambda: s.select)()
                    sel_mark = " ✓" if is_selected else ""
                    act_mark = " ★" if getattr(seq_editor, "active_strip", None) == s else ""
                    row.label(text=f"{i}: {s.name} | Type: {s.type} | Ch:{s.channel}{sel_mark}{act_mark}")
            else:
                debug_box.label(text="No sequence editor")
        except Exception as e:
            debug_box.label(text=f"Debug error: {e}")

        if strip:
            # Show strip info prominently
            row = box.row()
            row.label(text=f"{strip.name}", icon="FILE_MOVIE" if strip.type == "MOVIE" else "SPEAKER")
            row = box.row()
            row.label(text=f"Type: {strip.type}  |  Channel: {strip.channel}  |  Frames: {strip.frame_final_duration}")
            
            # Show strip timing
            try:
                scene = context.scene
                fps = scene.render.fps / scene.render.fps_base
                start_sec = strip.frame_final_start / fps
                end_sec = strip.frame_final_end / fps
                row = box.row()
                row.label(text=f"Time: {self._format_time(start_sec)} → {self._format_time(end_sec)}  ({strip.frame_final_duration/fps:.1f}s)")
            except Exception:
                pass
        else:
            row = box.row()
            row.alert = True
            row.label(text="No strip selected", icon="ERROR")
            row = box.row()
            row.label(text="Select a SOUND or MOVIE strip in the VSE")

        # Only show rest if strip is selected
        if not strip:
            return

        layout.separator()

        # --- ENGINE SELECTION (compact) ---
        box = layout.box()
        row = box.row()
        row.label(text="Engine", icon="MODIFIER")
        row = box.row()
        row.prop(settings, "engine_type", expand=True)

        engine = settings.engine_type
        if engine == "local_whisper":
            self._draw_local_whisper_settings(box, settings)
        elif engine == "external_api":
            self._draw_external_api_settings(box, settings)

        layout.separator()

        # --- LANGUAGE SELECTION (prominent) ---
        box = layout.box()
        box.label(text="Language", icon="LINENUMBERS_ON")

        row = box.row()
        # Auto-detect option
        if engine == "local_whisper":
            row.prop(settings.local_whisper, "language", text="")
        elif engine == "external_api":
            row.prop(settings.external_api, "language", text="")
        
        # Auto-detect hint
        row = box.row()
        row.scale_y = 0.7
        row.label(text="Leave empty for auto-detect", icon="INFO")

        layout.separator()

        # --- TRANSCRIBE BUTTON (prominent) ---
        box = layout.box()
        row = box.row()
        row.scale_y = 1.5
        op = row.operator("vse_transcribe.transcribe", text="Transcribe", icon="FILE_TICK")
        try:
            op.enabled = not settings.is_transcribing
        except Exception:
            pass

        if settings.is_transcribing:
            row = box.row()
            row.label(text="Transcribing...", icon="TIME")

        # Show transcript status if available
        if settings.transcript_storage:
            try:
                import json
                data = json.loads(settings.transcript_storage)
                seg_count = len(data.get("segments", []))
                lang = data.get("language", "?")
                dur = data.get("duration", 0)
                
                layout.separator()
                box = layout.box()
                box.label(text="Transcript Ready", icon="CHECKMARK")
                row = box.row()
                row.label(text=f"{seg_count} segments  •  {lang}  •  {dur:.1f}s")
                
                # Auto-generate subtitles button
                row = box.row()
                row.scale_y = 1.2
                op = row.operator("vse_transcribe.generate_subtitles", text="Create Subtitle Strips", icon="PLUS")
                
                # Show subtitle settings compact
                layout.separator()
                self._draw_subtitle_settings_compact(layout, settings)
            except Exception:
                pass

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

    def _draw_subtitle_settings_compact(self, layout, settings):
        """Draw compact subtitle settings."""
        box = layout.box()
        box.label(text="Subtitle Style", icon="FILE_TEXT")
        sub = settings.subtitle
        row = box.row(align=True)
        row.prop(sub, "max_chars_per_line", text="Max Chars")
        row.prop(sub, "max_lines", text="Lines")
        row = box.row(align=True)
        row.prop(sub, "min_duration", text="Min Dur")
        row.prop(sub, "gap_threshold", text="Gap")

    def _get_active_strip(self, context: Context):
        """Get the active sound/movie strip in the VSE."""
        if not _HAS_BPY:
            return None

        try:
            seq_editor = context.scene.sequence_editor
            if not seq_editor:
                return None

            # Try sequences_all (Blender 5.2+) fallback to sequences
            strips = getattr(seq_editor, "sequences_all", None)
            if strips is None:
                strips = getattr(seq_editor, "sequences", [])

            # Strategy 1: Check selected strips (Blender 5.2+ uses select_get())
            for strip in strips:
                is_selected = getattr(strip, "select_get", lambda: strip.select)()
                if is_selected and strip.type in {"SOUND", "MOVIE"}:
                    return strip

            # Strategy 2: Check active strip
            active = getattr(seq_editor, "active_strip", None)
            if active and active.type in {"SOUND", "MOVIE"}:
                return active

            # Strategy 3: Fallback - any SOUND/MOVIE strip in the timeline
            for strip in strips:
                if strip.type in {"SOUND", "MOVIE"}:
                    return strip

        except Exception:
            pass

        return None

    def _format_time(self, seconds: float) -> str:
        """Format seconds as MM:SS.mmm"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        millis = int((seconds - int(seconds)) * 1000)
        return f"{minutes:02d}:{secs:02d}.{millis:03d}"


# Registration handled by __init__.py