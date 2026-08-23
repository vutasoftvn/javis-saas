const EPOCH = 1704067200000n; // 2024-01-01 00:00:00 UTC
const NODE_ID = BigInt(Math.floor(Math.random() * 1024)); // Randomized 10-bit node ID (0-1023) to prevent worker collisions

let sequence = BigInt(Math.floor(Math.random() * 64));
let lastTimestamp = -1n;

export function generateSnowflake(): bigint {
  let timestamp = BigInt(Date.now());

  if (timestamp === lastTimestamp) {
    sequence = (sequence + 1n) & 4095n;
    if (sequence === 0n) {
      while (timestamp <= lastTimestamp) {
        timestamp = BigInt(Date.now());
      }
    }
  } else if (timestamp > lastTimestamp) {
    sequence = (sequence + 1n) & 4095n;
  } else {
    timestamp = lastTimestamp;
    sequence = (sequence + 1n) & 4095n;
  }

  lastTimestamp = timestamp;

  return (
    ((timestamp - EPOCH) << 22n) |
    (NODE_ID << 12n) |
    sequence
  );
}

export function generateSnowflakeStr(): string {
  return generateSnowflake().toString();
}
