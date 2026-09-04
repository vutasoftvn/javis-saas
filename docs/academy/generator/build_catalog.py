import sys, os

sys.path.insert(0, '/Volumes/SSD/javis-saas/docs/academy/generator')
import module_00, module_01, module_02, module_03, module_04, module_05, module_06

modules = [
    module_00, module_01, module_02, module_03, module_04, module_05, module_06
]

out = []
out.append('# COSA Academy: Complete Slide & Audio Production Master Catalog')
out.append('')
out.append('> **Comprehensive Production Assets for all 7 Modules and 62 Lessons (124 Production Files)**')
out.append('')
out.append('Every lesson in the COSA Academy lifecycle curriculum has been paired into **two production-grade files**:')
out.append('1. **`{prefix}-slides-prompt.md`**: Tailored for **Gemini Notebook (NotebookLM / Gemini Pro)** to generate complete 5-6 slide decks with exact layout rules, visual generation directives, color tokens, and clean typography matching the COSA dark theme.')
out.append('2. **`{prefix}-audio-script.md`**: Tailored for **TTS Software** (ElevenLabs, OpenAI TTS, Descript, Azure) with voice actor personas, pacing brackets `[pause 0.5s]`, emotional tone annotations, slide sync checkpoints, and continuous raw narration blocks.')
out.append('')
out.append('---')
out.append('')
out.append('## 1. Production Workflow: From Text to Published Video')
out.append('')
out.append('```mermaid')
out.append('flowchart LR')
out.append('    A["Prompt File<br/>(slides-prompt.md)"] -->|Copy Prompt| B["Gemini Notebook / NotebookLM<br/>(Generate Deck)"]')
out.append('    B --> C["Slide Deck Export<br/>(PNG / PDF / 16:9)"]')
out.append('    D["Script File<br/>(audio-script.md)"] -->|Paste Script| E["TTS Engine<br/>(ElevenLabs / OpenAI)"]')
out.append('    E --> F["Audio Narration<br/>(WAV / MP3)"]')
out.append('    C --> G["Video Assembly<br/>(CapCut / Premiere / Descript)"]')
out.append('    F --> G')
out.append('    G --> H["Published Lesson Video<br/>(1080p MP4 / YouTube / LMS)"]')
out.append('```')
out.append('')
out.append('### Step A: Generating Slides via Gemini Notebook')
out.append('1. Open **Gemini Notebook (NotebookLM)** or **Gemini 1.5 Pro**.')
out.append('2. Open the corresponding `{prefix}-slides-prompt.md` file.')
out.append('3. Scroll to the bottom and copy the **Master Execution Prompt Block**.')
out.append('4. Paste the prompt block into Gemini Notebook.')
out.append('5. Gemini generates the structured presentation slides matching the exact slide-by-slide layout, design tokens, and visual archetypes.')
out.append('')
out.append('### Step B: Generating Voiceover via TTS Software')
out.append('1. Open **ElevenLabs** (recommended voice: *Adam* or *George* - Mature, authoritative, paced) or **OpenAI TTS** (recommended voice: *Onyx* or *Echo*).')
out.append('2. Open the corresponding `{prefix}-audio-script.md` file.')
out.append('3. For single-take batch generation: Scroll to Section 3 (**Complete Continuous Narration Script**) and copy the clean raw text.')
out.append('4. Set speech rate to **130 WPM** (steady, measured executive mentor cadence).')
out.append('5. Generate and export the high-fidelity audio file (`.wav` or `.mp3`).')
out.append('')
out.append('### Step C: Assembling the Lesson Video')
out.append('1. Import the exported slide deck images (16:9 1920x1080) and the generated audio track into your editor (**CapCut**, **Descript**, or **Premiere Pro**).')
out.append('2. Use the slide transition markers (`[SLIDE 1]`, `[SLIDE 2]`, etc.) in the audio script to align each slide transition exactly with the voiceover.')
out.append('3. Add subtle background ambient audio (dark synthpad or soft corporate ambient at -24dB).')
out.append('4. Export the final lesson video as a 1080p MP4 file.')
out.append('')
out.append('---')
out.append('')
out.append('## 2. Design System Tokens (Dark Navy Editorial Aesthetics)')
out.append('')
out.append('| Element | Hex Token | CSS / Usage |')
out.append('|---|---|---|')
out.append('| **Canvas Background** | `#070C18` | Deep void space canvas |')
out.append('| **Surface / Card Background** | `#0D172A` | Floating card background with `rgba(255,255,255,0.08)` border |')
out.append('| **Primary Brand Accent** | `#14B8A6` | Teal highlight for core takeaways and active stages |')
out.append('| **Secondary Accent** | `#2DD4BF` | Light teal for badges and icons |')
out.append('| **Evidence / Data Accent** | `#38BDF8` | Sky blue for verified empirical metrics |')
out.append('| **Hazard / Anti-Pattern** | `#F43F5E` | Rose crimson for mistakes and traps |')
out.append('| **Typography** | `Inter` / `Outfit` | Editorial sans-serif, high contrast white `#F8FAFC` and muted `#94A3B8` |')
out.append('')
out.append('---')
out.append('')
out.append('## 3. Complete Curriculum Master Catalog (All 62 Lessons)')
out.append('')

for m in modules:
    meta = m.MODULE_METADATA
    lessons = m.LESSONS_DATA
    out.append(f"### Module {meta['num']}: {meta['name']} ({len(lessons)} Lessons = {len(lessons)*2} Files)")
    out.append(f"Directory: `docs/academy/{meta['dir_name']}/slides-and-audio/`")
    out.append('')
    out.append('| # | Lesson ID | Lesson Title | Gemini Slides Prompt | TTS Audio Script |')
    out.append('|---|---|---|---|---|')
    for l in lessons:
        p = l['file_prefix']
        slide_link = f"[{p}-slides-prompt.md]({meta['dir_name']}/slides-and-audio/{p}-slides-prompt.md)"
        audio_link = f"[{p}-audio-script.md]({meta['dir_name']}/slides-and-audio/{p}-audio-script.md)"
        out.append(f"| {l['order']} | **{l['id']}** | {l['title']} | {slide_link} | {audio_link} |")
    out.append('')

catalog_content = '\n'.join(out)
catalog_path = '/Volumes/SSD/javis-saas/docs/academy/README-slides-and-audio-catalog.md'
with open(catalog_path, 'w', encoding='utf-8') as f:
    f.write(catalog_content)

print(f'Master catalog successfully created at {catalog_path}')
