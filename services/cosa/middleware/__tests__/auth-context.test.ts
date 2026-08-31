import { describe, it, expect, vi } from 'vitest';
import { extractAuthContext, AuthContext } from '../auth-context.middleware';
import { APIError } from 'encore.dev/api';
import * as tokenService from '../../services/token.service';

describe('extractAuthContext', () => {
  it('should extract valid auth context from headers', () => {
    const mockPlatformToken: tokenService.PlatformJwtPayload = {
      sub: 'user-789',
      aud: 'cosa',
      role: 'user',
      workspaceId: 'ws-test-456',
    };
    vi.spyOn(tokenService, 'verifyPlatformToken').mockReturnValue(mockPlatformToken);

    const context = extractAuthContext(
      'Bearer valid-token-123',
      'ws-test-456'
    );

    expect(context.userID).toBe('user-789');
    expect(context.workspaceId).toBe('ws-test-456');
    expect(context.claims.sub).toBe('user-789');
  });

  it('should throw unauthenticated if no Authorization header', () => {
    expect(() => {
      extractAuthContext(undefined, 'ws-test-456');
    }).toThrow();
  });

  it('should throw unauthenticated if Authorization header does not start with Bearer', () => {
    expect(() => {
      extractAuthContext('Basic 12345', 'ws-test-456');
    }).toThrow();
  });

  it('should throw permissionDenied if workspace header is missing', () => {
    const mockPlatformToken: tokenService.PlatformJwtPayload = {
      sub: 'user-789',
      aud: 'cosa',
      role: 'user',
      workspaceId: 'ws-test-456',
    };
    vi.spyOn(tokenService, 'verifyPlatformToken').mockReturnValue(mockPlatformToken);

    expect(() => {
      extractAuthContext('Bearer valid-token-123', undefined);
    }).toThrow();
  });

  it('should throw permissionDenied if workspace mismatch in token claims', () => {
    const mockPlatformToken: tokenService.PlatformJwtPayload = {
      sub: 'user-789',
      aud: 'cosa',
      role: 'user',
      workspaceId: 'ws-allowed-1',
    };
    vi.spyOn(tokenService, 'verifyPlatformToken').mockReturnValue(mockPlatformToken);

    expect(() => {
      extractAuthContext('Bearer valid-token-123', 'ws-forbidden');
    }).toThrow();
  });
});
