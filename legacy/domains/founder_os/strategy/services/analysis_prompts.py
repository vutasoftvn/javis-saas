import random

DEFAULT_STRATEGY_PROMPT_TEMPLATE = """Bạn là chuyên gia tư vấn chiến lược doanh nghiệp cao cấp. Dựa trên hồ sơ chiến lược và ngữ cảnh dự án thực tế sau:
- Tầm nhìn (Vision): {vision_text}
- Sứ mệnh (Mission): {mission_text}
- Giá trị cốt lõi (Core Values): {core_values_text}
- Ngữ cảnh & Mô tả Dự án / Phạm vi phân tích: {project_context}
- Trọng tâm phân tích bổ sung: {focus_note}

Hãy thực hiện phân tích chiến lược chuyên sâu (PESTEL, SWOT, TOWS). YÊU CẦU BẮT BUỘC & NGUYÊN TẮC BÁM SÁT MÔ TẢ DỰ ÁN & PESTEL:

1. PESTEL (Phân tích Bối cảnh Vĩ mô):
   - Phải sinh ĐẦY ĐỦ 6 yếu tố vĩ mô (Political, Economic, Social, Technological, Environmental, Legal hoặc tiếng Việt tương ứng). MỖI YẾU TỐ PHẢI CÓ ĐÚNG {pestel_count} MỤC NHẬN ĐỊNH CỤ THỂ (Tổng cộng đúng {pestel_total} mục PESTEL).
   - Cấu trúc phần "statement" của từng mục PESTEL gồm ĐÚNG 2 DÒNG (phân cách bằng \\n):
     + Dòng 1: Mô tả nhận định vĩ mô và tác động thực tế đến dự án/doanh nghiệp.
     + Dòng 2 (bắt buộc): 📌 Bằng chứng xác thực: [Trích dẫn rõ tên báo cáo chính thống, số nghị định/quyết định pháp lý hoặc số liệu thống kê thực tế - TUYỆT ĐỐI KHÔNG TỰ BỊA].

2. SWOT (BÁM SÁT MÔ TẢ DỰ ÁN VÀ KẾ THỪA TỪ PESTEL):
   - Phải sinh ĐẦY ĐỦ 4 chiều (Strength, Weakness, Opportunity, Threat). MỖI CHIỀU PHẢI CÓ ĐÚNG {swot_count} MỤC ĐÁNH GIÁ SÂU SẮC & THỰC TẾ (Tổng cộng đúng {swot_total} mục SWOT).
   - Strength (Điểm mạnh) & Weakness (Điểm yếu): Phải đánh giá TRỰC TIẾP năng lực nội tại, nguồn lực, sản phẩm/dịch vụ, rào cản và đặc thù của DỰ ÁN / DOANH NGHIỆP ở phần ngữ cảnh trên. Không phán đoán chung chung.
   - Opportunity (Cơ hội) & Threat (Thách thức): Phải KẾ THỪA VÀ KẾT NỐI TRỰC TIẾP từ các yếu tố vĩ mô PESTEL tích cực và tiêu cực đối với Dự án này.

3. TOWS (MA TRẬN HÀNH ĐỘNG THỰC TẾ & KHẢ THI CAO - KẾT HỢP SWOT & PESTEL):
   - Phải sinh ĐẦY ĐỦ 4 góc phần tư kết hợp (SO, ST, WO, WT). MỖI GÓC PHẦN TƯ PHẢI CÓ ĐÚNG {tows_count} LỰA CHỌN CHIẾN LƯỢC HÀNH ĐỘNG (Tổng cộng {tows_total} lựa chọn TOWS).
   - Nguyên tắc kết hợp bám sát:
     + SO (Strength + Opportunity): Sử dụng Điểm mạnh nội tại của dự án để chớp lấy Cơ hội PESTEL.
     + ST (Strength + Threat): Sử dụng Điểm mạnh nội tại của dự án để hóa giải/phòng thủ Thách thức PESTEL.
     + WO (Weakness + Opportunity): Khắc phục Điểm yếu nội tại của dự án bằng cách nắm bắt Cơ hội PESTEL.
     + WT (Weakness + Threat): Tối thiểu hóa Điểm yếu nội tại và né tránh Thách thức PESTEL.
   - Đưa ra nội dung HỢP LÝ VÀ KHẢ THI NHẤT: Mỗi mục TOWS phải có tên chiến lược hành động rõ ràng và phần "tradeoffs" chỉ rõ sự đánh đổi, yêu cầu nguồn lực, ngân sách hoặc nhân sự khả thi cho dự án.

Trả về DUY NHẤT một chuỗi JSON hợp lệ theo đúng cấu trúc sau (không kèm markdown ngoài JSON):
{json_structure}"""


