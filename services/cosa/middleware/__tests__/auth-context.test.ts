import { describe, it, expect, vi, beforeEach, afterAll } from 'vitest';
import { extractAuthContext } from '../auth-context.middleware';
import * as coreAccess from '../../services/core-access.service';
import { APIError } from 'encore.dev/api';
import jwt from 'jsonwebtoken';

const CORE_TOKEN = 'opaque-core-token';

describe('extractAuthContext (access token OIDC của core)', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  const access = {
    userId: '42',
    info: { userId: '42', clientId: 'vn.mivacorp.cosa', scopes: ['openid'], expiresAt: 9999999999 },
    decision: {
      role: 'founder',
      membershipVersion: 4,
      typeCode: null,
      organizationName: 'Acme',
      ownerUserId: '7',
    },
    role: 'founder',
    cosaRole: 'founder',
    membershipVersion: 4,
  };

  it('core quyết định quyền organization và bản chiếu được cập nhật', async () => {
    const authorize = vi.spyOn(coreAccess, 'authorizeAndProjectCoreAccess').mockResolvedValue(access);

    const context = await extractAuthContext(`Bearer ${CORE_TOKEN}`, '100');

    expect(context).toMatchObject({
      userID: '42',
      organizationId: '100',
      organizationRole: 'founder',
      membershipVersion: 4,
    });
    expect(context.claims).toMatchObject({ sub: '42', aud: 'cosa', role: 'founder', organizationId: '100' });
    expect(authorize).toHaveBeenCalledWith(CORE_TOKEN, '100', 'cosa.workspace.read');
  });

  it('thiếu Authorization hoặc không phải Bearer -> unauthenticated', async () => {
    await expect(extractAuthContext(undefined, '100')).rejects.toMatchObject({ code: 'unauthenticated' });
    await expect(extractAuthContext('Basic 12345', '100')).rejects.toMatchObject({ code: 'unauthenticated' });
  });

  it('token dạng JWT không phải delegation hợp lệ -> unauthenticated, không gọi core', async () => {
    const authorize = vi.spyOn(coreAccess, 'authorizeAndProjectCoreAccess');
    await expect(extractAuthContext('Bearer aaa.bbb.ccc', '100')).rejects.toMatchObject({
      code: 'unauthenticated',
    });
    expect(authorize).not.toHaveBeenCalled();
  });

  it('thiếu header organization -> permissionDenied, không gọi core', async () => {
    const authorize = vi.spyOn(coreAccess, 'authorizeAndProjectCoreAccess');
    await expect(extractAuthContext(`Bearer ${CORE_TOKEN}`, undefined)).rejects.toMatchObject({
      code: 'permission_denied',
    });
    expect(authorize).not.toHaveBeenCalled();
  });

  it('core từ chối token -> lỗi nổi lên nguyên vẹn', async () => {
    vi.spyOn(coreAccess, 'authorizeAndProjectCoreAccess').mockRejectedValue(
      APIError.unauthenticated('invalid or expired access token')
    );
    await expect(extractAuthContext(`Bearer ${CORE_TOKEN}`, '100')).rejects.toMatchObject({
      code: 'unauthenticated',
    });
  });

  it('không phải thành viên organization -> permissionDenied', async () => {
    vi.spyOn(coreAccess, 'authorizeAndProjectCoreAccess').mockRejectedValue(
      APIError.permissionDenied('not a member')
    );
    await expect(extractAuthContext(`Bearer ${CORE_TOKEN}`, '999')).rejects.toMatchObject({
      code: 'permission_denied',
    });
  });
});

describe('extractAuthContext (control-plane delegation do apps/cosa ký)', () => {
  const SECRET = 'test-control-delegation-secret-min-32-chars';
  const prev = process.env.COSA_CONTROL_DELEGATION_SECRET;

  beforeEach(() => {
    vi.restoreAllMocks();
    process.env.COSA_CONTROL_DELEGATION_SECRET = SECRET;
  });

  afterAll(() => {
    if (prev === undefined) delete process.env.COSA_CONTROL_DELEGATION_SECRET;
    else process.env.COSA_CONTROL_DELEGATION_SECRET = prev;
  });

  const sign = (claims: Record<string, unknown>, secret = SECRET) =>
    jwt.sign(claims, secret, { audience: 'cosa_control', issuer: 'cosa_apps', expiresIn: '10m' });

  it('tin claim của delegation (apps/cosa đã kiểm tra thành viên), không gọi core', async () => {
    const authorize = vi.spyOn(coreAccess, 'authorizeAndProjectCoreAccess');
    const token = sign({ sub: '42', workspace_id: '100', role: 'founder' });

    const context = await extractAuthContext(`Bearer ${token}`, '100');

    expect(context).toMatchObject({ userID: '42', organizationId: '100', organizationRole: 'founder' });
    expect(context.claims).toMatchObject({ sub: '42', role: 'founder', organizationId: '100' });
    expect(authorize).not.toHaveBeenCalled();
  });

  it('delegation của workspace khác -> permissionDenied', async () => {
    const token = sign({ sub: '42', workspace_id: '100', role: 'founder' });
    await expect(extractAuthContext(`Bearer ${token}`, '999')).rejects.toMatchObject({
      code: 'permission_denied',
    });
  });

  it('thiếu header workspace -> permissionDenied', async () => {
    const token = sign({ sub: '42', workspace_id: '100', role: 'founder' });
    await expect(extractAuthContext(`Bearer ${token}`, undefined)).rejects.toMatchObject({
      code: 'permission_denied',
    });
  });

  it('delegation ký sai secret -> unauthenticated', async () => {
    const token = sign({ sub: '42', workspace_id: '100', role: 'founder' }, 'a-different-secret-min-32-characters-long');
    await expect(extractAuthContext(`Bearer ${token}`, '100')).rejects.toMatchObject({
      code: 'unauthenticated',
    });
  });
});
