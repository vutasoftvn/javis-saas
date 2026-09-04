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


VISUAL_DESIGN_SYSTEM_VI = """### HỆ THỐNG THIẾT KẾ & CHỈ DẪN HÌNH ẢNH CHUẨN (COSA Dark Canvas)
- **Tỉ lệ khung hình**: 16:9 Widescreen
- **Bảng mã màu (Color Tokens)**:
  - `Màu nền Canvas`: `#070C18` (Không gian đen huyền vũ trụ sâu thẳm)
  - `Ánh sáng tỏa / Ambient Glow`: `#0B1934` (Độ sâu tinh tế phía sau các thẻ trung tâm)
  - `Bề mặt chứa nội dung / Card Surface`: `#0D172A` với viền mờ `1px solid rgba(255, 255, 255, 0.08)`
  - `Điểm nhấn thương hiệu chính`: `#14B8A6` (Màu Teal COSA - Tiến trình, khái niệm cốt lõi, đòn bẩy hành động)
  - `Tín hiệu dữ liệu / Bằng chứng`: `#38BDF8` (Xanh da trời - Dữ liệu thực nghiệm, phản hồi khách hàng)
  - `Cảnh báo / Bẫy sai lầm`: `#F43F5E` (Đỏ hồng - Giả định nguy hiểm, cạm bẫy, chỉ số ảo)
  - `Màu chữ chính`: `#FFFFFF` (Tiêu đề, thông điệp cốt lõi in đậm)
  - `Màu chữ phụ`: `#E2E8F0` (Nội dung diễn giải, các điểm dữ liệu)
  - `Màu chữ chú thích`: `#94A3B8` (Ghi chú chân trang, nhãn phụ trợ)
- **Kiểu chữ**: Sans-serif hình học hiện đại (Inter, Outfit, hoặc SF Pro Display). Độ đậm rõ ràng (Bold 700 cho tiêu đề, Medium 500 cho thẻ, Regular 400 cho nội dung).
- **Triết lý bố cục**: Tối giản biên tập (Editorial minimalism). Nhiều khoảng trắng (whitespace), phân cấp thị giác mạnh mẽ, độ tương phản sắc nét.
- **Quy tắc giới hạn quan trọng**:
  - TUYỆT ĐỐI KHÔNG vẽ các bảng điều khiển phần mềm giả tạo, lộn xộn hoặc mockup giao diện SaaS đại trà.
  - TUYỆT ĐỐI KHÔNG dùng hình hoạt hình trẻ con, nhân vật 3D đất sét công sở khuôn mẫu hoặc clipart rẻ tiền.
  - Luôn duy trì khung thẻ sắc sảo, sơ đồ luồng định hướng rõ ràng và các khối số liệu tác động cao.
"""

def render_slides_prompt_vi(lesson_id, lesson_slug, title, module_num, module_name, lifecycle_topic, slides_data):
    """
    Tạo prompt tiếng Việt chuẩn hóa cho Gemini Notebook / NotebookLM để sinh bộ slide thuyết trình 6 trang.
    """
    out = []
    out.append(f"# Lời Nhắc Tạo Slide Gemini Notebook: Bài học {lesson_id} — {title}")
    out.append(f"> **Module**: {module_num} — {module_name}")
    out.append(f"> **Giai đoạn Vòng đời**: `{lifecycle_topic}` | **Mã bài học**: `{lesson_slug}`")
    out.append(f"> **Định dạng đầu ra**: Bản thuyết trình 16:9 Độ Tác Động Cao (6 Slides)")
    out.append("")
    out.append("---")
    out.append("")
    out.append("## HƯỚNG DẪN DÀNH CHO GEMINI / NOTEBOOKLM")
    out.append("Bạn đang đóng vai trò là Kiến trúc sư Khởi nghiệp Cấp cao (Principal Venture Architect) và Chuyên gia Thiết kế Slide Đẳng cấp Thế giới cho **Hệ điều hành Nhà sáng lập COSA**.")
    out.append(f"Hãy tạo một bộ slide thuyết trình 6 trang chuyên nghiệp, sẵn sàng sản xuất cho **Bài học {lesson_id}: {title}**.")
    out.append("Tuân thủ chính xác các mã thiết kế, khung bố cục, cấu trúc nội dung và chỉ dẫn hình ảnh bên dưới.")
    out.append("")
    out.append(VISUAL_DESIGN_SYSTEM_VI)
    out.append("")
    out.append("---")
    out.append("")
    out.append("## QUY CÁCH CHI TIẾT TỪNG TRANG SLIDE")
    out.append("")

    for i, s in enumerate(slides_data, 1):
        out.append(f"### Slide {i}: {s['title']} ({s['type']})")
        out.append(f"- **Visual Archetype**: `{s['archetype']}`")
        out.append(f"- **Bố cục & Cấu trúc Trình bày**: {s['layout']}")
        out.append(f"- **Huy hiệu Đầu trang (Badge)**: `{s['badge']}`")
        out.append(f"- **Tiêu đề Chính (Main Headline)**: **{s['headline']}**")
        out.append(f"- **Tiêu đề Phụ / Luận điểm cốt lõi**: {s['subheadline']}")
        out.append("- **Nội dung Trọng tâm Slide**:")
        for item in s['content_points']:
            out.append(f"  - {item}")
        if s.get('callout'):
            out.append(f"- **Hộp Điểm nhấn / Đòn bẩy Hành động**: {s['callout']}")
        if s.get('visual_element'):
            out.append(f"- **Sơ đồ / Cấu trúc Trực quan**: {s['visual_element']}")
        if s.get('visual_prompt'):
            out.append(f"- **Chỉ dẫn Tạo Ảnh AI**: *{s['visual_prompt']}*")
        else:
            out.append(f"- **Chỉ dẫn Tạo Ảnh AI**: *Bố cục slide biên tập tối giản trên nền đen tối sâu #070C18 với điểm nhấn màu teal #14B8A6, kiểu chữ hiện đại, tương phản sắc nét.*")
        out.append("")
    
    out.append("---")
    out.append("")
    out.append("## LỆNH SAO CHÉP THỰC THI NHANH TRÊN GEMINI NOTEBOOK (COPY-PASTE PROMPT)")
    out.append("```text")
    out.append(f"Tạo bản thuyết trình 6 slide cấp điều hành cho Bài học {lesson_id}: '{title}' theo phong cách COSA Dark Canvas (nền #070C18, điểm nhấn teal #14B8A6, xanh da trời chứng cứ #38BDF8, rủi ro #F43F5E).")
    out.append("Sử dụng các khối thẻ sắc nét, kiểu chữ tinh gọn, không đưa vào giao diện UI giả lập lộn xộn. Cấu trúc từng slide chuẩn xác theo các thông số sau:")
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


