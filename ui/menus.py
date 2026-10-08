"""Menu integration for VSE_Transcribe.

Adds menu items to the Video Sequence Editor menus.
"""

from __future__ import annotations

try:
    import bpy
    from bpy.types import Menu, Context
    _HAS_BPY = True
except ImportError:
    class Menu:
        pass
    class Context:
        pass
    _HAS_BPY = False


class VSETRANSCRIBE_MT_main_menu(Menu):
    """Main menu for VSE_Transcribe in the VSE header."""

    bl_label = "VSE_Transcribe"
    bl_idname = "VSETRANSCRIBE_MT_main_menu"

    def draw(self, context: Context) -> None:
        """Draw the menu items."""
        if not _HAS_BPY:
            return

        layout = self.layout
        settings = context.scene.vse_transcribe

        # Transcribe
        layout.operator("vse_transcribe.transcribe", icon="REC")

        # Generate subtitles
        layout.operator("vse_transcribe.generate_subtitles", icon="PLUS")

        # Clear subtitles
        layout.operator("vse_transcribe.clear_subtitles", icon="TRASH")

        layout.separator()

        # Export submenu
        layout.menu("VSETRANSCRIBE_MT_export_menu", icon="EXPORT")

        layout.separator()

        # Open sidebar
        layout.operator("wm.call_panel", text="Open Sidebar", icon="PREFERENCES").name = "VSETRANSCRIBE_PT_sidebar"


class VSETRANSCRIBE_MT_export_menu(Menu):
    """Export format submenu."""

    bl_label = "Export Subtitles"
    bl_idname = "VSETRANSCRIBE_MT_export_menu"

    def draw(self, context: Context) -> None:
        """Draw export format options."""
        if not _HAS_BPY:
            return

        layout = self.layout

        # SRT
        op = layout.operator("vse_transcribe.export_subtitles", text="SubRip (.srt)")
        op.format = "SRT"

        # VTT
        op = layout.operator("vse_transcribe.export_subtitles", text="WebVTT (.vtt)")
        op.format = "VTT"

        # ASS
        op = layout.operator("vse_transcribe.export_subtitles", text="Advanced SubStation Alpha (.ass)")
        op.format = "ASS"


# Menu registration functions
def menu_draw(self, context: Context) -> None:
    """Draw menu in VSE header."""
    if not _HAS_BPY:
        return

    layout = self.layout
    layout.menu("VSETRANSCRIBE_MT_main_menu", icon="SEQUENCE")


def register_menus() -> None:
    """Register menu classes and append to VSE menus."""
    if not _HAS_BPY:
        return

    bpy.utils.register_class(VSETRANSCRIBE_MT_main_menu)
    bpy.utils.register_class(VSETRANSCRIBE_MT_export_menu)

    # Append to VSE header menu - try different menu names for Blender version compatibility
    menu_targets = [
        "SEQUENCE_MT_editor_menus",
        "SEQUENCE_MT_menu",
        "SEQUENCE_MT_view",
        "SEQUENCE_MT_header",
    ]

    for menu_name in menu_targets:
        try:
            menu = getattr(bpy.types, menu_name)
            menu.append(menu_draw)
            break
        except AttributeError:
            continue

    # Also add to strip context menu (right-click on strip)
    strip_menu_targets = [
        "SEQUENCE_MT_strip",
        "SEQUENCE_MT_strip_context_menu",
    ]

    for menu_name in strip_menu_targets:
        try:
            menu = getattr(bpy.types, menu_name)
            menu.append(menu_draw)
            break
        except AttributeError:
            continue


def unregister_menus() -> None:
    """Unregister menu classes and remove from VSE menus."""
    if not _HAS_BPY:
        return

    # Remove from VSE menus - try all possible targets
    menu_targets = [
        "SEQUENCE_MT_editor_menus",
        "SEQUENCE_MT_menu",
        "SEQUENCE_MT_view",
        "SEQUENCE_MT_header",
    ]

    for menu_name in menu_targets:
        try:
            menu = getattr(bpy.types, menu_name)
            menu.remove(menu_draw)
        except (AttributeError, ValueError):
            pass

    # Remove from strip context menu
    strip_menu_targets = [
        "SEQUENCE_MT_strip",
        "SEQUENCE_MT_strip_context_menu",
    ]

    for menu_name in strip_menu_targets:
        try:
            menu = getattr(bpy.types, menu_name)
            menu.remove(menu_draw)
        except (AttributeError, ValueError):
            pass

    bpy.utils.unregister_class(VSETRANSCRIBE_MT_export_menu)
    bpy.utils.unregister_class(VSETRANSCRIBE_MT_main_menu)