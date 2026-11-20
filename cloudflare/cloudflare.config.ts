export default {
  name: "clubturistic",
  main: "worker.js",
  compatibilityDate: "2026-11-20",
  compatibilityFlags: ["nodejs_compat"],
  observability: {
    enabled: true,
    logs: { enabled: true, headSamplingRate: 1 },
    traces: { enabled: true, headSamplingRate: 0.01 },
  },
  bindings: {
    DB: { type: "d1", id: "785be804-a402-4bb0-ad6f-38ad632e45e7" },
    MEDIA_KV: { type: "kv_namespace", id: "36c56dede5934239a6853eb52f89195d" },
  },
};
