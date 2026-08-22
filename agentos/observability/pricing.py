from __future__ import annotations

# model name (theo ModelResponse.model) -> (usd trên 1 triệu input token, usd
# trên 1 triệu output token). Cố tình để trống mặc định, không bao giờ đoán
# giá cứng ở đây: blueprint §56 muốn "cost per business outcome" thật, mà quy
# đổi ra $ phụ thuộc mức giá deployer thực sự đàm phán với từng provider —
# repo này không có cách nào biết hay xác minh mức giá đó. Số token (thật, từ
# response API của provider — xem TokenUsage trong agentos/core/model_provider.py)
# luôn được track; cost $ chỉ được tính khi caller tự cung cấp bảng giá riêng.
PricingTable = dict[str, tuple[float, float]]


def estimate_cost_usd(
    model: str | None,
    input_tokens: int,
    output_tokens: int,
    pricing_table: PricingTable,
) -> float | None:
    """Trả về None (không phải số đoán) khi model không có entry trong
    `pricing_table` — một model chưa định giá phải hiện ra là "không rõ
    cost", không bao giờ là 0 giả hay mức giá bịa đặt.
    """
    if model is None or model not in pricing_table:
        return None
    input_rate, output_rate = pricing_table[model]
    return (input_tokens / 1_000_000) * input_rate + (output_tokens / 1_000_000) * output_rate
