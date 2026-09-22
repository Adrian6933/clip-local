// Compatibility entry point: the durable API now runs on Python/FastAPI.
process.argv[2] = 'api';
await import('../scripts/start.mjs');
