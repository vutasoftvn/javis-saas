# Runbook: nâng PostgreSQL 16 -> 18 cho production (dump/restore, có downtime)

Trạng thái: đã diễn tập đầy đủ trên container local (2026-10-05, xem "Rehearsal evidence"). Chưa chạy trên production thật.

## 1. Phạm vi và điều kiện tiên quyết

- Phạm vi: cluster Postgres của stack `deploy/central_vps` (3 DB logic: `agent`, `cosa`, `workspace`; extension `vector` trong `agent`). Image đích: `pgvector/pgvector:pg18` (PG 18.x, pgvector 0.8.x).
- Compose đã đổi sang image pg18 + volume MỚI (`central_pgdata18` / `prod_pgdata18`, mount `/var/lib/postgresql`). Volume pg16 cũ (`central_pgdata` / `prod_pgdata`) KHÔNG bị đụng, dùng để rollback.
- Điều kiện: quyền SSH VPS, đủ ổ đĩa (>= 3x kích thước DB: volume cũ + dump + volume mới), `.env` prod có đủ 6 mật khẩu `*_APP_PASSWORD` / `*_MIGRATOR_PASSWORD` và `POSTGRES_PASSWORD`, đã pull trước image `pgvector/pgvector:pg18`, đã đọc toàn bộ runbook này, có cửa sổ bảo trì đã thông báo.
- Đặt biến dùng chung cho các lệnh bên dưới (chỉnh theo máy thật):

```bash
cd /srv/javis-saas/deploy/central_vps            # thư mục chứa compose
export COMPOSE_FILE=docker-compose.prod.yaml     # hoặc docker-compose.yaml
export PROJ="$(docker compose ps -q postgres | xargs docker inspect -f '{{index .Config.Labels "com.docker.compose.project"}}')"
export NET="${PROJ}_default"                      # kiểm tra: docker network ls | grep "$PROJ"
export PGSVC=postgres                             # tên service trong compose
export BK=/var/backups/pg18-cutover/$(date -u +%Y%m%dT%H%M%SZ); mkdir -p "$BK"
set -a; . ./.env; set +a                          # POSTGRES_USER, POSTGRES_PASSWORD, ...
```

## 2. Quyết định theo loại triển khai

| Tình huống | Làm gì |
|---|---|
| Postgres chạy bằng compose của repo (`postgres` trong `docker-compose*.yaml`) | Làm đúng runbook này. |
| Postgres là resource do Coolify quản lý (README `deploy/central_vps`, Bước 2) | Phiên bản đặt trong Coolify UI (ngoài repo). Bước 1-5 làm giống nhau (dump bằng client pg18 qua network của Coolify); thay "bước 6 start pg18 bằng compose" bằng: tạo resource PostgreSQL MỚI image `pgvector/pgvector:pg18` trong Coolify (volume mới), chạy `deploy/postgres/init/01-create-app-roles.sql` thủ công (`psql -f`, truyền 6 mật khẩu qua env), rồi đổi `*_DATABASE_URL` trỏ sang resource mới. Resource pg16 cũ giữ nguyên để rollback. Cần xác nhận Coolify cho chọn image có pgvector. |
| DB managed của nhà cung cấp (RDS/Cloud SQL...) | Dùng công cụ nâng cấp major của nhà cung cấp (blue/green); runbook này chỉ tham khảo phần verify. |

## 3. Rủi ro

- Downtime: toàn bộ thời gian dump + restore + verify, ước tính mục 9. Writer phải dừng để dump nhất quán.
- Volume không tương thích: data dir PG16 không mở được bằng PG18. Image pg18 đặt PGDATA `/var/lib/postgresql/18/docker` và khai báo `VOLUME /var/lib/postgresql`, nên mount `.../data` sẽ lỗi hoặc tạo volume ẩn. Vì vậy dùng volume mới + mount thư mục cha.
- Phiên bản client: `pg_dump`/`pg_restore` phải >= major của server. Sau nâng cấp, client 16 chạy với server 18 sẽ FAIL. `scripts/backup/pg-backup.sh` đã có guard (`pg_dump 16 older than server 18`); host chạy backup phải cài `postgresql-client-18` (hoặc chạy script trong container pg18) TRƯỚC khi cron chạy lần đầu sau cutover.
- pgvector: phiên bản có thể đổi (rehearsal: 0.8.6 -> 0.8.7). Dump logic tạo lại extension từ image mới nên không cần `ALTER EXTENSION UPDATE`. Index HNSW/IVFFlat được build lại khi restore (tốn thời gian với bảng vector lớn).
- RPO 24h: backup định kỳ có thể cũ tới 24h. KHÔNG dựa vào backup cron; luôn dump mới trong cửa sổ bảo trì sau khi dừng writer.
- Hành vi mới của PG17/18: ACL owner có thêm quyền `m` (MAINTAIN) (vô hại, quan sát ở rehearsal); các thay đổi khác không ảnh hưởng schema repo (fingerprint trùng).
- Role/password: script init tạo role từ env, không replay globals (xem 5.4).