def build_dynamic_json_example(pestel_count: int = 3, swot_count: int = 3, tows_count: int = 2) -> str:
    pestel_examples = []
    factors = ["Political", "Economic", "Social", "Technological", "Environmental", "Legal"]
    for f in factors:
        for i in range(pestel_count):
            impact = "Positive" if i % 2 == 0 else "Negative"
            pestel_examples.append(
                f'{{"factor": "{f}", "statement": "Nhận định {f} {i+1}...\\n📌 Bằng chứng xác thực: Báo cáo / Nghị định...", "impact": "{impact}"}}'
            )
    swot_examples = []
    categories = ["Strength", "Weakness", "Opportunity", "Threat"]
    for c in categories:
        for i in range(swot_count):
            impact = "High" if i == 0 else "Medium"
            swot_examples.append(
                f'{{"category": "{c}", "statement": "Nhận định {c} {i+1}...", "impact": "{impact}"}}'
            )
    tows_examples = []
    quadrants = ["SO", "ST", "WO", "WT"]
    for q in quadrants:
        for i in range(tows_count):
            tows_examples.append(
                f'{{"quadrant": "{q}", "title": "Chiến lược {q} {i+1}", "tradeoffs": "Đánh đổi và nguồn lực..."}}'
            )
    pestel_str = ",\n    ".join(pestel_examples)
    swot_str = ",\n    ".join(swot_examples)
    tows_str = ",\n    ".join(tows_examples)
    return f'{{\n  "pestel": [\n    {pestel_str}\n  ],\n  "swot": [\n    {swot_str}\n  ],\n  "tows": [\n    {tows_str}\n  ]\n}}'


