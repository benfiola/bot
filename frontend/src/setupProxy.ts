const { createProxyMiddleware } = require("http-proxy-middleware");
const { Express } = require("express");

const host = process.env.HOST || "http://localhost:8080"

module.exports = function(app: Express) {
    app.use(
        "/api",
        {
            changeOrigin: true,
            target: host
        }
    )
}