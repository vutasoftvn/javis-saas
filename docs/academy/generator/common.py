import os

VISUAL_DESIGN_SYSTEM = """### MASTER VISUAL DIRECTIVE & DESIGN SYSTEM (COSA Dark Canvas)
- **Aspect Ratio**: 16:9 Widescreen
- **Color Tokens**:
  - `Background Canvas`: `#070C18` (Deep navy void)
  - `Radial Accent / Ambient Glow`: `#0B1934` (Subtle depth behind central cards)
  - `Surface / Container Fill`: `#0D172A` with subtle outline `1px solid rgba(255, 255, 255, 0.08)`
  - `Primary Highlight`: `#14B8A6` (COSA Teal - Progress, key concepts, actionable levers)
  - `Secondary Signal`: `#38BDF8` (Sky Blue - Evidence, empirical validation, customer data)
  - `Warning / Anti-Pattern`: `#F43F5E` (Rose / Crimson - Assumptions, pitfalls, vanity metrics)
  - `Typography Primary`: `#FFFFFF` (Headers, bold takeaways)
  - `Typography Secondary`: `#E2E8F0` (Body text, data points)
  - `Typography Muted`: `#94A3B8` (Footnotes, captions, supporting labels)
- **Typography**: Modern geometric sans-serif (Inter, Outfit, or SF Pro Display). Clean weights (Bold 700 for titles, Medium 500 for cards, Regular 400 for copy).
- **Layout Philosophy**: Editorial minimalism. High whitespace, strong visual hierarchy, stark contrast.
- **Critical Negative Constraints**:
  - NEVER generate fake, cluttered software dashboards or generic SaaS UI mockups.
  - NEVER use childish cartoons, stock corporate 3D clay figures, or clip art.
  - Maintain crisp card containers, clear directional node diagrams, and high-impact data callouts.
"""

def render_slides_prompt(lesson_id, lesson_slug, title, module_num, module_name, lifecycle_topic, slides_data):
    """
    Renders a comprehensive prompt for Gemini Notebook / NotebookLM to generate presentation slides.
    """
    out = []
    out.append(f"# Gemini Notebook Slide Generation Prompt: Lesson {lesson_id} — {title}")
    out.append(f"> **Module**: {module_num} — {module_name}")
    out.append(f"> **Lifecycle Stage**: `{lifecycle_topic}` | **Lesson Slug**: `{lesson_slug}`")
    out.append(f"> **Output Format**: 16:9 High-Impact Presentation Deck (6 Slides)")
    out.append("")
    out.append("---")
    out.append("")
    out.append("## INSTRUCTIONS FOR GEMINI / NOTEBOOKLM")
    out.append("You are acting as a Principal Venture Architect and World-Class Slide Designer for the **COSA Founder Operating System**.")
    out.append(f"Generate a polished, production-grade 6-slide presentation deck for **Lesson {lesson_id}: {title}**.")
    out.append("Follow the exact design system tokens, layout wireframes, copy structure, and visual prompts provided below.")
    out.append("")
    out.append(VISUAL_DESIGN_SYSTEM)
    out.append("")
    out.append("---")
    out.append("")
    out.append("## SLIDE-BY-SLIDE SPECIFICATIONS")
    out.append("")

    for i, s in enumerate(slides_data, 1):
        out.append(f"### Slide {i}: {s['title']} ({s['type']})")
        out.append(f"- **Visual Archetype**: `{s['archetype']}`")
        out.append(f"- **Layout & Composition**: {s['layout']}")
        out.append(f"- **Header Badge**: `{s['badge']}`")
        out.append(f"- **Main Headline**: **{s['headline']}**")
        out.append(f"- **Sub-headline / Thesis**: {s['subheadline']}")
        out.append("- **Core Slide Content**:")
        for item in s['content_points']:
            out.append(f"  - {item}")
        if s.get('callout'):
            out.append(f"- **Highlight / Accent Box**: {s['callout']}")
        if s.get('visual_element'):
            out.append(f"- **Diagram / Visual Structure**: {s['visual_element']}")
        if s.get('visual_prompt'):
            out.append(f"- **AI Visual Generation Directive**: *{s['visual_prompt']}*")
        else:
            out.append(f"- **AI Visual Generation Directive**: *Editorial slide composition on dark canvas #070C18 with teal #14B8A6 accents, minimalist typography, high contrast.*")
        out.append("")
    
    out.append("---")
    out.append("")
    out.append("## GEMINI NOTEBOOK COPY-PASTE PROMPT EXECUTION")
    out.append("```text")
    out.append(f"Create a 6-slide executive presentation for Lesson {lesson_id}: '{title}' in the COSA dark canvas style (#070C18 canvas, #14B8A6 teal primary accent, #38BDF8 sky blue evidence, #F43F5E risk accent).")
    out.append("Include clean card containers, clear typography, and avoid fake UI clutter. Structure each slide strictly according to the following specifications:")
    for i, s in enumerate(slides_data, 1):
        out.append(f"\n[SLIDE {i} - {s['title'].upper()}]")
        out.append(f"Badge: {s['badge']}")
        out.append(f"Headline: {s['headline']}")
        out.append(f"Key Points:")
        for pt in s['content_points']:
            out.append(f"- {pt}")
        if s.get('callout'):
            out.append(f"Callout: {s['callout']}")
    out.append("```")
    return "\n".join(out)