## 4. Chuẩn bị (T-1 ngày)

```bash
docker pull pgvector/pgvector:pg18
docker compose config -q                      # compose hợp lệ
docker exec "$(docker compose ps -q $PGSVC)" psql -U "$POSTGRES_USER" -Atc "select datname,pg_size_pretty(pg_database_size(datname)) from pg_database order by 1"
df -h /var/lib/docker "$(dirname "$BK")"
```

Lưu số dòng các bảng chính của nguồn (đối chiếu sau restore); sửa danh sách bảng cho đúng:

```bash
cat > "$BK/tables.txt" <<'T'
agent agent.run_events
agent agent_conversation.messages
agent knowledge.knowledge_chunks
cosa cosa.users
cosa cosa.organizations
workspace operating.project_agent_assignments
workspace core.role_permissions
T
counts() {  # $1 = container postgres
  while read -r db t; do echo "$db $t $(docker exec "$1" psql -U "$POSTGRES_USER" -d "$db" -Atc "select count(*) from $t")"; done < "$BK/tables.txt"
}
```

## 5. Cutover (dump/restore, có downtime)

1. Thông báo bảo trì (kênh nội bộ + banner) và ghi mốc giờ bắt đầu.
2. Dừng writer, chỉ để postgres chạy:
   ```bash
   docker compose stop cosa-api cosa-worker cosa-ingestion-worker services-company services-cosa
   docker compose ps          # chỉ còn postgres (+ minio/caddy nếu có)
   PG16=$(docker compose ps -q $PGSVC)
   counts "$PG16" | tee "$BK/counts16.txt"
   ```
   (Nếu chạy `docker-compose.yaml` central: dừng các tiến trình ngoài compose kết nối vào cổng 5434.)
3. Backup cuối bằng client pg18 (đã kiểm chứng ở rehearsal):
   ```bash
   for d in agent cosa workspace; do
     docker run --rm --network "$NET" -e PGPASSWORD="$POSTGRES_PASSWORD" -v "$BK":/out pgvector/pgvector:pg18 \
       pg_dump -h $PGSVC -U "$POSTGRES_USER" -Fc -d $d -f /out/$d.dump
   done
   docker run --rm --network "$NET" -e PGPASSWORD="$POSTGRES_PASSWORD" -v "$BK":/out pgvector/pgvector:pg18 \
     pg_dumpall -h $PGSVC -U "$POSTGRES_USER" --globals-only -f /out/globals.sql     # chỉ để lưu trữ/đối chiếu
   (cd "$BK" && sha256sum *.dump globals.sql | tee SHA256SUMS && ls -l)
   ```
   Chép thêm `$BK` ra ngoài VPS (object store / máy khác).
4. Kiểm tra checksum và tính hợp lệ: `(cd "$BK" && sha256sum -c SHA256SUMS)` và `docker run --rm -v "$BK":/in pgvector/pgvector:pg18 pg_restore --list /in/agent.dump | head`. Không tiếp tục nếu lỗi.
5. Dừng pg16, GIỮ volume cũ:
   ```bash
   docker compose stop $PGSVC && docker compose rm -f $PGSVC     # KHÔNG dùng `down -v`
   docker volume ls | grep pgdata        # volume pg16 cũ (central_pgdata / prod_pgdata) vẫn còn
   ```
6. Khởi động pg18 trên volume MỚI (compose đã trỏ `*_pgdata18`; entrypoint chạy `deploy/postgres/init` tạo role + 3 DB + extension vector):
   ```bash
   git pull && docker compose up -d $PGSVC
   docker compose logs $PGSVC | grep -E "init process complete|ready to accept"
   PG18=$(docker compose ps -q $PGSVC)
   docker exec "$PG18" psql -U "$POSTGRES_USER" -Atc "show server_version"
   docker exec "$PG18" psql -U "$POSTGRES_USER" -Atc "select rolname from pg_roles where rolname ~ '_(app|migrator)$' order by 1"
   docker exec "$PG18" psql -U "$POSTGRES_USER" -Atc "select datname from pg_database where datname in ('agent','cosa','workspace')"
   ```
   Globals KHÔNG replay: script init đã tạo đúng 6 role với mật khẩu lấy từ env hiện hành (là nguồn sự thật), replay `globals.sql` sẽ ghi đè bằng hash cũ và xung đột `CREATE ROLE`.
