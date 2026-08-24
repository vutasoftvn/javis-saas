# Integration: A2A

## 1. Mục đích

Attenuate quyền hạn cho remote agent con — invariant bắt buộc `Authority(child) ⊆ Authority(parent)`.

## 2. Khi nào sử dụng

Khi 1 agent giao việc cho remote agent khác (A2A protocol) và cần tính toán quyền hạn thực tế cho agent con.

## 3. Không dùng cho việc gì

Không dùng để MỞ RỘNG quyền — `attenuate_authority()` chỉ có thể thu hẹp, không bao giờ mở rộng dù `requested` yêu cầu gì.

## 4. Kiến trúc và luồng dữ liệu

```
attenuate_authority(parent: A2AAuthorityGrant, requested: A2AAuthorityGrant) -> A2AAuthorityGrant (child)
  capability_refs = giao(requested, parent) theo wildcard prefix
  max_risk = min(parent, requested) theo LOW<MEDIUM<HIGH<CRITICAL
  expires_at = sớm hơn giữa 2 bên
  tenant_id = LUÔN theo parent (không theo requested, dù child tự khai tenant khác)
```

## 5. Public contracts/API

`agent_integrations.a2a.authority.{A2AAuthorityGrant, attenuate_authority}`.

## 6. Database/schema liên quan

Không có — pure function, không persist.

## 7. Cấu hình

Không có.

## 8. Ví dụ sử dụng

```python
child_grant = attenuate_authority(parent_grant, requested_grant)
# child_grant.capability_refs, .max_risk, .expires_at, .tenant_id đều <= parent
```

## 9. Cách bổ sung implementation mới

Không cần — pure function đủ dùng cho mọi trường hợp attenuation.

## 10. Security/governance

Đây CHÍNH LÀ cơ chế governance cho A2A — không có tầng nào khác kiểm soát.

## 11. Error handling

Không raise exception — luôn trả về grant hợp lệ (rỗng nếu không có giao capability nào).

## 12. Observability

Không có event riêng — caller nên log `child_grant` khi cấp cho remote agent.

## 13. Testing

`packages/agent_testkit/protocol_conformance/test_a2a_authority_attenuation.py` — 5 test cố ý cho `requested` vượt `parent` ở 4 chiều (capability/risk/expiry/tenant), chứng minh luôn bị chặn.

## 14. Migration/backward compatibility

Package mới hoàn toàn.

## 15. Troubleshooting

Child mất hết capability sau attenuate: kiểm tra `parent.capability_refs` có bao phủ đúng `requested.capability_refs` qua wildcard prefix (`"domain.*"`) không.

## 16. Definition of Done

- [x] Invariant verify đầy đủ 4 chiều, test không cần network
- [ ] Chưa wire vào 1 A2A transport thật (chỉ có logic attenuation, chưa có client/server A2A)
