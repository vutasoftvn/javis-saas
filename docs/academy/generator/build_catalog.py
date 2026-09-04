import sys, os

sys.path.insert(0, '/Volumes/SSD/javis-saas/docs/academy/generator')
import module_00, module_01, module_02, module_03, module_04, module_05, module_06

modules = [
    module_00, module_01, module_02, module_03, module_04, module_05, module_06
]

MODULE_NAMES_VI = {
    "00": "Nền Tảng Cho Nhà Sáng Lập: Từ Ý Tưởng Đến Nhịp Điệu Vận Hành",
    "01": "Khám Phá Vấn Đề và Thấu Cảm Khách Hàng",
    "02": "Thiết Kế Giải Pháp và Kiểm Chứng Sớm",
    "03": "Mô Hình Kinh Doanh và Kiểm Chứng Khả Năng Thu Tiền",
    "04": "Triển Khai Thử Nghiệm (Pilot) và Thực Thi Ra Mắt Thị Trường (GTM)",
    "05": "Độ Phù Hợp Sản Phẩm - Thị Trường (PMF) và Tăng Trưởng Giai Đoạn Đầu",
    "06": "Mở Rộng Quy Mô, Vận Hành và Quản Trị Doanh Nghiệp"
}

out = []
out.append('# COSA Academy: Complete Slide & Audio Production Master Catalog (Song Ngữ EN / VI)')
out.append('')
out.append('> **Comprehensive Production Assets for all 7 Modules and 62 Lessons (248 Production Files: 124 EN + 124 VI)**')
out.append('')
out.append('Mỗi bài học trong chương trình vòng đời khởi nghiệp COSA Academy được cung cấp đầy đủ **4 file sản xuất chuyên nghiệp**:')
out.append('1. **`{prefix}-slides-prompt.md`**: Prompt Tiếng Anh chuẩn cho **Gemini Notebook (NotebookLM / Gemini Pro)** để sinh bộ slide 16:9 6 trang theo COSA Dark Theme.')
out.append('2. **`{prefix}-slides-prompt-vi.md`**: Prompt Tiếng Việt chuẩn hóa cho **Gemini Notebook** với hệ thống thuật ngữ Venture Architect đã được tinh chỉnh sắc sảo.')
out.append('3. **`{prefix}-audio-script.md`**: Kịch bản lồng tiếng TTS Tiếng Anh với đánh dấu ngắt nghỉ `[pause 0.5s]`, voice profile người sáng lập và khối văn bản đọc liền mạch 1-click.')
out.append('4. **`{prefix}-audio-script-vi.md`**: Kịch bản lồng tiếng TTS Tiếng Việt chuẩn hóa tối ưu cho ElevenLabs Multilingual v2, OpenAI TTS (`onyx`, `alloy`), FPT.AI, Zalo AI.')
out.append('')
out.append('---')
out.append('')
out.append('## 1. Production Workflow: From Text to Published Video')
out.append('')
out.append('```mermaid')
out.append('flowchart LR')
out.append('    A["Prompt File<br/>(slides-prompt.md / -vi.md)"] -->|Copy Prompt| B["Gemini Notebook / NotebookLM<br/>(Generate Deck)"]')
out.append('    B --> C["Slide Deck Export<br/>(PNG / PDF / 16:9)"]')
out.append('    D["Script File<br/>(audio-script.md / -vi.md)"] -->|Paste Script| E["TTS Engine<br/>(ElevenLabs / OpenAI / FPT.AI)"]')
out.append('    E --> F["Audio Narration<br/>(WAV / MP3)"]')
out.append('    C --> G["Video Assembly<br/>(CapCut / Premiere / Descript)"]')
out.append('    F --> G')
out.append('    G --> H["Published Lesson Video<br/>(1080p MP4 / YouTube / LMS)"]')
out.append('```')
out.append('')
out.append('### Step A: Generating Slides via Gemini Notebook (Tạo Slides)')
out.append('1. Mở **Gemini Notebook (NotebookLM)** hoặc **Gemini 1.5 Pro**.')
out.append('2. Mở file `{prefix}-slides-prompt.md` (nếu làm bản tiếng Anh) hoặc `{prefix}-slides-prompt-vi.md` (nếu làm bản tiếng Việt).')
out.append('3. Cuộn xuống mục **Master Execution Prompt Block** (ở cuối file) và sao chép toàn bộ khối lệnh.')
out.append('4. Dán vào Gemini Notebook.')
out.append('5. Gemini sẽ sinh ra bộ 6 slide thuyết trình chuẩn xác theo đúng cấu trúc, mã màu và hình ảnh minh họa.')
out.append('')
out.append('### Step B: Generating Voiceover via TTS Software (Tạo Âm thanh Giọng đọc)')
out.append('1. Mở công cụ TTS lựa chọn:')
out.append('   - **Bản Tiếng Anh**: **ElevenLabs** (giọng: *Adam*, *George*, hoặc *Brian*) hoặc **OpenAI TTS** (giọng: *Onyx* hoặc *Echo*), tốc độ ~130 WPM.')
out.append('   - **Bản Tiếng Việt**: **ElevenLabs Multilingual v2** (giọng: *Adam*, *Brian*, *Rachel*) hoặc **OpenAI TTS** (giọng: *onyx*, *alloy*), hoặc **FPT.AI** (giọng *Ban Mai*, *Minh Quang*), tốc độ ~120–130 từ/phút.')
out.append('2. Mở file `{prefix}-audio-script.md` hoặc `{prefix}-audio-script-vi.md`.')
out.append('3. Sao chép khối **Continuous Raw Script** ở cuối file để sinh audio toàn bài chỉ với 1 click.')
out.append('4. Xuất file âm thanh chất lượng cao (`.wav` hoặc `.mp3`).')
out.append('')
out.append('### Step C: Assembling the Lesson Video (Ghép Video Hoàn chỉnh)')
out.append('1. Nhập ảnh slide đã xuất (16:9 1920x1080) và track audio vào phần mềm dựng (**CapCut**, **Descript**, hoặc **Premiere Pro**).')
out.append('2. Sử dụng các điểm mốc đánh dấu `[SLIDE 1]`, `[SLIDE 2]`, ... trong file kịch bản audio để căn chỉnh thời điểm chuyển slide khớp từng giây với lời thoại.')
out.append('3. Thêm nhạc nền nhẹ nhàng (ambient synthpad hoặc corporate chill ở mức -24dB).')
out.append('4. Xuất video bài học hoàn thiện chuẩn 1080p MP4.')
out.append('')
out.append('---')
out.append('')
out.append('## 2. Design System Tokens (Dark Navy Editorial Aesthetics)')
out.append('')
out.append('| Element | Hex Token | CSS / Usage | Ý nghĩa thiết kế |')
out.append('|---|---|---|---|')
out.append('| **Canvas Background** | `#070C18` | Deep void space canvas | Không gian nền đen vũ trụ sâu thẳm |')
out.append('| **Surface / Card Background** | `#0D172A` | Floating card background with `rgba(255,255,255,0.08)` border | Thẻ chứa nội dung nổi với viền mờ |')
out.append('| **Primary Brand Accent** | `#14B8A6` | Teal highlight for core takeaways and active stages | Màu xanh ngọc Teal COSA - Tiến trình & Hành động |')
out.append('| **Secondary Accent** | `#2DD4BF` | Light teal for badges and icons | Điểm nhấn phụ cho huy hiệu và biểu tượng |')
out.append('| **Evidence / Data Accent** | `#38BDF8` | Sky blue for verified empirical metrics | Xanh da trời cho dữ liệu và bằng chứng khách hàng |')
out.append('| **Hazard / Anti-Pattern** | `#F43F5E` | Rose crimson for mistakes and traps | Đỏ hồng cho cạm bẫy, rủi ro và chỉ số ảo |')
out.append('| **Typography** | `Inter` / `Outfit` | Editorial sans-serif, high contrast white `#F8FAFC` and muted `#94A3B8` | Kiểu chữ sans-serif hiện đại, độ tương phản cao |')
out.append('')
out.append('---')
out.append('')
out.append('## 3. Complete Curriculum Master Catalog (All 62 Lessons — Song Ngữ EN & VI)')
out.append('')

