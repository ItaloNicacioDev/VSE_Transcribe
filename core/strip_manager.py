"""Fronteira entre dados de legenda (core puro) e Text Strips do VSE.

Este módulo é o único lugar do addon que encosta em `bpy` para criar,
listar e remover Text Strips gerados pelo VSE_Transcribe.

Blender target: 5.2.0

Notas sobre a API (ver decisões e dúvidas no relatório):
    - Em Blender 4.x, Text Strips são criados via
      ``sequences.new_effect(name=..., type='TEXT', channel=...,
      frame_start=..., frame_end=...)`` ou pelo atalho
      ``sequences.new_text``. Eles retornam objetos do tipo
      ``TextSequence`` / ``EffectSequence``.
    - Em Blender 5.x, ``new_effect`` permanece documentado para efeitos
      (TEXT é um "effect" na taxonomia do VSE). Mantemos fallback entre
      ``new_effect('TEXT')`` e ``new_text`` para tolerância.
"""

from __future__ import annotations

from typing import List, Optional

try:
    import bpy  # type: ignore
    _HAS_BPY = True
except ImportError:  # fora do Blender (testes de sintaxe / lint apenas)
    bpy = None  # type: ignore
    _HAS_BPY = False

# Só usados como anotação (strings). No Blender 5.x alguns nomes mudaram
# (ex.: TextSequence -> TextStrip), então NÃO importamos de bpy.types.
Scene = object  # type: ignore
SequenceEditor = object  # type: ignore
TextSequence = object  # type: ignore


def _strips_collection(seq_editor):
    """Coleção de strips do nível superior (Blender 5.x: strips; 4.x: sequences)."""
    coll = getattr(seq_editor, "strips", None)
    if coll is None:
        coll = getattr(seq_editor, "sequences", None)
    return coll


# Helper local para compatibilidade Blender 5.2+ (sequences_all) / 4.x (sequences)
def _get_sequences_local(seq_editor: "SequenceEditor") -> List:
    """Get sequences list with Blender version compatibility."""
    if seq_editor is None:
        return []
    for attr in ("strips_all", "sequences_all", "strips", "sequences"):
        coll = getattr(seq_editor, attr, None)
        if coll is not None:
            return coll
    return []

# Importação tolerante: o Subagente 1 pode ainda não ter entregue os módulos.
try:
    from .subtitle_engine import SubtitleBlock  # type: ignore
except Exception:  # pragma: no cover - fallback estrutural
    from dataclasses import dataclass, field

    @dataclass
    class SubtitleBlock:  # type: ignore[no-redef]
        start: float
        end: float
        text: str
        lines: List[str] = field(default_factory=list)

try:
    from .timecode import seconds_to_frames  # type: ignore
except Exception:  # pragma: no cover - fallback estrutural
    def seconds_to_frames(seconds: float, fps: float) -> int:  # type: ignore[no-redef]
        return int(round(seconds * fps))


# Chave custom ID-property usada para marcar strips gerenciados pelo addon.
# Duplo underscore para evitar colisão com outras propriedades.
MANAGED_KEY = "__vse_transcribe_managed__"

# Limites aceitos de canal no VSE.
MIN_CHANNEL = 1
MAX_CHANNEL = 128


