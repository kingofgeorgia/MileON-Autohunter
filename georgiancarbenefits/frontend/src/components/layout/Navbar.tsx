"use client";

import Link from "next/link";
import dynamic from "next/dynamic";
import { useTranslations, useLocale } from "next-intl";
import { usePathname, useRouter } from "next/navigation";
import { Car } from "lucide-react";

const NavbarAuthControls = dynamic(
  () => import("./NavbarAuthControls").then((mod) => mod.NavbarAuthControls),
  {
    ssr: false,
    loading: () => <div className="h-7 w-40" />,
  },
);

export function Navbar() {
  const t = useTranslations("nav");
  const locale = useLocale();
  const pathname = usePathname();
  const router = useRouter();

  function switchLocale(newLocale: string) {
    // Replace current locale segment in path
    const segments = pathname.split("/");
    segments[1] = newLocale;
    router.push(segments.join("/"));
  }

  return (
    <header className="border-b bg-white sticky top-0 z-10">
      <div className="container mx-auto px-4 flex items-center justify-between h-14">
        <Link href={`/${locale}`} className="flex items-center gap-2 font-semibold text-lg">
          <Car className="h-5 w-5 text-green-600" />
          <span>GeoCarBenefits</span>
        </Link>

        <nav className="hidden md:flex items-center gap-6 text-sm">
          <Link href={`/${locale}`} className="hover:text-green-600 transition-colors">
            {t("calculator")}
          </Link>
          <Link href={`/${locale}/catalog`} className="hover:text-green-600 transition-colors">
            {t("catalog")}
          </Link>
          <Link href={`/${locale}/history`} className="hover:text-green-600 transition-colors">
            {t("history")}
          </Link>
        </nav>

        <div className="flex items-center gap-2">
          {/* Language switcher */}
          <div className="flex gap-1 text-xs border rounded-md overflow-hidden">
            {(["ru", "en", "ka"] as const).map((loc) => (
              <button
                key={loc}
                onClick={() => switchLocale(loc)}
                className={`px-2 py-1 uppercase transition-colors ${
                  locale === loc
                    ? "bg-green-600 text-white"
                    : "hover:bg-gray-100"
                }`}
              >
                {loc}
              </button>
            ))}
          </div>
          <NavbarAuthControls locale={locale} />
        </div>
      </div>
    </header>
  );
}