def render_audio_script_vi(lesson_id, lesson_slug, title, module_num, module_name, lifecycle_topic, slides_narration):
    """
    Tạo kịch bản lồng tiếng TTS tiếng Việt chất lượng cao cho ElevenLabs, OpenAI TTS, FPT.AI, Zalo AI.
    """
    out = []
    out.append(f"# Kịch Bản Lồng Tiếng Text-To-Speech (TTS): Bài học {lesson_id} — {title}")
    out.append(f"> **Module**: {module_num} — {module_name}")
    out.append(f"> **Giai đoạn Vòng đời**: `{lifecycle_topic}` | **Mã bài học**: `{lesson_slug}`")
    out.append(f"> **Thời lượng mục tiêu**: ~2.5 đến 3.0 phút | **Tốc độ đọc**: 120-130 từ/phút")
    out.append("")
    out.append("---")
    out.append("")
    out.append("## CẤU HÌNH SẢN XUẤT ÂM THANH & TTS")
    out.append("- **Hồ sơ Giọng đọc đề xuất**: Giọng Cố vấn Sáng lập Trưởng thành Nam / Nữ (Điềm đạm, uy lực, đĩnh đạc, thực chiến, truyền cảm, phát âm chuẩn).")
    out.append("- **Engine & Preset gợi ý**:")
    out.append("  - **ElevenLabs**: Mô hình `eleven_multilingual_v2` với giọng 'Adam' hoặc 'Brian' hoặc 'Rachel' (Stability: `0.65`, Clarity / Similarity: `0.85`, Style Exaggeration: `0.10`).")
    out.append("  - **OpenAI TTS**: Voice `onyx` (nam trầm ấm, uy quyền) hoặc `alloy` (trung tính, sáng rõ), speed `1.0x`.")
    out.append("  - **TTS Tiếng Việt chuyên dụng**: FPT.AI (Ban Mai / Minh Quang), Viettel AI, Zalo AI với tốc độ chuẩn 1.0x.")
    out.append("- **Hướng dẫn ký hiệu kịch bản**:")
    out.append("  - `[pause X.Xs]`: Khoảng lặng ngắt nghỉ để người xem kịp quan sát và tiếp thu nội dung trên slide.")
    out.append("  - `**Từ khóa**`: Nhấn giọng nhẹ nhàng vào từ khóa quan trọng.")
    out.append("  - `[tone: ...]`: Hướng dẫn sắc thái cảm xúc và ngữ điệu câu nói.")
    out.append("")
    out.append("---")
    out.append("")
    out.append("## KỊCH BẢN ÂM THANH ĐỒNG BỘ THEO SLIDE")
    out.append("")

    full_continuous_script = []

    for i, s in enumerate(slides_narration, 1):
        out.append(f"### [SLIDE {i} AUDIO] — {s['slide_title']} ({s['duration_est']})")
        out.append(f"**Slide Tham chiếu**: Slide {i} ({s['visual_cue']})")
        out.append(f"**Sắc thái giọng đọc (Tone)**: *{s['tone']}*")
        out.append("")
        out.append("> **Lời thoại**:")
        out.append(">")
        for para in s['script_paragraphs']:
            out.append(f"> \"{para}\"")
            out.append(">")
        out.append("")
        for para in s['script_paragraphs']:
            full_continuous_script.append(para)

    out.append("---")
    out.append("")
    out.append("## KỊCH BẢN ĐỌC LIỀN MẠCH (DÀNH CHO BATCH TTS 1-CLICK)")
    out.append("```text")
    out.append("\n\n".join(full_continuous_script))
    out.append("```")
    return "\n".join(out)

