import sys, os, json, time, re, urllib.request, urllib.parse

sys.path.insert(0, '/Volumes/SSD/javis-saas/docs/academy/generator')
import common
import module_00, module_01, module_02, module_03, module_04, module_05, module_06

CACHE_FILE = '/Volumes/SSD/javis-saas/docs/academy/generator/translations_cache.json'

MODULE_NAMES_VI = {
    "00": "Nền Tảng Cho Nhà Sáng Lập: Từ Ý Tưởng Đến Nhịp Điệu Vận Hành",
    "01": "Khám Phá Vấn Đề và Thấu Cảm Khách Hàng",
    "02": "Thiết Kế Giải Pháp và Kiểm Chứng Sớm",
    "03": "Mô Hình Kinh Doanh và Kiểm Chứng Khả Năng Thu Tiền",
    "04": "Triển Khai Thử Nghiệm (Pilot) và Thực Thi Ra Mắt Thị Trường (GTM)",
    "05": "Độ Phù Hợp Sản Phẩm - Thị Trường (PMF) và Tăng Trưởng Giai Đoạn Đầu",
    "06": "Mở Rộng Quy Mô, Vận Hành và Quản Trị Doanh Nghiệp"
}

# Domain-specific glossary regex substitutions to enforce venture architecture terminology
GLOSSARY_REPLACEMENTS = [
    # Pauses and markup
    (r'\[(?:tạm dừng|ngừng|dừng)\s+([0-9,.]+)\s*(?:giây|s)\]', lambda m: f"[pause {m.group(1).replace(',', '.')}s]"),
    (r'\[pause\s+([0-9,.]+)\s*giây\]', lambda m: f"[pause {m.group(1).replace(',', '.')}s]"),
    (r'\[tông màu:\s*([^\]]+)\]', lambda m: f"[tone: {m.group(1)}]"),
    
    # Core COSA Terminology
    (r'(?i)\bhọc viện cosa\b', 'COSA Academy'),
    (r'(?i)\bhệ điều hành của người sáng lập\b', 'Hệ điều hành cho Nhà sáng lập'),
    (r'(?i)\bhệ điều hành người sáng lập\b', 'Hệ điều hành cho Nhà sáng lập'),
    (r'(?i)\bngười sáng lập\b', 'nhà sáng lập'),
    (r'(?i)\bNgười sáng lập\b', 'Nhà sáng lập'),
    (r'(?i)\bvòng điều hành liên doanh\b', 'vòng lặp vận hành khởi nghiệp'),
    (r'(?i)\bvòng lặp điều hành liên doanh\b', 'vòng lặp vận hành khởi nghiệp'),
    (r'(?i)\bvòng lặp vận hành liên doanh\b', 'vòng lặp vận hành khởi nghiệp'),
    (r'(?i)\bđặt cược liên doanh\b', 'dự án đặt cược khởi nghiệp'),
    (r'(?i)\bĐặt cược liên doanh\b', 'Dự án đặt cược khởi nghiệp'),
    (r'(?i)\bđặt cược dự án\b', 'Dự án Đặt cược (Project Bet)'),
    (r'(?i)\bĐặt cược dự án\b', 'Dự án Đặt cược (Project Bet)'),
    (r'(?i)\bdự án cược\b', 'Dự án Đặt cược'),
    (r'(?i)\bDự án cược\b', 'Dự án Đặt cược'),
    (r'(?i)\bnhiệt độ hàng tuần\b', 'nhịp điệu hàng tuần'),
    (r'(?i)\bnhiệt độ tuần\b', 'nhịp điệu tuần'),
    (r'(?i)\bnhịp độ hàng tuần\b', 'nhịp điệu hàng tuần'),
    (r'(?i)\bnhịp độ tuần\b', 'nhịp điệu tuần'),
    (r'(?i)\bxem xét bằng chứng\b', 'Đánh giá Bằng chứng'),
    (r'(?i)\bXem xét bằng chứng\b', 'Đánh giá Bằng chứng'),
    (r'(?i)\bđánh giá hồi tưởng\b', 'buổi hồi tưởng (Retrospective)'),
    (r'(?i)\bkho tiền\b', 'kho lưu trữ Vault'),
    (r'(?i)\bKho tiền\b', 'Kho Lưu trữ Vault'),
    (r'(?i)\bkho lưu trữ kho tiền\b', 'kho lưu trữ Vault'),
    (r'(?i)\bKho lưu trữ kho tiền\b', 'Kho Lưu trữ Vault'),
    (r'(?i)\bchỉ số phù phiếm\b', 'chỉ số ảo (Vanity Metrics)'),
    (r'(?i)\bChỉ số phù phiếm\b', 'Chỉ số ảo (Vanity Metrics)'),
    (r'(?i)\bsố liệu phù phiếm\b', 'chỉ số ảo (Vanity Metrics)'),
    (r'(?i)\bSố liệu phù phiếm\b', 'Chỉ số ảo (Vanity Metrics)'),
    (r'(?i)\bchỉ số phù phiếm\b', 'chỉ số ảo (Vanity Metrics)'),
    (r'(?i)\bsự phù hợp của thị trường sản phẩm\b', 'Độ Phù hợp Sản phẩm - Thị trường (PMF)'),
    (r'(?i)\bsự phù hợp giữa sản phẩm và thị trường\b', 'Độ Phù hợp Sản phẩm - Thị trường (PMF)'),
    (r'(?i)\bphù hợp sản phẩm - thị trường\b', 'Độ Phù hợp Sản phẩm - Thị trường (PMF)'),
    (r'(?i)\bphù hợp giữa sản phẩm và thị trường\b', 'Độ Phù hợp Sản phẩm - Thị trường (PMF)'),
    (r'(?i)\bđộ phù hợp của thị trường sản phẩm\b', 'Độ Phù hợp Sản phẩm - Thị trường (PMF)'),
    (r'(?i)\bsự phù hợp của giải pháp sản phẩm\b', 'Độ Phù hợp Sản phẩm - Giải pháp (Solution Fit)'),
    (r'(?i)\bđộ phù hợp của giải pháp sản phẩm\b', 'Độ Phù hợp Sản phẩm - Giải pháp (Solution Fit)'),
    (r'(?i)\bviệc cần hoàn thành\b', 'Jobs to Be Done (JTBD)'),
    (r'(?i)\bViệc cần hoàn thành\b', 'Jobs to Be Done (JTBD)'),
    (r'(?i)\bcông ty một người\b', 'Công ty Một Người (One-Person Company)'),
    (r'(?i)\bCông ty một người\b', 'Công ty Một Người'),
    (r'(?i)\bkỳ lân một người\b', 'Kỳ lân Một Người (One-Person Unicorn)'),
    (r'(?i)\bKỳ lân một người\b', 'Kỳ lân Một Người'),
    (r'(?i)\bthị trường đầu cầu\b', 'thị trường ngách bàn đạp (Beachhead Market)'),
    (r'(?i)\bThị trường đầu cầu\b', 'Thị trường ngách bàn đạp (Beachhead Market)'),
    (r'(?i)\bsự sẵn sàng chi trả\b', 'sự sẵn sàng chi trả (Willingness to Pay)'),
    (r'(?i)\bSự sẵn sàng chi trả\b', 'Sự sẵn sàng chi trả (Willingness to Pay)'),
    (r'(?i)\bkinh tế đơn vị\b', 'hiệu quả kinh tế đơn vị (Unit Economics)'),
    (r'(?i)\bKinh tế đơn vị\b', 'Hiệu quả kinh tế đơn vị (Unit Economics)'),
    (r'(?i)\bhồ sơ nhà sáng lập\b', 'Hồ sơ Nhà sáng lập'),
    (r'(?i)\bHồ sơ người sáng lập\b', 'Hồ sơ Nhà sáng lập'),
    (r'(?i)\bgiả thuyết thương mại\b', 'giả thuyết thương mại'),
    (r'(?i)\bsách bán hàng\b', 'cẩm nang bán hàng (Sales Playbook)'),
    (r'(?i)\bSách bán hàng\b', 'Cẩm nang bán hàng (Sales Playbook)'),
    (r'(?i)\bsổ chơi bán hàng\b', 'cẩm nang bán hàng (Sales Playbook)'),
    (r'(?i)\bhợp đồng số liệu\b', 'khế ước chỉ số đo lường (Metric Contract)'),
    (r'(?i)\bHợp đồng số liệu\b', 'Khế ước chỉ số đo lường (Metric Contract)'),
    (r'(?i)\bphòng dữ liệu\b', 'phòng dữ liệu nhà đầu tư (Data Room)'),
    (r'(?i)\bPhòng dữ liệu\b', 'Phòng dữ liệu nhà đầu tư (Data Room)'),
    (r'(?i)\bnăm 12 tuần\b', 'Chu kỳ Năm 12 Tuần (12-Week Year)'),
    (r'(?i)\bNăm 12 tuần\b', 'Chu kỳ Năm 12 Tuần (12-Week Year)'),
    (r'(?i)\bsản phẩm khả thi tối thiểu\b', 'Sản phẩm Khả dụng Tối thiểu (MVP)'),
    (r'(?i)\bSản phẩm khả thi tối thiểu\b', 'Sản phẩm Khả dụng Tối thiểu (MVP)'),
    (r'(?i)\bsản phẩm khả dụng tối thiểu\b', 'Sản phẩm Khả dụng Tối thiểu (MVP)'),
    (r'(?i)\bSản phẩm khả dụng tối thiểu\b', 'Sản phẩm Khả dụng Tối thiểu (MVP)'),
    (r'(?i)\bTrình bày anh hùng\b', 'Slide Thuyết Trình Chủ Đạo (Hero Presentation)'),
    (r'(?i)\bBố cục anh hùng\b', 'Bố cục Chủ đạo (Hero Layout)'),
    (r'(?i)\bmàu xanh mòng két\b', 'màu xanh ngọc teal (#14B8A6)'),
    (r'(?i)\bxanh mòng két\b', 'xanh ngọc teal'),
    (r'(?i)\bnhịp hoạt động\b', 'nhịp điệu vận hành'),
    (r'(?i)\bcược mạo hiểm\b', 'dự án đặt cược khởi nghiệp'),
    (r'(?i)\bHệ điều hành sáng lập của bạn\b', 'Hệ điều hành cho Nhà sáng lập'),
    (r'(?i)\bhệ điều hành sáng lập\b', 'Hệ điều hành cho Nhà sáng lập'),
    (r'(?i)\blàm chuyển động kim chỉ nam\b', 'thực sự tạo ra đột phá'),
    (r'(?i)\bbảng điều khiển tổng hợp\b', 'các bảng số liệu ảo'),
    (r'(?i)\btiếng ồn thay vì động lực mạo hiểm\b', 'sự hỗn loạn thay vì tạo đà bứt phá'),
    (r'(?i)\bvận tốc giả\b', 'tốc độ ảo'),
    (r'(?i)\bngăn xếp công cụ\b', 'hệ thống công cụ'),
    (r'(?i)\bgạch bỏ 20 nhiệm vụ bị ngắt kết nối\b', 'đánh dấu hoàn thành 20 đầu việc rời rạc'),
    (r'(?i)\bngười cố vấn sáng lập ấm áp\b', 'Cố vấn sáng lập ấm áp'),
    (r'(?i)\bcó thẩm quyền\b', 'uy lực và đĩnh đạc')
]