7. Restore từng DB (đúng flag đã kiểm chứng; chạy bằng superuser nên owner = `*_migrator` và GRANT cho `*_app` được giữ nguyên; `--clean --if-exists` thay extension `vector` do init tạo bằng bản trong dump; `--single-transaction --exit-on-error` để lỗi nào cũng rollback sạch):
   ```bash
   for d in agent cosa workspace; do
     docker run --rm --network "$NET" -e PGPASSWORD="$POSTGRES_PASSWORD" -v "$BK":/in:ro pgvector/pgvector:pg18 \
       pg_restore -h $PGSVC -U "$POSTGRES_USER" -d $d --clean --if-exists --exit-on-error --single-transaction /in/$d.dump || { echo "RESTORE FAIL $d"; break; }
   done
   ```
   Không dùng `--no-owner/--no-privileges` ở bước này (sẽ mất GRANT cho app role). Không được có warning/lỗi; nếu có -> NO-GO.
8. `ANALYZE` (thống kê planner không đi theo dump):
   ```bash
   for d in agent cosa workspace; do docker exec "$PG18" psql -U "$POSTGRES_USER" -d $d -qc "ANALYZE"; done
   ```
9. Migration phải báo "nothing to apply" (đặt `*_MIGRATOR_DATABASE_URL` trỏ pg18):
   ```bash
   make migrate-all      # hoặc từng cái:
   (cd services/cosa    && node scripts/migrate.mjs)      # [migrate:cosa] nothing to apply, already up to date
   (cd services/company && node scripts/migrate.mjs)      # [migrate:company] nothing to apply, already up to date
   python -m packages.agent.scripts.migrate               # [migrate:agent] nothing to apply, already up to date
   ```
10. Verification checklist (tất cả phải đạt):
   - [ ] Row count bằng nguồn: `counts "$PG18" | diff - "$BK/counts16.txt"` không có khác biệt.
   - [ ] `select extname, extversion from pg_extension;` trong DB `agent` có `vector`.
   - [ ] `node scripts/schema-fingerprint.mjs --check` (ba URL migrator trỏ pg18) báo MATCH. Lưu ý: nếu DB nguồn đã lệch golden TRƯỚC khi nâng cấp thì pg18 lệch y hệt; so sánh với fingerprint chạy trên pg16 nguồn (bước 2) để phân biệt.
   - [ ] Truy vấn vector chạy được: `select count(*) from knowledge.knowledge_chunks where embedding is not null;` và một truy vấn `<=>`/`<->`.
   - [ ] Quyền app role: `PGPASSWORD=$AGENT_APP_PASSWORD psql -h ... -U agent_app -d agent -c "select 1 from agent.run_events limit 1"`.
   - [ ] Backup script chạy được với client 18: `BACKUP_DATABASES=... bash scripts/backup/pg-backup.sh` (guard in `pg_dump 18 >= server 18 OK`); manifest mới để `check-backup-freshness.sh` đạt.
   - [ ] Bật lại app: `docker compose up -d` rồi chạy smoke trong `deploy/central_vps/smoke` + `make deploy-preflight`.
11. Go/no-go: GO khi toàn bộ checklist trên đạt và smoke xanh. NO-GO (rollback mục 6) khi: restore có lỗi, row count lệch, fingerprint lệch so với pg16, migrator còn "applying", extension/vector lỗi, hoặc smoke đỏ. Quyết định trước khi app nhận ghi.

## 6. Rollback

Chỉ an toàn TRƯỚC khi app nhận ghi trên pg18 (dữ liệu ghi sau cutover sẽ mất nếu quay lại, trừ khi export lại).

```bash
docker compose stop cosa-api cosa-worker cosa-ingestion-worker services-company services-cosa
# (nếu đã nhận ghi trên pg18 và cần giữ: pg_dump -Fc từng DB bằng client 18 để import thủ công sang pg16 sau)
docker compose stop $PGSVC && docker compose rm -f $PGSVC
git checkout <commit-trước-khi-nâng>  -- deploy/central_vps/docker-compose*.yaml   # image pg16 + volume cũ (central_pgdata / prod_pgdata)
docker compose up -d $PGSVC && docker compose up -d
```
Volume pg18 giữ lại để điều tra. Rehearsal đã chứng minh pg16 + volume cũ khởi động lại bình thường sau khi pg18 chạy (counts giống hệt).

