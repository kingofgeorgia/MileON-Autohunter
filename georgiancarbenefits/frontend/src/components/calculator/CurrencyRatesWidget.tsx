"use client";

import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api";
import type { CurrencyRates } from "@/lib/types";

export function CurrencyRatesWidget() {
  const t = useTranslations("rates");

  const { data } = useQuery<CurrencyRates>({
    queryKey: ["rates"],
    queryFn: () => api.get("/calculator/rates").then((r) => r.data),
    staleTime: 60 * 60 * 1000, // 1h
    retry: false,
  });

  if (!data) return null;

  return (
    <div className="flex flex-wrap gap-4 text-sm text-gray-600">
      <span className="font-medium text-gray-800">{t("title")}:</span>
      <span>{t("usdRub")}: <strong>{data.usd_to_rub.toFixed(2)}</strong></span>
      <span>{t("eurRub")}: <strong>{data.eur_to_rub.toFixed(2)}</strong></span>
      <span>{t("gelRub")}: <strong>{data.gel_to_rub.toFixed(2)}</strong></span>
    </div>
  );
}