def apply_glossary(text):
    if not text:
        return text
    res = text
    for pattern, repl in GLOSSARY_REPLACEMENTS:
        if callable(repl):
            res = re.sub(pattern, repl, res)
        else:
            res = re.sub(pattern, repl, res)
    return res

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_cache(cache):
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def translate_batch(texts, cache):
    to_fetch = []
    indices = []
    results = [None] * len(texts)
    
    for i, t in enumerate(texts):
        if not t or not t.strip():
            results[i] = t
        elif t in cache:
            results[i] = cache[t]
        else:
            to_fetch.append(t)
            indices.append(i)
            
    if not to_fetch:
        return [apply_glossary(r) for r in results]
        
    chunk_size = 15
    for c in range(0, len(to_fetch), chunk_size):
        chunk = to_fetch[c:c+chunk_size]
        chunk_idx = indices[c:c+chunk_size]
        delimiter = ' ||| '
        joined = delimiter.join(chunk)
        url = 'https://clients5.google.com/translate_a/t?client=dict-chrome-ex&sl=en&tl=vi&q=' + urllib.parse.quote(joined)
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'})
        
        success = False
        try:
            with urllib.request.urlopen(req, timeout=12) as res:
                data = json.loads(res.read().decode('utf-8'))
                trans_joined = data[0]
                parts = trans_joined.split('|||')
                if len(parts) == len(chunk):
                    for p_idx, part in enumerate(parts):
                        orig = chunk[p_idx]
                        cleaned = part.strip()
                        cache[orig] = cleaned
                        results[chunk_idx[p_idx]] = cleaned
                    success = True
        except Exception as e:
            print(f"  [Warning] Batch request failed: {e}, falling back to single items...")
            
        if not success:
            for p_idx, orig in enumerate(chunk):
                u = 'https://clients5.google.com/translate_a/t?client=dict-chrome-ex&sl=en&tl=vi&q=' + urllib.parse.quote(orig)
                r = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'})
                try:
                    with urllib.request.urlopen(r, timeout=10) as single_res:
                        s_data = json.loads(single_res.read().decode('utf-8'))
                        cleaned = s_data[0].strip()
                        cache[orig] = cleaned
                        results[chunk_idx[p_idx]] = cleaned
                except Exception as ex:
                    print(f"  [Error] Single request failed for '{orig[:30]}...': {ex}")
                    results[chunk_idx[p_idx]] = orig  # Keep original on total failure
                time.sleep(0.15)
                
        time.sleep(0.2)
        
    return [apply_glossary(r) for r in results]


