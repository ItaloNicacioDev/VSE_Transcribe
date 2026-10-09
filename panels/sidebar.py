"""Sidebar panel for VSE_Transcribe in the 3D Viewport N-panel.

Workflow:
1. User selects video/audio file or VSE strip
2. Panel shows source info + auto-detects language
3. User selects/confirms target language
4. Click "Transcribe" button
5. Addon transcribes and creates subtitle strips in VSE
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
    """VSE_Transcribe panel in the 3D Viewport Sidebar (N-panel)."""

    bl_label = "VSE_Transcribe"
    bl_idname = "VSETRANSCRIBE_PT_sidebar"
    bl_space_type = "SEQUENCE_EDITOR"
    bl_region_type = "UI"
    bl_category = "VSE Transcribe"

    @classmethod
    def poll(cls, context: Context) -> bool:
        """Show panel in 3D Viewport when VSE Transcribe addon is enabled."""
        try:
            return _HAS_BPY and context.scene is not None
        except Exception:
            return False

    def draw(self, context: Context) -> None:
        """Draw the panel UI."""
        if not _HAS_BPY:
            return

        layout = self.layout
        
        # Get settings safely
        try:
            settings = context.scene.vse_transcribe
        except Exception:
            layout.box().label(text="Settings not loaded. Reinstall addon.", icon="ERROR")
            return

        # --- SOURCE SELECTION ---
        box = layout.box()
        box.label(text="Source", icon="SEQ_SEQUENCER")
        
        row = box.row(align=True)
        row.prop(settings, "use_vse_strip", toggle=True, text="Use VSE Strip")
        
        if settings.use_vse_strip:
            strip = self._get_active_strip(context)
            if strip:
                row = box.row()
                row.label(text=f"{strip.name}", icon="FILE_MOVIE" if strip.type == "MOVIE" else "SPEAKER")
                row = box.row()
                row.label(text=f"Type: {strip.type}  |  Channel: {strip.channel}  |  Frames: {strip.frame_final_duration}")
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
        else:
            row = box.row()
            row.prop(settings, "audio_source", text="Audio File")
            row = box.row()
            row.operator("vse_transcribe.browse_audio", text="", icon="FILE_FOLDER")
            if settings.audio_source:
                row = box.row()
                row.label(text=os.path.basename(settings.audio_source), icon="FILE_SOUND")
                try:
                    # Try to get duration? We'll skip for now.
                    pass
                except Exception:
                    pass
            else:
                row = box.row()
                row.label(text="No file selected", icon="BLANK1")

        layout.separator()

        # --- ENGINE SELECTION (compact) ---
        box = layout.box()
        box.label(text="Engine: Local Whisper", icon="FILE_TICK")
        self._draw_local_whisper_settings(box, settings)

        layout.separator()

        # --- LANGUAGE SELECTION (prominent) ---
        box = layout.box()
        box.label(text="Language", icon="LINENUMBERS_ON")
        
        row = box.row()
        # Auto-detect option
        row.prop(settings.local_whisper, "language", text="")
        
        # Auto-detect hint
        row = box.row()
        row.scale_y = 0.7
        row.label(text="Leave empty for auto-detect", icon="INFO")

        layout.separator()

        # --- CONTROLS ---
        col = layout.column(align=True)
        col.scale_y = 1.5
        
        row = col.row(align=True)
        row.scale_x = 2.0
        row.operator("vse_transcribe.transcribe", text="Transcribe", icon="FILE_TICK")
        
        row = col.row(align=True)
        row.scale_x = 2.0
        row.operator("vse_transcribe.cancel_transcription", text="Cancel", icon="CANCEL")
        
        row = col.row(align=True)
        row.scale_x = 2.0
        row.operator("vse_transcribe.generate_subtitles", text="Create Subtitle Strips", icon="PLUS")
        
        row = col.row(align=True)
        row.scale_x = 2.0
        row.operator("vse_transcribe.export_subtitles", text="Export", icon="EXPORT")
        
        row = col.row(align=True)
        row.scale_x = 2.0
        row.operator("vse_transcribe.clear_subtitles", text="Clear", icon="TRASH")

        layout.separator()

        # --- TRANSCRIPT STATUS ---
        if settings.transcript_storage:
            try:
                import json
                data = json.loads(settings.transcript_storage)
                seg_count = len(data.get("segments", []))
                lang = data.get("language", "?")
                dur = data.get("duration", 0)
                
                box = layout.box()
                box.label(text="Transcript Ready", icon="CHECKMARK")
                row = box.row()
                row.label(text=f"{seg_count} segments  •  {lang}  •  {dur:.1f}s")
                
                # Show subtitle settings compact
                layout.separator()
                self._draw_subtitle_settings_compact(layout, settings)
            except Exception:
                pass

        layout.separator()

        # --- TRANSCRIPTION PROGRESS ---
        if settings.is_transcribing:
            box = layout.box()
            box.label(text="Transcribing...", icon="TIME")
            # Progress bar
            row = box.row()
            row.prop(settings, "transcription_progress", text="")
            row = box.row()
            row.label(text=f"Progress: {settings.transcription_progress*100:.1f}%")
            # Current word
            if settings.last_word:
                row = box.row()
                row.label(text=f"Current word: {settings.last_word}", icon="SOUND")
            # Elapsed time
            if settings.transcription_elapsed > 0:
                mins = int(settings.transcription_elapsed // 60)
                secs = int(settings.transcription_elapsed % 60)
                row = box.row()
                row.label(text=f"Elapsed: {mins:02d}:{secs:02d}")
            # Animated icon (simple spinner)
            icons = ['TIME', 'FILE_REFRESH', 'FILE_TICK', 'FILE_CHECK', 'FILE_NEW', 'FILE_FOLDER', 'FILE_BLEND', 'FILE_SCRIPT']
            icon_idx = settings.transcription_icon_index % len(icons)
            row = box.row()
            row.label(text="", icon=icons[icon_idx])

    def _get_active_strip(self, context: Context):
        """Get the active sound/movie strip in the VSE."""
        if not _HAS_BPY:
            return None
        
        try:
            seq_editor = context.scene.sequence_editor
            if not seq_editor:
                return None
        except Exception:
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
        
        return None
        
    def _format_time(self, seconds: float) -> str:
        """Format seconds as MM:SS.mmm"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        millis = int((seconds - int(seconds)) * 1000)
        return f"{minutes:02d}:{secs:02d}.{millis:03d}"

    def _draw_local_whisper_settings(self, box, settings):
        row = box.row()
        row.prop(settings.local_whisper, "model_size")
        row = box.row()
        row.prop(settings.local_whisper, "device")
        row = box.row()
        row.prop(settings.local_whisper, "compute_type")
        row = box.row()
        row.prop(settings.local_whisper, "word_timestamps")
        row = box.row()
        row.prop(settings.local_whisper, "model_dir")

    def _draw_subtitle_settings_compact(self, layout, settings):
        """Draw compact subtitle settings."""
        box = layout.box()
        box.label(text="Subtitle Style", icon="FILE_TEXT")
        sub = settings.subtitle
        row = box.row(align=True)
        row.prop(sub, "max_chars_per_line", text="Max Chars")
        row = box.row(align=True)
        row.prop(sub, "max_lines", text="Lines")
        row = box.row(align=True)
        row.prop(sub, "min_duration", text="Min Dur")
        row = box.row(align=True)
        row.prop(sub, "gap_threshold", text="Gap")


# Registration handled by __init__.py
