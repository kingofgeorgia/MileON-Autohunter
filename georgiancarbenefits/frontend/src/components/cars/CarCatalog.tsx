"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { useQuery } from "@tanstack/react-query";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ExternalLink } from "lucide-react";
import { api } from "@/lib/api";
import type { CarListing, CarMakeOption, CarModelOption } from "@/lib/types";
import { ListingImageGallery } from "./ListingImageGallery";

const ALL_MAKES = "__all_makes__";
const ALL_MODELS = "__all_models__";

function formatCarTitle(car: CarListing) {
  const parts = [car.make, car.model];

  if (car.car_model && car.car_model !== car.model) {
    parts.push(car.car_model);
  }

  parts.push(String(car.year));
  return parts.join(" ");
}

function fmt(n: number) {
  return new Intl.NumberFormat("ru-RU", { style: "currency", currency: "RUB", maximumFractionDigits: 0 }).format(n);
}

export function CarCatalog() {
  const t = useTranslations("catalog");

  const [filters, setFilters] = useState({
    make_id: "",
    model_id: "",
    year_from: "",
    year_to: "",
    price_usd_to: "",
    logistics_cost_rub: "170000",
    page: "1",
  });
  const [submitted, setSubmitted] = useState(false);

  const params = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => { if (v) params.set(k, v); });

  const { data, isFetching } = useQuery<CarListing[]>({
    queryKey: ["cars", filters],
    queryFn: () => api.get(`/cars/search?${params}`).then((r) => r.data),
    enabled: submitted,
  });

  const { data: makes = [] } = useQuery<CarMakeOption[]>({
    queryKey: ["car-makes"],
    queryFn: () => api.get("/cars/makes").then((r) => r.data),
  });

  const { data: models = [], isFetching: isFetchingModels } = useQuery<CarModelOption[]>({
    queryKey: ["car-models", filters.make_id],
    queryFn: () => api.get(`/cars/models?make_id=${filters.make_id}`).then((r) => r.data),
    enabled: Boolean(filters.make_id),
  });

  useEffect(() => {
    setFilters((current) => {
      if (!current.model_id) {
        return current;
      }

      const hasSelectedModel = models.some((model) => String(model.model_id) === current.model_id);
      if (hasSelectedModel) {
        return current;
      }

      return { ...current, model_id: "" };
    });
  }, [models]);

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    setFilters((f) => ({ ...f, [e.target.name]: e.target.value }));
  }

  function handleMakeChange(value: string) {
    setFilters((current) => ({
      ...current,
      make_id: value === ALL_MAKES ? "" : value,
      model_id: "",
      page: "1",
    }));
  }

  function handleModelChange(value: string) {
    setFilters((current) => ({
      ...current,
      model_id: value === ALL_MODELS ? "" : value,
      page: "1",
    }));
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">{t("title")}</h1>

      <Card>
        <CardContent className="pt-4">
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
            <div>
              <Label>{t("make")}</Label>
              <Select value={filters.make_id || ALL_MAKES} onValueChange={handleMakeChange}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder={t("make")} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={ALL_MAKES}>{t("allMakes")}</SelectItem>
                  {makes.map((make) => (
                    <SelectItem key={make.man_id} value={String(make.man_id)}>
                      {make.title}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>{t("model")}</Label>
              <Select
                value={filters.model_id || ALL_MODELS}
                onValueChange={handleModelChange}
                disabled={!filters.make_id || isFetchingModels}
              >
                <SelectTrigger className="w-full">
                  <SelectValue placeholder={t("model")} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={ALL_MODELS}>{t("allModels")}</SelectItem>
                  {models.map((model) => (
                    <SelectItem key={model.model_id} value={String(model.model_id)}>
                      {model.group_title ? `${model.group_title} · ${model.title}` : model.title}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>{t("yearFrom")}</Label>
              <Input name="year_from" type="number" onChange={handleChange} value={filters.year_from} />
            </div>
            <div>
              <Label>{t("yearTo")}</Label>
              <Input name="year_to" type="number" onChange={handleChange} value={filters.year_to} />
            </div>
            <div>
              <Label>{t("priceUsdTo")}</Label>
              <Input name="price_usd_to" type="number" onChange={handleChange} value={filters.price_usd_to} />
            </div>
            <div>
              <Label>{t("logisticsCost")}</Label>
              <Input name="logistics_cost_rub" type="number" onChange={handleChange} value={filters.logistics_cost_rub} />
            </div>
          </div>
          {filters.make_id && isFetchingModels && (
            <p className="mt-3 text-sm text-gray-500">{t("loadingModels")}</p>
          )}
          <Button className="mt-4" onClick={() => setSubmitted(true)} disabled={isFetching}>
            {isFetching ? "..." : t("search")}
          </Button>
        </CardContent>
      </Card>

      {data && data.length === 0 && (
        <p className="text-gray-500">{t("noResults")}</p>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {data?.map((car) => (
          <Card key={car.car_id} className="overflow-hidden">
            <ListingImageGallery
              imageUrls={car.image_urls?.length ? car.image_urls : car.image_url ? [car.image_url] : []}
              alt={formatCarTitle(car)}
              aspectClassName="aspect-[16/10]"
              thumbnailClassName="h-12 w-16"
            />
            <CardContent className="p-4 space-y-2">
              <div className="flex justify-between items-start">
                <div>
                  <p className="font-semibold">{formatCarTitle(car)}</p>
                  <p className="text-sm text-gray-500">{car.engine_volume_cc} сс</p>
                </div>
                <Badge variant="outline">${car.price_usd.toLocaleString()}</Badge>
              </div>
              {car.mileage_km != null && (
                <p className="text-xs text-gray-400">{t("mileage")}: {car.mileage_km.toLocaleString()} {t("km")}</p>
              )}
              {car.estimated_total_rub != null && (
                <p className="text-sm font-medium text-green-700">
                  {t("estimatedTotal")}: {fmt(car.estimated_total_rub)}
                </p>
              )}
              <a
                href={car.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 text-xs text-blue-600 hover:underline"
              >
                {t("viewOnMyauto")} <ExternalLink className="h-3 w-3" />
              </a>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
