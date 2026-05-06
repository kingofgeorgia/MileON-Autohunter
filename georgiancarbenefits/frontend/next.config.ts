import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin("./src/i18n/request.ts");

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "**.myauto.ge" },
      { protocol: "https", hostname: "static.myauto.ge" },
    ],
  },
};

export default withNextIntl(nextConfig);