class StripManager:
    """Cria, lista e remove Text Strips de legenda no VSE.

    Args:
        scene: ``bpy.types.Scene`` cujo ``sequence_editor`` hospedará os strips.
        sequencer: ``bpy.types.SequenceEditor`` (``scene.sequence_editor``).
            Passado explicitamente para facilitar testes/mock e deixar claro
            o contrato com o chamador.
    """

    def __init__(self, scene: "Scene", sequencer: "SequenceEditor") -> None:
        if sequencer is None:
            raise ValueError(
                "sequencer é None — chame scene.sequence_editor_create() antes."
            )
        self.scene = scene
        self.sequencer = sequencer

    # ------------------------------------------------------------------
    # Validação
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_block(block: SubtitleBlock) -> None:
        if block.start < 0:
            raise ValueError(f"start negativo: {block.start}")
        if block.end <= block.start:
            raise ValueError(
                f"end ({block.end}) deve ser maior que start ({block.start})"
            )
        if not (block.text or block.lines):
            raise ValueError("block sem texto (text e lines vazios)")

    @staticmethod
    def _validate_channel(channel: int) -> None:
        if not (MIN_CHANNEL <= channel <= MAX_CHANNEL):
            raise ValueError(
                f"channel {channel} fora do intervalo "
                f"[{MIN_CHANNEL}, {MAX_CHANNEL}]"
            )

    # ------------------------------------------------------------------
    # FPS
    # ------------------------------------------------------------------

    def _fps(self) -> float:
        fps = self.scene.render.fps / self.scene.render.fps_base
        if fps <= 0:
            raise ValueError("FPS da cena inválido")
        return float(fps)

    # ------------------------------------------------------------------
    # API principal
    # ------------------------------------------------------------------

    def create_subtitle_strips(
        self, blocks: List[SubtitleBlock], channel: int
    ) -> List["TextSequence"]:
        """Cria Text Strips no ``channel`` a partir de ``blocks``.

        Garante não-sobreposição no ``channel``: quando um strip colidiria
        com strips já existentes naquele canal, ele é deslocado para depois
        do maior ``frame_final_end`` ocupado no canal.

        Returns:
            Lista dos Text Strips criados (na ordem dos blocks).
        """
        if not _HAS_BPY:
            raise RuntimeError("bpy indisponível: fora do runtime do Blender")
        if not blocks:
            raise ValueError("blocks vazio")
        self._validate_channel(channel)
        for b in blocks:
            self._validate_block(b)

        fps = self._fps()
        created: List["TextSequence"] = []

        for block in blocks:
            frame_start = seconds_to_frames(block.start, fps)
            frame_end = seconds_to_frames(block.end, fps)

            # Não-sobreposição: empurra para depois do último frame ocupado
            # no canal, se necessário.
            occupied_end = self._channel_occupied_end(channel)
            if occupied_end is not None and frame_start < occupied_end:
                shift = occupied_end - frame_start
                frame_start += shift
                frame_end += shift

            text = block.text if block.text else "\n".join(block.lines)
            strip = self._new_text_strip(
                name=self._strip_name(block),
                channel=channel,
                frame_start=frame_start,
                frame_end=frame_end,
                text=text,
            )
            strip[MANAGED_KEY] = True
            created.append(strip)

        return created

    def remove_subtitle_strips(self, strips: List["TextSequence"]) -> None:
        """Remove strips gerenciados (silenciosamente ignora não-gerenciados)."""
        if not _HAS_BPY:
            raise RuntimeError("bpy indisponível")
        for strip in list(strips):
            if strip is None:
                continue
            if strip.get(MANAGED_KEY):
                try:
                    _strips_collection(self.sequencer).remove(strip)
                except Exception:
                    # strip já removido externamente
                    pass

    def get_managed_strips(self) -> List["TextSequence"]:
        """Retorna todos os strips marcados como gerenciados pelo addon."""
        if not _HAS_BPY:
            raise RuntimeError("bpy indisponível: fora do runtime do Blender")
        out: List["TextSequence"] = []
        for seq in _get_sequences_local(self.sequencer):
            if seq.get(MANAGED_KEY):
                out.append(seq)
        return out

    def clear_managed_strips(self) -> int:
        """Remove todos os strips gerenciados. Retorna quantos foram removidos."""
        managed = self.get_managed_strips()
        for strip in managed:
            try:
                _strips_collection(self.sequencer).remove(strip)
            except Exception:
                pass
        return len(managed)

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------

    def _channel_occupied_end(self, channel: int) -> Optional[int]:
        """Maior ``frame_final_end`` entre os strips atualmente em ``channel``.

        Retorna ``None`` se o canal está vazio.
        """
        end: Optional[int] = None
        for seq in _get_sequences_local(self.sequencer):
            if seq.channel == channel:
                frame_end = seq.frame_final_end
                if end is None or frame_end > end:
                    end = frame_end
        return end

    def _new_text_strip(
        self,
        name: str,
        channel: int,
        frame_start: int,
        frame_end: int,
        text: str,
    ) -> "TextSequence":
        """Cria o Text Strip, com tolerância a variações da API 4.x/5.x.

        Preferência: ``sequences.new_text`` (atalho específico). Fallback:
        ``sequences.new_effect(type='TEXT')``.
        """
        seqs = _strips_collection(self.sequencer)
        length = max(1, int(frame_end) - int(frame_start))

        def _create(fn, **extra):
            # Blender 5.x usa ``length``; versões antigas usam ``frame_end``.
            try:
                return fn(name=name, channel=channel, frame_start=frame_start,
                          length=length, **extra)
            except TypeError:
                return fn(name=name, channel=channel, frame_start=frame_start,
                          frame_end=frame_end, **extra)

        if hasattr(seqs, "new_text"):
            strip = _create(seqs.new_text)
        else:
            strip = _create(seqs.new_effect, type="TEXT")

        # ``text`` é a propriedade padrão do TextSequence em 4.x.
        # Blender 5.x pode usar ``body``. Tentamos ambos.
        if hasattr(strip, "text"):
            strip.text = text
        elif hasattr(strip, "body"):
            strip.body = text
        else:
            # Fallback: tentar definir via setattr
            try:
                strip.text = text
            except Exception:
                pass
        return strip

    @staticmethod
    def _strip_name(block: SubtitleBlock) -> str:
        snippet = (block.text or (block.lines[0] if block.lines else ""))[:24]
        snippet = snippet.replace("\n", " ").strip()
        return f"VSET_{snippet}" if snippet else "VSET_Subtitle"