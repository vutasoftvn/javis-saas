// IA09 — cas-client.ts trước đây thiếu header developer credentials
// (x-client-id/x-secret-key/X-BankHub-Api-Version), dùng sai path
// (/tokens/exchange thay vì /grant/exchange), sai casing body
// (public_token thay vì publicToken), và thừa tiền tố "Bearer " trên
// Authorization. Test này khoá lại đúng contract đã xác nhận qua tài liệu
// công khai thật của cas.so (WebFetch) — KHÔNG gọi mạng thật, chỉ mock
// global fetch để assert request thực sự gửi đi đúng shape.
import { afterEach, describe, expect, it, vi } from "vitest";
import { casExchangePublicToken, casGetTransactions } from "../services/cas-client";

describe("Cas.so client contract (IA09)", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("casGetTransactions sends developer headers and a raw (non-Bearer) Authorization token", async () => {
    const fetchMock = vi.fn(async (_url: string, _init?: RequestInit) =>
      new Response(JSON.stringify({ data: [], pagination: { has_more: false } }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );
    vi.stubGlobal("fetch", fetchMock);

    await casGetTransactions({
      accessToken: "real-access-token",
      environment: "sandbox",
      clientId: "client-abc",
      secretKey: "secret-xyz",
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toBe("https://sandbox.bankhub.dev/transactions");
    const headers = init!.headers as Record<string, string>;
    expect(headers["Authorization"]).toBe("real-access-token");
    expect(headers["x-client-id"]).toBe("client-abc");
    expect(headers["x-secret-key"]).toBe("secret-xyz");
    expect(headers["X-BankHub-Api-Version"]).toBe("2023-01-01");
  });

  it("casExchangePublicToken calls POST /grant/exchange with camelCase publicToken body", async () => {
    const fetchMock = vi.fn(async (_url: string, _init?: RequestInit) =>
      new Response(
        JSON.stringify({ accessToken: "at_123", grantId: "grant_123", expiresAt: "2027-01-01T00:00:00Z" }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await casExchangePublicToken("pub_token_abc", "sandbox", {
      clientId: "client-abc",
      secretKey: "secret-xyz",
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toBe("https://sandbox.bankhub.dev/grant/exchange");
    expect(init!.method).toBe("POST");
    const body = JSON.parse(init!.body as string);
    expect(body).toEqual({ publicToken: "pub_token_abc" });
    expect(body.public_token).toBeUndefined();

    expect(result).toEqual({ accessToken: "at_123", grantId: "grant_123", expiresAt: "2027-01-01T00:00:00Z" });
  });

  it("casExchangePublicToken also accepts a snake_case response as a defensive fallback", async () => {
    const fetchMock = vi.fn(async () =>
      new Response(
        JSON.stringify({ access_token: "at_snake", grant_id: "grant_snake", expires_at: "2027-01-01T00:00:00Z" }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await casExchangePublicToken("pub_token_abc", "sandbox", {
      clientId: "client-abc",
      secretKey: "secret-xyz",
    });

    expect(result).toEqual({ accessToken: "at_snake", grantId: "grant_snake", expiresAt: "2027-01-01T00:00:00Z" });
  });

  it("casExchangePublicToken throws CAS_EXCHANGE_FAILED when the provider rejects the request", async () => {
    const fetchMock = vi.fn(async () => new Response("Bad Request", { status: 400, statusText: "Bad Request" }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      casExchangePublicToken("garbage", "sandbox", { clientId: "client-abc", secretKey: "secret-xyz" })
    ).rejects.toThrow(/CAS_EXCHANGE_FAILED/);
  });
});
