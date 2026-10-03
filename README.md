# VSE_Transcribe

### AI transcription and subtitle generation for Blender's Video Sequence Editor

**VSE_Transcribe** is a modular Blender addon for transcribing audio and turning the result into synchronized, editable subtitles directly inside the **Video Sequence Editor (VSE)**.

Instead of exporting the audio to another application, generating subtitles externally and importing them back, VSE_Transcribe keeps the workflow inside Blender.

The transcription engine produces structured timestamped data, which is then converted into native Blender **Text Strips**. This keeps the subtitles part of the project itself — editable, stylable and fully integrated with the VSE timeline.

> **Built for Blender. Designed for an editor-first workflow.**

---

## What it does

VSE_Transcribe is focused on one workflow:

**Audio → Transcription → Timing → Subtitles → VSE**

The addon separates transcription from subtitle generation, allowing different AI engines to be used without changing the rest of the system.

### Core features

* AI-powered audio transcription
* Local transcription support
* Configurable external transcription APIs
* Timestamp-based subtitle generation
* Native Blender Text Strips
* Subtitle styling and layout controls
* Language configuration
* Word-level timestamps
* Modular transcription engine architecture
* N-panel integration
* Subtitle export architecture
* Designed for future transcription and editing tools

---

## Why VSE_Transcribe?

A common subtitle workflow looks like this:

```text
Video
  ↓
Export audio
  ↓
External transcription tool
  ↓
Generate subtitles
  ↓
Export SRT / VTT / ASS
  ↓
Import into Blender
  ↓
Adjust everything again
```

VSE_Transcribe aims to reduce that workflow to:

```text
Video
  ↓
VSE_Transcribe
  ↓
Transcription
  ↓
Native Text Strips
  ↓
Edit in Blender
```

The goal isn't to replace Blender's VSE with another editor.

The goal is to make the VSE better at handling transcription-based workflows.

---

# Architecture

VSE_Transcribe is built around a separation between **transcription**, **data**, and **Blender integration**.

```text
                         VSE_Transcribe
                               │
                    ┌──────────┴──────────┐
                    │                     │
              Transcription            VSE Layer
                 Engine                    │
                    │                     │
          ┌─────────┴─────────┐           │
          │                   │           │
     Local Engine        External API     │
          │                   │           │
          └─────────┬─────────┘           │
                    │                     │
                    ▼                     │
                Transcript ───────────────┘
                    │
                    ▼
             Subtitle Engine
                    │
                    ▼
             Blender Text Strips
```

The important part is the **Transcript** layer.

The subtitle system does not need to know whether the text came from Whisper, an external API or another engine.

Every engine produces the same internal data structure.

This makes the system easier to extend without coupling the entire addon to a single AI provider.

---

# Transcription Engines

VSE_Transcribe is designed around interchangeable transcription engines.

### Local

Local engines process the audio on the user's machine.

Typical implementation:

```text
Audio
  ↓
Whisper / faster-whisper
  ↓
Transcript
```

Advantages:

* No external API required
* Audio can remain local
* No mandatory subscription
* Works without depending on a specific provider
* Suitable for privacy-sensitive workflows

### External API

External services can be configured when the user prefers cloud-based transcription.

```text
Audio
  ↓
Configured API
  ↓
Transcript
```

Configuration can include:

* API endpoint
* API key
* Model
* Language
* Additional engine-specific options

The API implementation remains isolated from the rest of the addon.

---

# Transcript Model

Transcription results are represented as structured data rather than plain text.

Conceptually:

```text
Transcript
├── language
├── duration
└── segments
    ├── start
    ├── end
    ├── text
    └── words
        ├── text
        ├── start
        └── end
```

Example:

```text
00:00:01.200 → 00:00:03.800
"Olá pessoal, tudo bem?"

00:00:04.000 → 00:00:07.200
"Hoje vamos aprender a editar no Blender."
```

Keeping timing information at the data level makes the system suitable for future features such as:

* Word highlighting
* Text-based editing
* Animated captions
* Precise subtitle segmentation
* Search-based navigation
* Advanced subtitle timing tools

---

# Subtitle Generation

Once a transcript has been generated, VSE_Transcribe converts its segments into Blender Text Strips.

```text
Transcript Segment
       │
       ├── Start
       ├── End
       └── Text
              │
              ▼
       Subtitle Generator
              │
              ▼
        Blender Text Strip
```

The generated strips remain native Blender objects.

That means they can still be:

* Moved
* Trimmed
* Duplicated
* Edited
* Styled
* Animated
* Repositioned

directly from the VSE.

---

# Subtitle Styling

Subtitle appearance is controlled from the addon interface before generation.

Planned controls include:

| Property       | Description                 |
| -------------- | --------------------------- |
| Font           | Text font                   |
| Size           | Font size                   |
| Color          | Text color                  |
| Outline        | Outline width               |
| Shadow         | Shadow visibility           |
| Background     | Subtitle background / box   |
| Position       | Screen position             |
| Alignment      | Text alignment              |
| Max Characters | Maximum characters per line |
| Max Lines      | Maximum number of lines     |
| Timing         | Segment timing behavior     |

The styling system is intended to support reusable subtitle presets in the future.

---

# Blender Integration

VSE_Transcribe is designed around Blender's existing systems instead of creating parallel representations of the timeline.

Primary integration points include:

* Video Sequence Editor
* Text Strips
* Blender Properties
* Operators
* N-panel
* Menus
* Blender Python API

The main interface is exposed through the VSE Sidebar:

```text
VSE
└── Sidebar (N)
    └── VSE_Transcribe
        ├── Engine
        ├── Model
        ├── Language
        ├── Transcription
        └── Subtitles
```

---

# Project Structure

```text
VSE_Transcribe/
│
├── __init__.py
│
├── core/
│   ├── transcription.py
│   ├── subtitle_engine.py
│   ├── strip_manager.py
│   └── timecode.py
│
├── engines/
│   ├── base.py
│   ├── local_whisper.py
│   └── external_api.py
│
├── models/
│   └── transcript.py
│
├── operators/
│   ├── transcribe.py
│   ├── generate_subtitles.py
│   ├── clear_subtitles.py
│   └── export_subtitles.py
│
├── panels/
│   └── sidebar.py
│
├── properties/
│   └── settings.py
│
├── ui/
│   └── menus.py
│
└── utils/
    ├── audio.py
    ├── paths.py
    └── logging.py
```

### Module responsibilities

| Directory     | Responsibility                  |
| ------------- | ------------------------------- |
| `core/`       | Core application logic          |
| `engines/`    | Transcription implementations   |
| `models/`     | Transcript and data structures  |
| `operators/`  | Blender operators               |
| `panels/`     | Sidebar and panel UI            |
| `properties/` | Blender properties and settings |
| `ui/`         | Menus and interface elements    |
| `utils/`      | Shared utilities                |

The central `__init__.py` is responsible primarily for addon registration and unregistration.

The implementation of each subsystem remains isolated in its respective module.

---

# Installation

## From GitHub

Clone the repository:

```bash
git clone <REPOSITORY_URL>
```

Or download the repository as a ZIP file.

## Install in Blender

Open:

```text
Edit
└── Preferences
    └── Add-ons
        └── Install...
```

Select the VSE_Transcribe ZIP file.

Then enable:

```text
Preferences
└── Add-ons
    └── VSE_Transcribe
        └── Enable
```

During development, the addon can also be loaded directly from Blender's addons directory.

---

# Basic Workflow

## 1. Open the Video Sequence Editor

Switch an area to:

```text
Video Editing
```

or open the VSE workspace.

## 2. Add your media

Add a movie or audio strip containing the audio you want to transcribe.

```text
Add
└── Movie
```

## 3. Open VSE_Transcribe

With the mouse over the VSE, press:

```text
N
```

Open the:

