import { describe, it, expect } from "vitest";
import { eq, and } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import {
  addMoney,
  subtractMoney,
  compareMoney,
  zeroMoney,
  parseDecimalToMoney,
  formatMoneyToDecimal,
} from "../services/money";
import {
  openAccountingPeriodService,
  closeAccountingPeriodService,
} from "../services/accounting-period.service";
import {
  createDraftDocumentService,
  confirmAccountingDocumentService,
} from "../services/accounting-document.service";
import {
  recordFinancialTransactionService,
} from "../services/financial-transaction.service";
import {
  proposeReconciliationService,
  acceptReconciliationProposalService,
} from "../services/reconciliation-proposal.service";
import {
  computeSnapshot,
  calculateAndSaveSnapshotService,
} from "../services/financial-snapshot.service";
import { createBankConnectionService } from "../services/bank-connection.service";

const {
  bankTransactions,
  bankConnections,
  documentReconciliationProposals,
  accountingDocuments,
  accountingPeriods,
} = schema;

async function makeAuthedWorkspace(displayName: string) {
  const user = await createTestSession({
    email: `${displayName.toLowerCase().replace(/\s+/g, "-")}-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
    displayName,
    role: "founder",
  });
  return {
    workspaceId: user.workspaceId,
    userId: user.userId,
    authorization: `Bearer ${user.accessToken}`,
  };
}

describe("F1 Financial Integrity", () => {
  // -------------------------------------------------------------
  // 1. Money types & arithmetic operations (F09)
  // -------------------------------------------------------------
  describe("Money Operations", () => {
    it("adds money of the same currency accurately", () => {
      const res = addMoney(
        { minor: "1500000", currency: "VND" },
        { minor: "500000", currency: "VND" }
      );
      expect(res).toEqual({ minor: "2000000", currency: "VND" });
    });

    it("throws when adding money of different currencies", () => {
      expect(() =>
        addMoney(
          { minor: "1", currency: "VND" },
          { minor: "1", currency: "USD" }
        )
      ).toThrow();
    });

    it("subtracts money of the same currency accurately", () => {
      const res = subtractMoney(
        { minor: "2000000", currency: "VND" },
        { minor: "500000", currency: "VND" }
      );
      expect(res).toEqual({ minor: "1500000", currency: "VND" });
    });

    it("throws when subtracting money of different currencies", () => {
      expect(() =>
        subtractMoney(
          { minor: "200", currency: "USD" },
          { minor: "100", currency: "EUR" }
        )
      ).toThrow();
    });

    it("compares money of the same currency correctly", () => {
      expect(
        compareMoney(
          { minor: "100", currency: "USD" },
          { minor: "200", currency: "USD" }
        )
      ).toBe(-1);
      expect(
        compareMoney(
          { minor: "200", currency: "USD" },
          { minor: "100", currency: "USD" }
        )
      ).toBe(1);
      expect(
        compareMoney(
          { minor: "150", currency: "USD" },
          { minor: "150", currency: "USD" }
        )
      ).toBe(0);
    });

    it("parses and formats decimal money without floating-point distortion", () => {
      const vnd = parseDecimalToMoney("1500000", "VND");
      expect(vnd).toEqual({ minor: "1500000", currency: "VND" });
      expect(formatMoneyToDecimal(vnd)).toBe("1500000");

      const usd = parseDecimalToMoney("123.45", "USD");
      expect(usd).toEqual({ minor: "12345", currency: "USD" });
      expect(formatMoneyToDecimal(usd)).toBe("123.45");

      const zero = zeroMoney("VND");
      expect(zero).toEqual({ minor: "0", currency: "VND" });
    });
  });

  // -------------------------------------------------------------
  // 2. Posting Guard & Period Locks (F07)
  // -------------------------------------------------------------
  describe("Posting Guard & Period Locks (F07)", () => {
    it("blocks confirming documents and posting transactions in a CLOSED accounting period", async () => {
      const { workspaceId, userId, authorization } = await makeAuthedWorkspace(
        "Closed Period Ws"
      );

      // Mở kỳ tháng 1/2026
      const period = await openAccountingPeriodService(
        {
          workspaceId,
          startDate: "2026-01-01",
          endDate: "2026-01-31",
        },
        authorization
      );

      // Đóng kỳ tháng 1/2026
      await closeAccountingPeriodService(period.id, authorization);

      // 1. Cố gắng ghi transaction vào kỳ đã đóng (2026-01-15) -> BỊ CHẶN
      await expect(
        recordFinancialTransactionService({
          workspaceId,
          transactionDate: "2026-01-15",
          description: "Expense in closed period",
          amount: "500000",
          direction: "OUT",
          authorization,
        })
      ).rejects.toThrow(/PERIOD_CLOSED/);

      // 2. Draft document vẫn có thể soạn trước
      const draftDoc = await createDraftDocumentService({
        workspaceId: BigInt(workspaceId),
        documentType: "PAYMENT",
        number: "PC-001",
        documentDate: "2026-01-20",
        amount: "1000000",
        description: "Payment draft",
      });
      expect(draftDoc.status).toBe("DRAFT");

      // 3. Cố gắng confirm document trong kỳ đã đóng -> BỊ CHẶN
      await expect(
        confirmAccountingDocumentService({
          documentId: BigInt(draftDoc.id),
          workspaceId: BigInt(workspaceId),
          confirmedBy: BigInt(userId),
        })
      ).rejects.toThrow(/PERIOD_CLOSED/);
    });

    it("allows posting and confirming in an OPEN accounting period", async () => {
      const { workspaceId, userId, authorization } = await makeAuthedWorkspace(
        "Open Period Ws"
      );

      // Mở kỳ tháng 2/2026
      await openAccountingPeriodService(
        {
          workspaceId,
          startDate: "2026-02-01",
          endDate: "2026-02-28",
        },
        authorization
      );

      // Ghi transaction vào kỳ mở -> THÀNH CÔNG
      const txn = await recordFinancialTransactionService({
        workspaceId,
        transactionDate: "2026-02-15",
        description: "Valid open period txn",
        amount: "2000000",
        direction: "IN",
        authorization,
      });
      expect(txn.id).toBeDefined();

      // Soạn và confirm document trong kỳ mở -> THÀNH CÔNG
      const draftDoc = await createDraftDocumentService({
        workspaceId: BigInt(workspaceId),
        documentType: "RECEIPT",
        number: "PT-001",
        documentDate: "2026-02-15",
        amount: "2000000",
        description: "Valid open period doc",
      });

      const confirmedDoc = await confirmAccountingDocumentService({
        documentId: BigInt(draftDoc.id),
        workspaceId: BigInt(workspaceId),
        confirmedBy: BigInt(userId),
      });
      expect(confirmedDoc.status).toBe("CONFIRMED");
    });

    it("blocks posting to dates outside any open period once periods are active", async () => {
      const { workspaceId, authorization } = await makeAuthedWorkspace(
        "Active Periods Ws"
      );

      // Mở kỳ tháng 3/2026
      await openAccountingPeriodService(
        {
          workspaceId,
          startDate: "2026-03-01",
          endDate: "2026-03-31",
        },
        authorization
      );

      // Ghi transaction ngày 2026-04-15 (chưa mở kỳ tháng 4) -> BỊ CHẶN
      await expect(
        recordFinancialTransactionService({
          workspaceId,
          transactionDate: "2026-04-15",
          description: "Out of bounds date",
          amount: "100000",
          direction: "OUT",
          authorization,
        })
      ).rejects.toThrow(/NO_OPEN_PERIOD/);
    });
  });

  // -------------------------------------------------------------
  // 3. Concurrent Reconciliation Proposal Claim (F08)
  // -------------------------------------------------------------
  describe("Reconciliation Concurrency & Atomic Claim (F08)", () => {
    it("allows only ONE proposal to claim a bank transaction when two proposals race concurrently", async () => {
      const { workspaceId, userId, authorization } = await makeAuthedWorkspace(
        "Recon Race Ws"
      );
      const wsBig = BigInt(workspaceId);

      // Mở kỳ kế toán để có thể confirm documents
      await openAccountingPeriodService(
        {
          workspaceId,
          startDate: "2026-01-01",
          endDate: "2026-12-31",
        },
        authorization
      );

      // 1. Tạo Bank connection và 1 Bank transaction (UNRECONCILED)
      const conn = await createBankConnectionService({
        workspaceId: wsBig,
        provider: "cas",
        secretRef: "secret://cosa-connectors/cas/test1",
      });

      const bankTxnId = generateSnowflake();
      await db.insert(bankTransactions).values({
        id: bankTxnId,
        workspaceId: wsBig,
        bankConnectionId: BigInt(conn.id),
        externalTransactionId: `bank_txn_race_${Date.now()}`,
        postedAt: new Date("2026-05-15"),
        amount: "5000000.00",
        currency: "VND",
        direction: "IN",
        description: "Payment from customer X",
        status: "UNRECONCILED",
      });

      // 2. Tạo 2 Accounting documents khác nhau
      const doc1 = await createDraftDocumentService({
        workspaceId: wsBig,
        documentType: "INVOICE",
        number: "INV-001",
        documentDate: "2026-05-10",
        amount: "5000000",
        description: "Invoice 1",
      });
      const doc2 = await createDraftDocumentService({
        workspaceId: wsBig,
        documentType: "INVOICE",
        number: "INV-002",
        documentDate: "2026-05-12",
        amount: "5000000",
        description: "Invoice 2",
      });

      // 3. Tạo 2 reconciliation proposals cùng nhắm tới bank transaction này
      const prop1 = await proposeReconciliationService({
        workspaceId: wsBig,
        bankTransactionId: bankTxnId,
        accountingDocumentId: BigInt(doc1.id),
        confidence: 0.95,
      });

      const prop2 = await proposeReconciliationService({
        workspaceId: wsBig,
        bankTransactionId: bankTxnId,
        accountingDocumentId: BigInt(doc2.id),
        confidence: 0.90,
      });

      // 4. Hai connection / request đua nhau accept proposal đồng thời
      const results = await Promise.allSettled([
        acceptReconciliationProposalService({
          proposalId: BigInt(prop1.id),
          workspaceId: wsBig,
          acceptedBy: BigInt(userId),
        }),
        acceptReconciliationProposalService({
          proposalId: BigInt(prop2.id),
          workspaceId: wsBig,
          acceptedBy: BigInt(userId),
        }),
      ]);

      // Kiểm tra: Đúng 1 thành công, 1 thất bại
      const fulfilled = results.filter((r) => r.status === "fulfilled");
      const rejected = results.filter((r) => r.status === "rejected");

      expect(fulfilled).toHaveLength(1);
      expect(rejected).toHaveLength(1);

      // Proposal bị reject phải là do lỗi đã match / không còn UNRECONCILED
      const rejectedError = (rejected[0] as PromiseRejectedResult).reason;
      expect(String(rejectedError)).toMatch(/BANK_TRANSACTION_ALREADY_MATCHED|UNRECONCILED/);

      // 5. Kiểm tra trạng thái trong DB:
      // Bank transaction phải là MATCHED và chỉ trỏ tới duy nhất 1 document
      const [bankRow] = await db
        .select()
        .from(bankTransactions)
        .where(eq(bankTransactions.id, bankTxnId));

      expect(bankRow.status).toBe("MATCHED");
      expect(bankRow.matchedAccountingDocumentId).toBeDefined();

      // Proposal thua cuộc PHẢI VẪN LÀ PENDING (không bị đổi thành ACCEPTED)
      const winningProposalId = (fulfilled[0] as PromiseFulfilledResult<any>).value.id;
      const losingProposalId = winningProposalId === prop1.id ? prop2.id : prop1.id;

      const [losingPropRow] = await db
        .select()
        .from(documentReconciliationProposals)
        .where(eq(documentReconciliationProposals.id, BigInt(losingProposalId)));

      expect(losingPropRow.status).toBe("PENDING");
    });
  });

  // -------------------------------------------------------------
  // 4. Currency Separation & Operating Burn Integrity (F09)
  // -------------------------------------------------------------
  describe("Currency Separation & Burn Integrity (F09)", () => {
    it("computes snapshot strictly per currency and excludes internal transfers & capital from operating burn", () => {
      const txns = [
        // Operating revenue (VND)
        { amount: "10000000", direction: "IN", postedAt: "2026-08-01T00:00:00Z", currency: "VND", category: "REVENUE" },
        // Operating expense (VND)
        { amount: "2000000", direction: "OUT", postedAt: "2026-08-10T00:00:00Z", currency: "VND", category: "OPERATING" },
        // Internal transfer (VND) - Không làm tăng operating burn!
        { amount: "5000000", direction: "OUT", postedAt: "2026-08-15T00:00:00Z", currency: "VND", category: "INTERNAL_TRANSFER" },
        // Capital contribution (VND) - Không được tính là operating revenue!
        { amount: "20000000", direction: "IN", postedAt: "2026-08-20T00:00:00Z", currency: "VND", category: "CAPITAL_CONTRIBUTION" },
        // USD transactions - Tuyệt đối không cộng vào VND!
        { amount: "500", direction: "IN", postedAt: "2026-08-05T00:00:00Z", currency: "USD", category: "REVENUE" },
        { amount: "100", direction: "OUT", postedAt: "2026-08-12T00:00:00Z", currency: "USD", category: "OPERATING" },
      ];

      // 1. Tính snapshot cho VND
      const vndSnap = computeSnapshot(txns, {
        snapshotDate: "2026-08-25",
        openingBalance: 0,
        burnWindowMonths: 1,
        currency: "VND",
      });

      // Total lifetime cash in VND: 10M + 20M = 30M
      expect(vndSnap.cashInLifetime).toBe(30_000_000);
      // Total lifetime cash out VND: 2M + 5M = 7M
      expect(vndSnap.cashOutLifetime).toBe(7_000_000);
      // Current cash = 30M - 7M = 23M
      expect(vndSnap.currentCash).toBe(23_000_000);

      // Period net burn chỉ tính operating: OUT (2M) - IN (10M) = -8M (cashflow positive)
      // INTERNAL_TRANSFER (5M OUT) và CAPITAL_CONTRIBUTION (20M IN) bị loại trừ khỏi burn!
      expect(vndSnap.periodNetBurn).toBe(-8_000_000);
      expect(vndSnap.cashFlowPositive).toBe(true);

      // 2. Tính snapshot cho USD
      const usdSnap = computeSnapshot(txns, {
        snapshotDate: "2026-08-25",
        openingBalance: 0,
        burnWindowMonths: 1,
        currency: "USD",
      });

      expect(usdSnap.cashInLifetime).toBe(500);
      expect(usdSnap.cashOutLifetime).toBe(100);
      expect(usdSnap.currentCash).toBe(400);
      expect(usdSnap.periodNetBurn).toBe(100 - 500);
    });

    it("persists entity and currency scoped snapshots in database", async () => {
      const { workspaceId } = await makeAuthedWorkspace("Snapshot Scope Ws");
      const wsBig = BigInt(workspaceId);

      const conn = await createBankConnectionService({
        workspaceId: wsBig,
        provider: "cas",
        secretRef: "secret://cosa-connectors/cas/test2",
      });

      // Insert 1 VND transaction và 1 USD transaction vào DB
      await db.insert(bankTransactions).values([
        {
          id: generateSnowflake(),
          workspaceId: wsBig,
          bankConnectionId: BigInt(conn.id),
          externalTransactionId: `ext_vnd_${Date.now()}`,
          postedAt: new Date("2026-08-10"),
          amount: "15000000.00",
          currency: "VND",
          direction: "IN",
          description: "Contract payment VND",
          status: "UNRECONCILED",
        },
        {
          id: generateSnowflake(),
          workspaceId: wsBig,
          bankConnectionId: BigInt(conn.id),
          externalTransactionId: `ext_usd_${Date.now()}`,
          postedAt: new Date("2026-08-12"),
          amount: "1000.00",
          currency: "USD",
          direction: "IN",
          description: "Contract payment USD",
          status: "UNRECONCILED",
        },
      ]);

      // Lưu snapshot VND
      const savedVnd = await calculateAndSaveSnapshotService({
        workspaceId: wsBig,
        snapshotDate: "2026-08-31",
        currency: "VND",
      });
      expect(savedVnd.currency).toBe("VND");
      expect(parseFloat(savedVnd.cashIn)).toBe(15000000);

      // Lưu snapshot USD
      const savedUsd = await calculateAndSaveSnapshotService({
        workspaceId: wsBig,
        snapshotDate: "2026-08-31",
        currency: "USD",
      });
      expect(savedUsd.currency).toBe("USD");
      expect(parseFloat(savedUsd.cashIn)).toBe(1000);
    });

    it("computes cash/burn per legal entity instead of pooling across all entities in the workspace (IA12)", async () => {
      const { workspaceId } = await makeAuthedWorkspace("Multi-Entity Snapshot Ws");
      const wsBig = BigInt(workspaceId);

      const entityA = generateSnowflake();
      const entityB = generateSnowflake();

      const connA = await createBankConnectionService({
        workspaceId: wsBig,
        provider: "cas",
        secretRef: "secret://cosa-connectors/cas/entity-a",
      });
      await db
        .update(bankConnections)
        .set({ legalEntityId: entityA })
        .where(eq(bankConnections.id, BigInt(connA.id)));

      const connB = await createBankConnectionService({
        workspaceId: wsBig,
        provider: "cas",
        secretRef: "secret://cosa-connectors/cas/entity-b",
      });
      await db
        .update(bankConnections)
        .set({ legalEntityId: entityB })
        .where(eq(bankConnections.id, BigInt(connB.id)));

      // Entity A nhận 10,000,000 VND; Entity B nhận 3,000,000 VND — cùng
      // workspace, cùng ngày, cùng currency.
      await db.insert(bankTransactions).values([
        {
          id: generateSnowflake(),
          workspaceId: wsBig,
          bankConnectionId: BigInt(connA.id),
          externalTransactionId: `ext_a_${Date.now()}`,
          postedAt: new Date("2026-08-10"),
          amount: "10000000.00",
          currency: "VND",
          direction: "IN",
          description: "Entity A revenue",
          status: "UNRECONCILED",
        },
        {
          id: generateSnowflake(),
          workspaceId: wsBig,
          bankConnectionId: BigInt(connB.id),
          externalTransactionId: `ext_b_${Date.now()}`,
          postedAt: new Date("2026-08-10"),
          amount: "3000000.00",
          currency: "VND",
          direction: "IN",
          description: "Entity B revenue",
          status: "UNRECONCILED",
        },
      ]);

      const snapshotA = await calculateAndSaveSnapshotService({
        workspaceId: wsBig,
        legalEntityId: entityA,
        snapshotDate: "2026-08-31",
        currency: "VND",
      });
      expect(snapshotA.legalEntityId).toBe(String(entityA));
      expect(parseFloat(snapshotA.cashIn)).toBe(10000000);

      const snapshotB = await calculateAndSaveSnapshotService({
        workspaceId: wsBig,
        legalEntityId: entityB,
        snapshotDate: "2026-08-31",
        currency: "VND",
      });
      expect(snapshotB.legalEntityId).toBe(String(entityB));
      expect(parseFloat(snapshotB.cashIn)).toBe(3000000);

      // Cả 2 snapshot cùng tồn tại (không ghi đè nhau qua unique constraint —
      // migration 38 thêm entity vào unique key).
      const rows = await db
        .select()
        .from(schema.financialSnapshots)
        .where(
          and(
            eq(schema.financialSnapshots.workspaceId, wsBig),
            eq(schema.financialSnapshots.snapshotDate, "2026-08-31" as unknown as string),
            eq(schema.financialSnapshots.currency, "VND")
          )
        );
      expect(rows.length).toBe(2);
    });
  });
});
