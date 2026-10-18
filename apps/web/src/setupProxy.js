// Dev-only: proxy /api to the backend so the site and API share one origin (cookie auth, previews).
const { createProxyMiddleware } = require("http-proxy-middleware");

module.exports = function (app) {
  const target = process.env.KAOS_API_PROXY;
  if (!target) return;
  app.use("/api", createProxyMiddleware({ target, changeOrigin: true }));
};