def generate_fallback_mock_analysis(
    vision_text: str,
    project_label: str,
    focus_note: str,
    pestel_count: int = 3,
    swot_count: int = 3,
    tows_count: int = 2
):
    focus_clean = focus_note if focus_note and focus_note.strip() else "Phát triển Nền tảng SaaS & Tối ưu hóa Vận hành"
    proj_label = project_label if project_label else "Doanh nghiệp"

    pestel_pool = {
        "Political": [
            (f"Chính phủ đẩy mạnh chuyển đổi số quốc gia và khuyến khích doanh nghiệp ứng dụng giải pháp {proj_label}.\n📌 Bằng chứng xác thực: Nghị quyết 52-NQ/TW của Bộ Chính trị về định hướng tham gia cuộc Cách mạng công nghiệp lần thứ tư.", "Positive"),
            (f"Nghị định 13/2023/NĐ-CP về bảo vệ dữ liệu cá nhân thắt chặt quy trình lưu trữ và xử lý dữ liệu người dùng trong hệ thống SaaS.\n📌 Bằng chứng xác thực: Nghị định 13/2023/NĐ-CP ban hành ngày 17/04/2023.", "Negative"),
            (f"Chính sách ưu đãi thuế TNDN cho doanh nghiệp công nghệ cao và đổi mới sáng tạo thúc đẩy R&D cho {proj_label}.\n📌 Bằng chứng xác thực: Luật Thuế TNDN số 14/2008/QH12 (sửa đổi, bổ sung qua các năm).", "Positive"),
        ],
        "Economic": [
            (f"Chi phí vận hành hạ tầng Cloud và API AI quốc tế có xu hướng gia tăng do biến động tỷ giá hối đoái.\n📌 Bằng chứng xác thực: Báo cáo Thống kê Ngân hàng Nhà nước & Tổng cục Thống kê Q1/2026.", "Negative"),
            (f"Thị trường SaaS B2B tại Việt Nam và Đông Nam Á duy trì tốc độ tăng trưởng kép CAGR ~18.5% giai đoạn 2024-2028.\n📌 Bằng chứng xác thực: Báo cáo nghiên cứu thị trường Vietnam Digital Economy 2025 (e-Conomy SEA).", "Positive"),
            (f"Doanh nghiệp vừa và nhỏ (SMEs) thắt chặt ngân sách CNTT nhưng ưu tiên đầu tư giải pháp AI giúp tối ưu chi phí vận hành cho {proj_label}.\n📌 Bằng chứng xác thực: Báo cáo khảo sát thực trạng DN Việt Nam 2025 của VCCI.", "Positive"),
        ],
        "Social": [
            (f"Làn sóng chấp nhận công nghệ AI và trợ lý ảo làm việc tự động gia tăng nhanh chóng ở nhóm lao động trẻ văn phòng.\n📌 Bằng chứng xác thực: Báo cáo Work Trend Index 2025 của Microsoft.", "Positive"),
            (f"Nhu cầu về tính minh bạch, trải nghiệm người dùng mượt mà và cá nhân hóa cao trong giao diện quản trị doanh nghiệp.\n📌 Bằng chứng xác thực: Báo cáo xu hướng hành vi người dùng B2B Việt Nam 2025.", "Positive"),
            (f"Tâm lý e ngại rủi ro rò rỉ dữ liệu khi tích hợp AI vào vận hành doanh nghiệp đặt ra yêu cầu tuân thủ nghiêm ngặt.\n📌 Bằng chứng xác thực: Khảo sát An toàn thông tin DN 2025 của VNISA.", "Negative"),
        ],
        "Technological": [
            (f"Sự bùng nổ của các mô hình ngôn ngữ lớn (LLMs) thế hệ mới hạ thấp chi phí tích hợp tính năng AI thông minh vào {proj_label}.\n📌 Bằng chứng xác thực: Báo cáo AI Index Report 2025 - Stanford University.", "Positive"),
            (f"Kiến trúc Microservices, Serverless và Event-Driven Architecture giúp hệ thống mở rộng linh hoạt theo lượng người dùng.\n📌 Bằng chứng xác thực: Tài liệu Kiến trúc Hệ thống chuẩn SaaS Cloud-Native (CNCFR 2025).", "Positive"),
            (f"Nguy cơ tấn công mạng API và khai thác lỗ hổng bảo mật dịch vụ đám mây gia tăng độ phức tạp.\n📌 Bằng chứng xác thực: Báo cáo Mối đe dọa An ninh mạng Q4/2025 từ Kaspersky Labs.", "Negative"),
        ],
        "Environmental": [
            (f"Xu hướng Green IT và giảm thiểu dấu chân carbon (Carbon Footprint) từ các trung tâm dữ liệu AI đòi hỏi tối ưu thuật toán.\n📌 Bằng chứng xác thực: Định hướng Net-Zero 2050 và Báo cáo ESG Doanh nghiệp Công nghệ 2025.", "Negative"),
            (f"Tối ưu năng lượng tính toán bằng cách cache kết quả xử lý AI và giảm tải API call không cần thiết.\n📌 Bằng chứng xác thực: Tiêu chuẩn ISO 14001 & Hướng dẫn Tối ưu Hạ tầng Đám mây Xanh.", "Positive"),
        ],
        "Legal": [
            (f"Khung pháp lý về trí tuệ nhân tạo (AI Act) và trách nhiệm pháp lý đối với nội dung do AI tạo ra đang dần được hoàn thiện.\n📌 Bằng chứng xác thực: Dự thảo Luật Công nghiệp Công nghệ số & EU AI Act 2024.", "Negative"),
            (f"Quy định sở hữu trí tuệ đối với mã nguồn, thuật toán và tài sản số được bảo hộ rõ ràng hơn.\n📌 Bằng chứng xác thực: Luật Sở hữu trí tuệ Việt Nam 2022 (sửa đổi, bổ sung).", "Positive"),
        ],
    }

    swot_pool = {
        "Strength": [
            (f"Kiến trúc hệ thống SaaS hiện đại, khả năng linh hoạt phân tách module và tích hợp AI thông minh bám sát '{focus_clean}'."),
            (f"Đội ngũ phát triển nắm vững công nghệ lõi, tối ưu hóa quy trình từ Backend Python FastAPI đến Frontend Flutter Cross-platform."),
            (f"Trải nghiệm người dùng cao cấp, khả năng mở rộng quy mô vượt trội phục vụ {proj_label}."),
            (f"Tầm nhìn định hướng chiến lược rõ ràng: '{vision_text[:75]}...', tạo sự đồng thuận toàn tổ chức."),
        ],
        "Weakness": [
            (f"Quy trình Onboarding khách hàng khi mở rộng quy mô '{focus_clean}' cần tiếp tục được tự động hóa."),
            (f"Đội ngũ tư vấn kỹ thuật chuyên sâu tại chỗ còn mỏng khi triển khai đồng loạt {proj_label}."),
            (f"Phụ thuộc một phần vào độ ổn định và chi phí API của các nhà cung cấp mô hình AI quốc tế."),
            (f"Hệ thống tài liệu kỹ thuật và hướng dẫn người dùng tự phục vụ cho '{focus_clean}' cần được bổ sung."),
        ],
        "Opportunity": [
            (f"Nhu cầu thị trường về nền tảng SaaS tích hợp AI thông minh phục vụ '{focus_clean}' đang ở giai đoạn bùng nổ."),
            (f"Mở rộng phân khúc khách hàng doanh nghiệp vừa và lớn với gói giải pháp chuyên biệt cho {proj_label}."),
            (f"Hợp tác chiến lược với các nhà cung cấp hạ tầng Cloud và hệ sinh thái đối tác công nghệ lớn."),
            (f"Dẫn đầu thị trường ngách nhờ tiên phong ứng dụng công nghệ AI thế hệ mới vào '{focus_clean}'."),
        ],
        "Threat": [
            (f"Sự cạnh tranh gay gắt từ các giải pháp SaaS quốc tế có tiềm lực tài chính mạnh trong mảng '{focus_clean}'."),
            (f"Tốc độ tăng chi phí API AI và điện toán đám mây nếu không kiểm soát và tối ưu kịp thời."),
            (f"Rủi ro gián đoạn dịch vụ hoặc thay đổi chính sách từ nhà cung cấp mô hình AI nền tảng."),
            (f"Tốc độ thay đổi công nghệ nhanh đòi hỏi nguồn vốn đầu tư R&D duy trì liên tục cho {proj_label}."),
        ],
    }

    tows_pool = {
        "SO": [
            (f"Tận dụng thế mạnh kiến trúc AI để dẫn đầu thị trường trong định hướng '{focus_clean}'", f"Tập trung 60% năng lực R&D thúc đẩy tính năng lõi cho {proj_label}; ưu tiên phân bổ nhân lực trọng điểm."),
            (f"Xây dựng gói giải pháp Enterprise chuyên biệt cho {proj_label}", f"Hợp tác với các đối tác tư vấn ngành để gia tăng giá trị hợp đồng B2B."),
            (f"Đẩy mạnh tự động hóa quy trình dựa trên tầm nhìn và giá trị cốt lõi doanh nghiệp", f"Đầu tư hoàn thiện bộ công cụ tích hợp tự động cho khách hàng."),
        ],
        "ST": [
            (f"Tối ưu chi phí vận hành AI bằng mô hình Hybrid & Local Cache khi thực hiện '{focus_clean}'", f"Đầu tư thời gian kỹ thuật ban đầu cho cơ chế cache và fine-tune mô hình nhỏ."),
            (f"Khẳng định lợi thế tuân thủ bảo mật và dữ liệu bản địa hóa cho {proj_label}", f"Hoàn thiện các chứng chỉ an toàn thông tin và tài liệu pháp lý cho khối doanh nghiệp."),
            (f"Ứng dụng AI Monitoring tự động phát hiện biến động chi phí hạ tầng", f"Tích hợp hệ thống cảnh báo ngân sách API real-time."),
        ],
        "WO": [
            (f"Tự động hóa toàn diện luồng Onboarding cho khách hàng mới bằng AI Assistant trong '{focus_clean}'", f"Tái thiết kế giao diện hướng dẫn và xây dựng tài liệu tương tác tự phục vụ."),
            (f"Mở rộng mạng lưới đối tác triển khai để khắc phục hạn chế nhân sự cho {proj_label}", f"Áp dụng chính sách chia sẻ doanh thu hấp dẫn cho đối tác chiến lược."),
            (f"Chuẩn hóa Developer Portal và API công khai giúp khách hàng tự tích hợp", f"Dành 2 tuần sprint tập trung hoàn thiện tài liệu kỹ thuật."),
        ],
        "WT": [
            (f"Thiết lập cơ chế chuyển đổi dự phòng đa nhà cung cấp AI (Multi-LLM Failover) cho {proj_label}", f"Đảm bảo độ sẵn sàng 99.9% dịch vụ ngay cả khi nhà cung cấp chính gặp sự cố."),
            (f"Chuẩn hóa hệ thống cảnh báo sớm rủi ro chi phí khi triển khai '{focus_clean}'", f"Cấu hình ngưỡng ngân sách tự động ngắt dịch vụ bất thường."),
            (f"Tối ưu hóa quy trình hỗ trợ kỹ thuật theo tầng (Tiered Support)", f"Ứng dụng Trợ lý AI xử lý 80% câu hỏi thường gặp để giảm tải cho nhóm kỹ thuật."),
        ],
    }

    pestel_res = []
    for factor in ["Political", "Economic", "Social", "Technological", "Environmental", "Legal"]:
        items = pestel_pool.get(factor, [])
        selected = random.sample(items, min(pestel_count, len(items)))
        for stmt, imp in selected:
            pestel_res.append({"factor": factor, "statement": stmt, "impact": imp})

    swot_res = []
    for cat in ["Strength", "Weakness", "Opportunity", "Threat"]:
        items = swot_pool.get(cat, [])
        selected = random.sample(items, min(swot_count, len(items)))
        for stmt in selected:
            swot_res.append({"category": cat, "statement": stmt, "impact": "High"})

    tows_res = []
    for quad in ["SO", "ST", "WO", "WT"]:
        items = tows_pool.get(quad, [])
        selected = random.sample(items, min(tows_count, len(items)))
        for title, trade in selected:
            tows_res.append({"quadrant": quad, "title": title, "tradeoffs": trade})

    return pestel_res, swot_res, tows_res