## 7. Dọn dẹp sau nâng cấp

- Giữ volume pg16 cũ và thư mục `$BK` tối thiểu N = 7 ngày sau cutover (và sau ít nhất 1 chu kỳ backup `weekly` thành công trên pg18).
- Sau đó: `docker volume rm <project>_central_pgdata` / `<project>_prod_pgdata`; xoá `$BK` hoặc chuyển vào lưu trữ lạnh.
- Cập nhật host cài `postgresql-client-18` (backup cron, drill restore). Ghi kết quả vào `docs/operations/disaster-recovery.md` (Rehearsal log).

## 8. Phương án thay thế: `pg_upgrade --link` (KHÔNG khuyến nghị)

Nhanh hơn với DB rất lớn, nhưng cần cả binary PG16 và PG18 trong cùng một container (image pgvector chỉ có một major, phải tự dựng image), phải khớp đúng bản pgvector ở hai phía, thao tác trên chính data dir (`--link` làm volume cũ không còn rollback được sau khi chạy pg18), cần `pg_upgrade --check` và chạy lại `vacuumdb --analyze-in-stages`. Dữ liệu ở đây nhỏ (< vài trăm MB), dump/restore chỉ mất vài giây và cho phép rollback sạch nên không đáng đánh đổi.

## 9. Ước tính downtime

Rehearsal: dump + restore ~ 1-2 giây cho DB 120 MB (dump 9.7 MB). Ngân sách thực tế gồm: dừng app, dump, chép dump, init pg18 (~10 giây), restore, ANALYZE, migrate, smoke. Nên đặt cửa sổ 30-60 phút cho quy mô hiện tại; nếu DB prod lớn hơn nhiều, nhân tuyến tính theo kích thước dump (restore tuần tự, cộng build lại index vector).

## 10. Rehearsal evidence (2026-10-05)

Môi trường: container local dùng một lần, mạng docker `rehearsal-net`, cổng 55440/55441, đã xoá sạch sau khi xong. Nguồn: `pg_dumpall` của cluster dev PG16 (78 MB SQL, 6 DB: agent, cosa, workspace và 3 DB test; DB dev thật không bị đụng).

a. Dựng nguồn PG16 (`rehearsal-pg16`, `pgvector/pgvector:pg16`, trống, không init) và restore dumpall:
```bash
docker run -d --name rehearsal-pg16 --network rehearsal-net -e POSTGRES_PASSWORD=*** -p 127.0.0.1:55440:5432 -v rehearsal-pg16-data:/var/lib/postgresql/data pgvector/pgvector:pg16
docker exec -i rehearsal-pg16 psql -U postgres -f - < cosa_postgres_pg16_dumpall.sql     # 5.9 giây
```
Kết quả: chỉ 1 lỗi vô hại `role "postgres" already exists`. Có 3 DB đích (agent 15 MB, cosa 10 MB, workspace 20 MB) + 3 DB test (workspace test 120 MB). pgvector 0.8.6 trong `agent` (cột `knowledge.knowledge_chunks.embedding`, 27 dòng nhưng 0 vector thật). Row count 32 bảng chính (top theo `n_live_tup` mỗi DB + 2 bảng knowledge), `count(*)` chính xác:

```
agent agent.project_activity_events 959
agent agent.project_activity_idempotency 959
agent agent.run_events 339
agent agent_conversation.run_stream_events 323
agent agent_registry.published_specs 212
agent agent_artifact.workspace_artifacts 202
agent agent_conversation.messages 151
agent agent.runtime_signal_outbox 145
agent agent.agent_skill_candidates 105
agent agent.project_activity_sequences 67
cosa control_plane.organization_settings_audit_events 126
cosa cosa.users 96
cosa cosa.profiles 95
cosa cosa.organization_memberships 93
cosa cosa.organizations 83
cosa cosa.organization_sync_log 50
cosa cosa.organization_entitlements 49
cosa cosa.organization_licenses 49
cosa control_plane.organization_connector_installations 17
cosa control_plane.connector_authorizations 16
workspace operating.project_agent_assignment_events 124
workspace operating.project_agent_assignments 96
workspace legal.ai_system_capability_bindings 82
workspace public.schema_migrations 62
workspace integration.event_outbox 39
workspace core.permission_definitions 32
workspace core.role_permissions 31
workspace operating.founder_asset_events 30
workspace legal.ai_compliance_evidence 28
workspace legal.ai_data_processing_profiles 28
agent knowledge.chunk_embeddings 0
agent knowledge.knowledge_chunks 27
```