def render_audio_script(lesson_id, lesson_slug, title, module_num, module_name, lifecycle_topic, slides_narration):
    """
    Renders an audio voiceover script ready for TTS software (ElevenLabs, OpenAI TTS, PlayHT).
    """
    out = []
    out.append(f"# Text-To-Speech (TTS) Narration Script: Lesson {lesson_id} — {title}")
    out.append(f"> **Module**: {module_num} — {module_name}")
    out.append(f"> **Lifecycle Stage**: `{lifecycle_topic}` | **Lesson Slug**: `{lesson_slug}`")
    out.append(f"> **Target Duration**: ~2.5 to 3.0 minutes | **Pacing**: 130 words/minute")
    out.append("")
    out.append("---")
    out.append("")
    out.append("## AUDIO PRODUCTION & TTS CONFIGURATION")
    out.append("- **Recommended Voice Profile**: Mature Male / Female Founder Mentor (Calm, authoritative, deliberate, grounded, neutral international accent).")
    out.append("- **Suggested Engines & Presets**:")
    out.append("  - **ElevenLabs**: 'Adam' or 'Brian' or 'Rachel' (Stability: `0.65`, Clarity / Similarity: `0.85`, Style Exaggeration: `0.10`).")
    out.append("  - **OpenAI TTS**: Voice `onyx` (deep, authoritative) or `alloy` (neutral, crisp), speed `1.0x`.")
    out.append("- **Narration Markup Guide**:")
    out.append("  - `[pause X.Xs]`: Dedicated silence pause to allow visual intake on the slide.")
    out.append("  - `**Word**`: Gentle vocal emphasis and stress.")
    out.append("  - `[tone: ...]`: Direction for tone and inflection.")
    out.append("")
    out.append("---")
    out.append("")
    out.append("## SLIDE-SYNCHRONIZED AUDIO SCRIPT")
    out.append("")

    full_continuous_script = []

    for i, s in enumerate(slides_narration, 1):
        out.append(f"### [SLIDE {i} AUDIO] — {s['slide_title']} ({s['duration_est']})")
        out.append(f"**Slide Reference**: Slide {i} ({s['visual_cue']})")
        out.append(f"**Tone**: *{s['tone']}*")
        out.append("")
        out.append("> **Spoken Script**:")
        out.append(">")
        for para in s['script_paragraphs']:
            out.append(f"> \"{para}\"")
            out.append(">")
        out.append("")
        for para in s['script_paragraphs']:
            full_continuous_script.append(para)

    out.append("---")
    out.append("")
    out.append("## CONTINUOUS RAW SCRIPT (FOR ONE-TAKE TTS BATCH GENERATION)")
    out.append("```text")
    out.append("\n\n".join(full_continuous_script))
    out.append("```")
    return "\n".join(out)