def process_lesson(lesson, module_meta, cache):
    # Collect all strings to translate
    texts_to_trans = [lesson['title']]
    
    for s in lesson['slides']:
        texts_to_trans.append(s['title'])
        texts_to_trans.append(s['type'])
        texts_to_trans.append(s['layout'])
        texts_to_trans.append(s['badge'])
        texts_to_trans.append(s['headline'])
        texts_to_trans.append(s['subheadline'])
        for pt in s['content_points']:
            texts_to_trans.append(pt)
        texts_to_trans.append(s.get('callout', ''))
        texts_to_trans.append(s.get('visual_element', ''))
        texts_to_trans.append(s.get('visual_prompt', ''))
        
    for n in lesson['narration']:
        texts_to_trans.append(n['slide_title'])
        texts_to_trans.append(n['visual_cue'])
        texts_to_trans.append(n['tone'])
        for p in n['script_paragraphs']:
            texts_to_trans.append(p)
            
    # Translate all in batch
    trans_results = translate_batch(texts_to_trans, cache)
    
    idx = 0
    title_vi = trans_results[idx]; idx += 1
    
    slides_vi = []
    for s in lesson['slides']:
        s_title = trans_results[idx]; idx += 1
        s_type = trans_results[idx]; idx += 1
        s_layout = trans_results[idx]; idx += 1
        s_badge = trans_results[idx]; idx += 1
        s_headline = trans_results[idx]; idx += 1
        s_subheadline = trans_results[idx]; idx += 1
        s_content = []
        for _ in s['content_points']:
            s_content.append(trans_results[idx]); idx += 1
        s_callout = trans_results[idx]; idx += 1
        s_visual_element = trans_results[idx]; idx += 1
        s_visual_prompt = trans_results[idx]; idx += 1
        
        slides_vi.append({
            "title": s_title,
            "type": s_type,
            "archetype": s['archetype'],  # Keep technical archetype ID
            "layout": s_layout,
            "badge": s_badge,
            "headline": s_headline,
            "subheadline": s_subheadline,
            "content_points": s_content,
            "callout": s_callout if s_callout else None,
            "visual_element": s_visual_element if s_visual_element else None,
            "visual_prompt": s_visual_prompt if s_visual_prompt else None
        })
        
    narration_vi = []
    for n in lesson['narration']:
        n_slide_title = trans_results[idx]; idx += 1
        n_visual_cue = trans_results[idx]; idx += 1
        n_tone = trans_results[idx]; idx += 1
        n_paras = []
        for _ in n['script_paragraphs']:
            n_paras.append(trans_results[idx]); idx += 1
            
        narration_vi.append({
            "slide_title": n_slide_title,
            "duration_est": n['duration_est'],
            "visual_cue": n_visual_cue,
            "tone": n_tone,
            "script_paragraphs": n_paras
        })
        
    return title_vi, slides_vi, narration_vi