b. Dump bằng client PG18 (image `pgvector/pgvector:pg18`, pg_dump 18.6) từ pg16:
```bash
docker run --rm --network rehearsal-net -e PGPASSWORD=*** -v $OUT:/out pgvector/pgvector:pg18 pg_dump -h rehearsal-pg16 -U postgres -Fc -d agent -f /out/agent.dump   # tương tự cosa, workspace
docker run --rm ... pgvector/pgvector:pg18 pg_dumpall -h rehearsal-pg16 -U postgres --globals-only -f /out/globals.sql
```
Mỗi dump <= 1 giây. Kích thước và sha256:
```
672239  c664ca6863984d7603eb5368dfae3b8df547f6f564a752f7f0fbc5a61117860a  agent.dump
143591  041cdc8ce51c1a9f4cb1174e6b087d1b2881c38885ec10f886ef55489337a410  cosa.dump
845233  48bd058f432f28940ae7186d5fe821579bbcb3c0e9ae60fe764e3265338f836e  workspace.dump
2351    80a70488951542cb7a662e8dae794fc98605a14656a645644a8c6815431af38e  globals.sql
```

c. `rehearsal-pg18` (image pg18, 18.6) trên volume MỚI `rehearsal-pg18-data` mount `/var/lib/postgresql`, init `deploy/postgres/init` + 6 mật khẩu giả: init hoàn tất, đủ 6 role `*_app`/`*_migrator`, 3 DB owner đúng, `vector 0.8.7` trong `agent`, PGDATA `/var/lib/postgresql/18/docker`. Restore:
```bash
docker run --rm --network rehearsal-net -e PGPASSWORD=*** -v $OUT:/in:ro pgvector/pgvector:pg18 \
  pg_restore -h rehearsal-pg18 -U postgres -d agent --clean --if-exists --exit-on-error --single-transaction /in/agent.dump   # cosa, workspace tương tự
```
Cả 3 rc=0, 0 warning, mỗi DB 0-1 giây. Thêm thử DB lớn (workspace test 118 MB): dump 1 giây, restore 2 giây, rc=0.

d. Verify trên pg18:
- Row count: 32/32 bảng bằng nguồn (`diff` rỗng).
- `pg_extension` trong `agent`: `plpgsql 1.0`, `vector 0.8.7`. Truy vấn pgvector: bảng tạm `vector(3)` + `<->` chạy đúng (bảng thật không có vector để truy vấn).
- ACL/owner toàn bộ bảng/sequence/view/schema giống nguồn, trừ ký hiệu quyền `m` (MAINTAIN, mới từ PG17) trên owner: `arwdDxt` -> `arwdDxtm`.
- Migrator: `[migrate:cosa]`, `[migrate:company]`, `[migrate:agent]` đều "nothing to apply, already up to date".
- `schema-fingerprint --check`: cosa MATCH; agent (`438e719f...`) và workspace (`756505b5...`) MISMATCH so với golden, nhưng chạy cùng lệnh trên NGUỒN pg16 cho kết quả y hệt từng chữ số, tức là drift có sẵn của DB dev (đã lệch golden trước khi nâng cấp: agent 6 bảng, workspace 5 bảng `*_dossier_revisions`), không do PG18/restore. Đối chứng: DB mới tinh trên pg18 migrate từ đầu (cosa 11, company 62, agent 19 migration) -> cả 3 nhóm MATCH golden (agent f40955c3..., cosa 021f2b26..., workspace 3ced4ca0...). Trên production phải MATCH golden hoặc bằng fingerprint pg16 nguồn.

e. Timing: restore dumpall 78 MB vào pg16 5.9 giây; dump 3 DB <= 1 giây mỗi DB; restore 3 DB <= 1 giây mỗi DB; DB 118 MB: dump 1 giây + restore 2 giây; init pg18 khoảng 10 giây.

f. Rollback drill: sau khi pg18 chạy và nhận restore, `rehearsal-pg16` (volume cũ) vẫn nguyên: dừng, `docker restart rehearsal-pg16`, `server_version` = 16.15, 32 bảng count giống hệt trước.

g. Guard backup: `tests/scripts/test_pg_backup_version_guard.sh` (stub pg_dump/psql/aws) PASS 4/4 (client 16 vs server 18 bị chặn rc=1 với `pg_dump 16 older than server 18`; client 18 vs 18 và 18 vs 16 chạy rc=0; không đọc được version -> rc=1). Chưa chạy `pg-backup.sh` thật với object store trên pg18 (cần bước verify ở mục 5.10 khi cutover).
