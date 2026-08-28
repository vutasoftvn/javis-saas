-- Tạo role Postgres RIÊNG cho từng service, KHÔNG dùng chung role superuser
-- `javis`/`postgres` mặc định của image - vá rủi ro 1 credential có toàn
-- quyền trên cả cluster (superuser) đã phát hiện khi audit auth.
--
-- Chỉ chạy tự động qua docker-entrypoint-initdb.d khi khởi tạo volume MỚI
-- (Postgres image chỉ chạy các script trong thư mục này lần đầu tiên, lúc
-- data directory còn trống). Instance đang chạy sẵn phải tạo role này thủ
-- công 1 lần (xem README/db.md).
--
-- Mật khẩu ở đây là PLACEHOLDER cho dev/local - production PHẢI đổi qua
-- ALTER ROLE ... WITH PASSWORD '<secret thật>' sau khi khởi tạo, không commit
-- mật khẩu thật vào repo.

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'javis_app') THEN
        CREATE ROLE javis_app WITH LOGIN PASSWORD 'change-me-javis-app';
    END IF;
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'cosa_control_plane_app') THEN
        CREATE ROLE cosa_control_plane_app WITH LOGIN PASSWORD 'change-me-control-plane-app';
    END IF;
END
$$;

-- javis_app: full quyền trên database javis (Local Business - schema public,
-- agent_runtime, integrations) - dùng cho brain-api, agent-worker,
-- realtime-agent*, migrate.
GRANT ALL PRIVILEGES ON DATABASE javis TO javis_app;

-- GRANT ALL PRIVILEGES ON DATABASE chỉ cấp CONNECT/CREATE/TEMP ở mức database,
-- KHÔNG cấp quyền trên schema/bảng bên trong - cấp riêng cho schema `public`
-- (script này chạy trong lúc kết nối đang ở database `javis`, do Postgres
-- image init connect vào $POSTGRES_DB mặc định). Schema `agent_runtime`/
-- `integrations` được tạo sau ở migration riêng (không thuộc phạm vi script
-- init này) - grant tương ứng khi đó.
GRANT ALL ON SCHEMA public TO javis_app;
GRANT ALL ON ALL TABLES IN SCHEMA public TO javis_app;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO javis_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO javis_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO javis_app;

-- cosa_control_plane_app: full quyền trên database cosa_control_plane
-- (Central Control Plane - schema control_plane) - dùng cho
-- migrate-control-plane và mọi service chạy role central_control_plane.
SELECT 'CREATE DATABASE cosa_control_plane OWNER cosa_control_plane_app'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'cosa_control_plane')
\gexec

GRANT ALL PRIVILEGES ON DATABASE cosa_control_plane TO cosa_control_plane_app;

-- company: dedicated database cho company service
SELECT 'CREATE DATABASE company'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'company')
\gexec

GRANT ALL PRIVILEGES ON DATABASE company TO javis_app;

-- QUAN TRỌNG: Postgres mặc định cấp CONNECT trên MỌI database cho role PUBLIC
-- (mọi role login đều là thành viên PUBLIC) - GRANT ALL PRIVILEGES ở trên
-- KHÔNG tự cô lập 2 role với nhau. Phải REVOKE CONNECT FROM PUBLIC rồi GRANT
-- lại đích danh, nếu không javis_app vẫn kết nối được vào cosa_control_plane
-- và ngược lại (đã verify thực nghiệm lúc thiết lập role này lần đầu).
REVOKE CONNECT ON DATABASE javis FROM PUBLIC;
REVOKE CONNECT ON DATABASE cosa_control_plane FROM PUBLIC;
REVOKE CONNECT ON DATABASE company FROM PUBLIC;
GRANT CONNECT ON DATABASE javis TO javis_app;
GRANT CONNECT ON DATABASE cosa_control_plane TO cosa_control_plane_app;
GRANT CONNECT ON DATABASE company TO javis_app;