```text
VSE_Transcribe
```

panel.

## 4. Select a transcription engine

Choose between an available local engine or a configured external API.

Example:

```text
Engine       [ Local Whisper ▼ ]
Model        [ ...             ]
Language     [ Auto            ]

             [ TRANSCRIBE ]
```

## 5. Generate the transcript

The selected engine processes the audio and returns timestamped segments.

## 6. Create subtitles

After transcription:

```text
SUBTITLES

[ CREATE SUBTITLES ]
```

VSE_Transcribe creates the corresponding Text Strips directly in the timeline.

```text
VIDEO    ███████████████████████████████████

AUDIO    ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓

TEXT     ░░ "Olá pessoal..." ░░
                  ░░ "Hoje vamos..." ░░
```

From this point onward, the subtitles are part of the Blender project.

---

# Privacy

VSE_Transcribe does not require a cloud transcription service as its only option.

When a local engine is used, transcription can be performed on the user's machine.

When an external API is selected, the audio is handled according to the configuration and privacy policy of that service.

The addon itself is designed to keep the transcription provider separate from the subtitle workflow.

---

# Export

Subtitle export is part of the project's architecture and will be handled independently from subtitle generation.

Planned formats include:

```text
SRT
VTT
ASS
```

Additional formats may be supported later.

---

# Roadmap

The project is being developed incrementally.

### V0.1 — Foundation

* [x] Modular addon structure
* [x] Central registration system
* [x] Settings architecture
* [x] VSE Sidebar integration
* [x] Transcription engine interface
* [x] Transcript data model

### V0.2 — Transcription

* [ ] Local transcription engine
* [ ] External API engine
* [ ] Language configuration
* [ ] Timestamp handling
* [ ] Word-level timestamps
* [ ] Error handling

### V0.3 — Subtitles

* [ ] Automatic segmentation
* [ ] Text Strip generation
* [ ] Subtitle styling
* [ ] Character limits
* [ ] Line limits
* [ ] Positioning
* [ ] Subtitle presets

### V0.4 — Export

* [ ] SRT
* [ ] VTT
* [ ] ASS

### Future

Possible future directions include:

* Text-based editing
* Word-level subtitle animation
* Advanced caption presets
* Timeline search through transcript
* AI-assisted editing tools
* Integration with other Blender addons

These features are intentionally outside the initial scope.

The current priority is to build a reliable transcription and subtitle foundation first.

---

# Development

VSE_Transcribe uses a modular architecture so new components can be added without rewriting the existing workflow.

New transcription engines should implement the interface defined in:

```text
engines/base.py
```

Core application logic belongs in:

```text
core/
```

Blender-specific operators belong in:

```text
operators/
```

This separation keeps the transcription layer independent from Blender's UI and timeline implementation.

---

# Compatibility

| Component              | Support                         |
| ---------------------- | ------------------------------- |
| Blender                | 5.2+                            |
| Operating Systems      | Windows / Linux / macOS         |
| Interface              | Blender Python API              |
| Editor                 | Video Sequence Editor           |
| Local transcription    | Whisper / faster-whisper        |
| External transcription | Configurable API                |
| Subtitle system        | Blender Text Strips             |
| Languages              | Depends on transcription engine |

> Compatibility may change as Blender and the supported transcription engines evolve.

---

# Project Status

VSE_Transcribe is currently under active development.

The architecture is being established before expanding the feature set, with particular attention to:

* Modular engines
* Reliable timestamp handling
* Native Blender integration
* Editable subtitle output
* Extensibility
* Local-first workflows

The project is not intended to become a separate video editor.

**It is a transcription and subtitle layer built specifically for the Blender VSE.**

---

# Author

**Italo Nicacio**

Full Stack Developer · Software Architecture · Open Source

---

# License

The project license will be defined before the first public release.

---

<div align="center">

**VSE_Transcribe**

AI transcription and subtitle generation for Blender VSE.

Built with Python and the Blender Python API.

</div>
