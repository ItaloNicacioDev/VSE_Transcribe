VSE_Transcribe

<div align="center">

VSE_Transcribe

AI-powered transcription and subtitle generation for Blender VSE







Developed by Italo Nicacio

</div>

Sobre

VSE_Transcribe é um addon modular para o Blender Video Sequence Editor (VSE) focado em transcrição automática por IA e geração de legendas diretamente na timeline.

A proposta é aproveitar a infraestrutura nativa do VSE em vez de criar um editor de vídeo separado. O addon transforma uma transcrição sincronizada em Text Strips nativas do Blender, mantendo as legendas editáveis dentro do próprio projeto.

Principais objetivos

🎙️ Transcrição automática por IA

🧠 Engine híbrida: IA local gratuita + API externa configurável

📝 Geração automática de legendas

⏱️ Sincronização por timestamps

🎨 Controle completo do estilo das Text Strips

🎬 Integração direta com o Blender VSE

🧩 Arquitetura modular e extensível

⚙️ Configurações acessíveis pelo painel N

🔌 Preparado para múltiplos engines de transcrição

✨ Funcionalidades

🎙️ Transcrição por IA

O VSE_Transcribe será capaz de utilizar diferentes engines sem prender o restante do addon a uma implementação específica.

                    VSE_Transcribe
                          │
                 ┌────────┴────────┐
                 │ Transcription   │
                 │    Interface    │
                 └────────┬────────┘
                          │
             ┌────────────┴────────────┐
             │                         │
             ▼                         ▼
      Local Whisper              External API
      ─────────────              ────────────
      Gratuito                   Configurável
      Offline                    API Key
      Privado                    Endpoint

📝 Geração de legendas

A transcrição será convertida em segmentos sincronizados:

00:00:01.200 → 00:00:03.800
"Olá pessoal, tudo bem?"

00:00:04.000 → 00:00:07.200
"Hoje vamos aprender a editar no Blender."

Cada segmento poderá ser convertido em uma Text Strip do VSE.

🎨 Estilo das legendas

O painel próprio do addon permitirá controlar as propriedades das legendas, incluindo:

Fonte

Tamanho

Cor

Outline

Sombra

Fundo/Box

Posição

Alinhamento

Quebra de linhas

Limite de caracteres

Configurações de timing

As Text Strips continuam sendo objetos nativos do Blender e podem ser editadas manualmente depois da geração.

🧠 Arquitetura

O projeto foi pensado para ser modular desde o início.

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

__init__.py

O __init__.py central é responsável por registrar e remover os componentes do addon:

Blender
  │
  ▼
VSE_Transcribe/__init__.py
  │
  ├── Properties
  ├── Operators
  ├── Panels
  ├── Menus
  │
  └── Registration / Unregistration

A lógica de cada sistema permanece separada nos respectivos módulos.

🧠 Modelo de dados

A transcrição não será armazenada apenas como texto.

O objetivo é trabalhar com uma estrutura semelhante a:

Transcript
│
├── language
├── duration
│
└── segments
    │
    ├── start
    ├── end
    ├── text
    │
    └── words
        ├── text
        ├── start
        └── end

Isso permite manter precisão temporal e deixa a arquitetura preparada para recursos futuros, como edição baseada em texto, destaque de palavras e animações sincronizadas.

🛠️ Tecnologias

<div align="center">







</div>

Algumas dependências de IA ainda estão sendo definidas durante o desenvolvimento. A implementação final poderá variar conforme o engine escolhido.

📦 Compatibilidade

Componente

Suporte

Blender

5.2+

Sistema operacional

Windows / Linux / macOS

Interface

Blender Python API

Editor

Video Sequence Editor

Transcrição local

Whisper / faster-whisper

Transcrição externa

API configurável

Legendas

Blender Text Strips

Idiomas

Depende do engine de IA

🚀 Instalação

1. Baixe o projeto

Clone o repositório:

git clone <URL_DO_REPOSITORIO>

Ou baixe o projeto como ZIP pelo GitHub.

2. Instale no Blender

No Blender:

Edit
 └── Preferences
      └── Add-ons
           └── Install...

Selecione o arquivo ZIP do VSE_Transcribe.

Depois:

Preferences
 └── Add-ons
      └── VSE_Transcribe
           ☑ Enable

Durante o desenvolvimento, também é possível trabalhar diretamente com a pasta do addon no diretório de addons do Blender.

🎬 Como usar

1. Abra o Video Sequence Editor

No Blender:

Shift + F3

ou altere qualquer área para:

Video Editing

2. Adicione o vídeo

No VSE:

Add
 └── Movie

Selecione o vídeo que deseja transcrever.

