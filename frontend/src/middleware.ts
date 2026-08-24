import { defineMiddleware } from "astro:middleware";

const baseHeaders: Record<string, string> = {
  "X-Content-Type-Options": "nosniff",
  "X-Frame-Options": "DENY",
  "Referrer-Policy": "strict-origin-when-cross-origin",
  "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
  "Cross-Origin-Opener-Policy": "same-origin",
};

const isProd =
  typeof process !== "undefined" && process.env.NODE_ENV === "production";

export const onRequest = defineMiddleware(async (context, next) => {
  const response = await next();
  for (const [name, value] of Object.entries(baseHeaders)) {
    response.headers.set(name, value);
  }
  if (isProd) {
    response.headers.set(
      "Strict-Transport-Security",
      "max-age=31536000",
    );
  }
  return response;
});