for m in modules:
    meta = m.MODULE_METADATA
    mod_num = meta['num']
    mod_name_vi = MODULE_NAMES_VI.get(mod_num, meta['name'])
    lessons = m.LESSONS_DATA
    out.append(f"### Module {mod_num}: {meta['name']}")
    out.append(f"**Tên Tiếng Việt**: *{mod_name_vi}* ({len(lessons)} bài học = {len(lessons)*4} files: 2 EN + 2 VI mỗi bài)")
    out.append(f"Thư mục: `docs/academy/{meta['dir_name']}/slides-and-audio/`")
    out.append('')
    out.append('| # | ID | Lesson Title | Slide Prompts (EN / VI) | Audio Scripts (EN / VI) |')
    out.append('|:---:|:---:|---|---|---|')
    for l in lessons:
        p = l['file_prefix']
        dir_name = meta['dir_name']
        s_en = f"[EN Slide]({dir_name}/slides-and-audio/{p}-slides-prompt.md)"
        s_vi = f"[VI Slide]({dir_name}/slides-and-audio/{p}-slides-prompt-vi.md)"
        a_en = f"[EN Audio]({dir_name}/slides-and-audio/{p}-audio-script.md)"
        a_vi = f"[VI Audio]({dir_name}/slides-and-audio/{p}-audio-script-vi.md)"
        out.append(f"| {l['order']} | **{l['id']}** | {l['title']} | {s_en} · {s_vi} | {a_en} · {a_vi} |")
    out.append('')

catalog_content = '\n'.join(out)
catalog_path = '/Volumes/SSD/javis-saas/docs/academy/README-slides-and-audio-catalog.md'
with open(catalog_path, 'w', encoding='utf-8') as f:
    f.write(catalog_content)

print(f'Master catalog successfully updated at {catalog_path}')