O áudio precisa estar disponível para o engine de transcrição.

3. Abra o painel do VSE_Transcribe

Com o mouse sobre o VSE:

N

Isso abre a Sidebar.

Procure:

VSE_Transcribe

4. Escolha o engine

O addon terá suporte para dois tipos principais:

Local

Engine:
[ Local Whisper ▼ ]

A transcrição será processada localmente, sem necessidade de enviar o áudio para um serviço externo.

API externa

Engine:
[ External API ▼ ]

API URL:
[ https://... ]

API Key:
[ ******** ]

Model:
[ ... ]

A API será configurável pelo usuário.

5. Transcreva

Com o vídeo selecionado:

VSE_Transcribe
│
├── Engine
├── Model
├── Language
│
└── [ TRANSCRIBE ]

O engine processará o áudio e retornará os segmentos com seus timestamps.

6. Gere as legendas

Depois da transcrição:

SUBTITLES

[ CREATE SUBTITLES ]

O addon criará automaticamente as Text Strips correspondentes aos segmentos.

Exemplo:

VSE TIMELINE

VIDEO
████████████████████████████████████

AUDIO
▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓

CAPTIONS
░░░░ "Olá pessoal..." ░░░░
              ░░░░ "Hoje vamos..." ░░░░

🎨 Configuração das legendas

Antes de gerar as Text Strips, o usuário poderá configurar o estilo no painel:

STYLE

Font
[ Blender Font ▼ ]

Size
[ 48 ]

Color
[ █████████ ]

Outline
[ 2.0 ]

Shadow
[ ✓ ]

Background
[ ✓ ]

Position
[ Center / Bottom ▼ ]

Alignment
[ Center ▼ ]

Max Characters
[ 42 ]

Max Lines
[ 2 ]

As configurações serão aplicadas às novas legendas geradas.

Depois da criação, cada Text Strip continua editável diretamente pelo Blender.

🔌 Engine híbrida

O sistema de transcrição foi projetado para não depender de um único fornecedor.

Local

LocalWhisperEngine
        │
        ▼
Áudio
        │
        ▼
Whisper / faster-whisper
        │
        ▼
Transcript

API

ExternalAPIEngine
        │
        ▼
Áudio
        │
        ▼
API configurada pelo usuário
        │
        ▼
Transcript

Ambos devem retornar uma estrutura comum para o restante do addon.

Isso significa que o sistema de legendas não precisa saber qual IA foi utilizada.

🔒 Privacidade

Quando o usuário utilizar o engine local, o áudio poderá ser processado localmente.

Quando uma API externa for selecionada, o áudio poderá ser enviado ao serviço configurado pelo usuário.

O VSE_Transcribe não deve exigir uma API paga para funcionar quando o engine local estiver disponível.

📤 Exportação

A arquitetura já reserva um módulo para exportação:

operators/export_subtitles.py

O objetivo é permitir futuramente:

SRT

VTT

ASS

Outros formatos compatíveis

A implementação de exportação será adicionada conforme o desenvolvimento avançar.

🗺️ Roadmap

V0.1 — Core

Estrutura modular

Sistema central de registro

Settings

N Panel

Interface de engines

Modelo de transcript

V0.2 — Transcrição

Engine local

Engine externo

Detecção de idioma

Timestamps

Word-level timestamps

Tratamento de erros

V0.3 — Legendas

Segmentação automática

Criação de Text Strips

Estilos

Controle de linhas

Controle de caracteres

Posicionamento

Aplicação de presets

V0.4 — Exportação

SRT

VTT

ASS

Futuro

Recursos como edição baseada em transcrição e ferramentas avançadas de edição por IA não fazem parte do escopo inicial. O foco atual é construir um sistema de transcrição + legendagem profissional e sólido.

🤝 Desenvolvimento

O projeto utiliza uma arquitetura modular para facilitar:

novos engines de IA;

novos formatos de legenda;

novos estilos;

novos operadores;

novas interfaces;

integração futura com outras ferramentas do Blender.

Novos engines devem implementar a interface definida em:

engines/base.py

A lógica de negócio deve permanecer em core/, enquanto os operadores do Blender ficam em operators/.

📁 Organização do código

Diretório

Responsabilidade

core/

Lógica principal

engines/

Engines de transcrição

models/

Estruturas de dados

operators/

Operadores Blender

panels/

Interface do painel N

properties/

Configurações

ui/

Menus e elementos de interface

utils/

Utilitários

👤 Autor

Italo Nicacio



📄 Licença

A licença do projeto será definida antes do primeiro release público.

<div align="center">

VSE_Transcribe

AI transcription and subtitle generation for Blender VSE.

Made with Python and Blender.

</div>