def run():
    print("=== STARTING BILINGUAL VIETNAMESE GENERATION FOR COSA ACADEMY ===")
    cache = load_cache()
    print(f"Loaded cache with {len(cache)} existing translated strings.")
    
    modules = [
        module_00, module_01, module_02, module_03, module_04, module_05, module_06
    ]
    
    total_files = 0
    
    for mod in modules:
        meta = mod.MODULE_METADATA
        mod_num = meta['num']
        mod_name_vi = MODULE_NAMES_VI.get(mod_num, meta['name'])
        dir_name = meta['dir_name']
        out_dir = f"/Volumes/SSD/javis-saas/docs/academy/{dir_name}/slides-and-audio"
        os.makedirs(out_dir, exist_ok=True)
        
        print(f"\nProcessing Module {mod_num}: {mod_name_vi} ({len(mod.LESSONS_DATA)} lessons)...")
        
        for lesson in mod.LESSONS_DATA:
            prefix = lesson['file_prefix']
            lesson_id = lesson['id']
            lesson_slug = lesson['slug']
            lifecycle_topic = lesson['lifecycle_topic']
            
            title_vi, slides_vi, narration_vi = process_lesson(lesson, meta, cache)
            
            # Render markdown contents
            slides_prompt_md = common.render_slides_prompt_vi(
                lesson_id=lesson_id,
                lesson_slug=lesson_slug,
                title=title_vi,
                module_num=mod_num,
                module_name=mod_name_vi,
                lifecycle_topic=lifecycle_topic,
                slides_data=slides_vi
            )
            
            audio_script_md = common.render_audio_script_vi(
                lesson_id=lesson_id,
                lesson_slug=lesson_slug,
                title=title_vi,
                module_num=mod_num,
                module_name=mod_name_vi,
                lifecycle_topic=lifecycle_topic,
                slides_narration=narration_vi
            )
            
            # Write files
            slide_file_path = os.path.join(out_dir, f"{prefix}-slides-prompt-vi.md")
            audio_file_path = os.path.join(out_dir, f"{prefix}-audio-script-vi.md")
            
            with open(slide_file_path, 'w', encoding='utf-8') as f:
                f.write(slides_prompt_md)
                
            with open(audio_file_path, 'w', encoding='utf-8') as f:
                f.write(audio_script_md)
                
            total_files += 2
            print(f"  ✓ [{prefix}] {title_vi} -> 2 VI files written")
            
        save_cache(cache)
        print(f"Module {mod_num} completed. Cache size: {len(cache)}")
        
    save_cache(cache)
    print(f"\n==================================================")
    print(f"SUCCESS: Generated {total_files} Vietnamese production files across all 7 modules!")
    print(f"==================================================")

if __name__ == '__main__':
    run()
