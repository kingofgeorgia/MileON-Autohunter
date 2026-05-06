"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { LogOut, User } from "lucide-react";
import { Button } from "@/components/ui/button";

interface NavbarAuthControlsProps {
  locale: string;
}

export function NavbarAuthControls({ locale }: NavbarAuthControlsProps) {
  const t = useTranslations("nav");
  const router = useRouter();
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  useEffect(() => {
    setIsLoggedIn(!!localStorage.getItem("access_token"));
  }, []);

  function handleLogout() {
    localStorage.removeItem("access_token");
    setIsLoggedIn(false);
    router.push(`/${locale}/login`);
  }

  if (isLoggedIn) {
    return (
      <Button variant="ghost" size="sm" onClick={handleLogout}>
        <LogOut className="h-4 w-4 mr-1" />
        {t("logout")}
      </Button>
    );
  }

  return (
    <div className="flex gap-1">
      <Button variant="ghost" size="sm" asChild>
        <Link href={`/${locale}/login`}>
          <User className="h-4 w-4 mr-1" />
          {t("login")}
        </Link>
      </Button>
      <Button size="sm" asChild>
        <Link href={`/${locale}/register`}>{t("register")}</Link>
      </Button>
    </div>
  );
}