"use client";

import { useEffect, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useTranslations } from "next-intl";
import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ExternalLink, Link2, X } from "lucide-react";
import { api } from "@/lib/api";
import type { CalculatorRequest, CalculatorResult, CarListing } from "@/lib/types";
import { CalculatorResults } from "./CalculatorResults";
import { CurrencyRatesWidget } from "./CurrencyRatesWidget";
import { ListingImageGallery } from "@/components/cars/ListingImageGallery";

const currentYear = new Date().getFullYear();
const HP_TO_KW = 0.73549875;
const DEFAULT_LOGISTICS_RUB = 170000;
const SUV_AND_CROSSOVER_LOGISTICS_RUB = 200000;
const SUV_AND_CROSSOVER_CATEGORY_IDS = new Set([5, 66]);
const AUTO_RU_MAKE_SLUG_OVERRIDES: Record<string, string> = {
  "mercedes-benz": "mercedes",
  "mercedes benz": "mercedes",
  "land rover": "land_rover",
  "alfa romeo": "alfa_romeo",
  "aston martin": "aston_martin",
  "great wall": "great_wall",
  "rolls-royce": "rolls_royce",
  "rolls royce": "rolls_royce",
};
type PowertrainKindValue = CalculatorRequest["powertrain_kind"] | CarListing["powertrain_kind"] | null | undefined;

function formatCarTitle(car: CarListing) {
  const parts = [car.make, car.model];

  if (car.car_model && car.car_model !== car.model) {
    parts.push(car.car_model);
  }

  parts.push(String(car.year));
  return parts.join(" ");
}

function isElectricPowertrain(powertrainKind: PowertrainKindValue) {
  return powertrainKind === "EV";
}

function convertHorsePowerToKw(horsePower: number) {
  return Number((horsePower * HP_TO_KW).toFixed(2));
}

function convertKwToHorsePower(powerKw: number) {
  return Number((powerKw / HP_TO_KW).toFixed(2));
}

function resolveDefaultLogisticsCostRub(categoryId: number | null | undefined) {
  return SUV_AND_CROSSOVER_CATEGORY_IDS.has(Number(categoryId))
    ? SUV_AND_CROSSOVER_LOGISTICS_RUB
    : DEFAULT_LOGISTICS_RUB;
}

function parseOptionalNumber(value: unknown) {
  if (value == null || value === "") {
    return null;
  }

  const numericValue = Number(value);
  return Number.isFinite(numericValue) ? numericValue : value;
}

function toAutoRuSlugPart(value: string) {
  return value
    .toLowerCase()
    .replace(/[+]/g, " plus ")
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .replace(/_+/g, "_");
}

function resolveAutoRuMakeSlug(make: string) {
  const normalizedMake = make.trim().toLowerCase();
  return AUTO_RU_MAKE_SLUG_OVERRIDES[normalizedMake] ?? toAutoRuSlugPart(make);
}

function resolveAutoRuModelSlug(car: CarListing) {
  const modelSource = car.model || car.car_model || "";
  return toAutoRuSlugPart(modelSource);
}

function buildAutoRuAnalogSearchUrl(car: CarListing, options: {
  carYear: number;
  engineVolumeCc: number;
  horsePower: number | null | undefined;
  powertrainKind: PowertrainKindValue;
}) {
  const params = new URLSearchParams();
  const searchParts = [car.make, car.model];
  const makeSlug = resolveAutoRuMakeSlug(car.make);
  const modelSlug = resolveAutoRuModelSlug(car);

  if (car.car_model && car.car_model !== car.model) {
    searchParts.push(car.car_model);
  }

  if (options.powertrainKind === "EV") {
    searchParts.push("электромобиль");
  } else if (options.powertrainKind === "OTHER_HYBRID" || options.powertrainKind === "SERIES_HYBRID") {
    searchParts.push("гибрид");
  }

  params.set("text", searchParts.join(" "));
  params.set("year_from", String(Math.max(1990, options.carYear - 1)));
  params.set("year_to", String(options.carYear + 1));

  if (options.engineVolumeCc > 0) {
    const engineLiters = options.engineVolumeCc / 1000;
    params.set("displacement_from", String(Math.max(0, engineLiters - 0.3).toFixed(1)));
    params.set("displacement_to", String((engineLiters + 0.3).toFixed(1)));
  }

  if (options.horsePower && options.horsePower > 0) {
    params.set("power_from", String(Math.max(1, Math.round(options.horsePower - 30))));
    params.set("power_to", String(Math.round(options.horsePower + 30)));
  }

  return `https://auto.ru/cars/used/sale/${makeSlug}/${modelSlug}/?${params.toString()}`;
}

function isEngineVolumeRequired(powertrainKind: PowertrainKindValue) {
  return !isElectricPowertrain(powertrainKind);
}

export function Calculator() {
  const t = useTranslations("calculator");
  const tErr = useTranslations("errors");

  const [carUrl, setCarUrl] = useState("");
  const [loadedCar, setLoadedCar] = useState<CarListing | null>(null);

  const urlMutation = useMutation({
    mutationFn: (url: string) =>
      api.post<CarListing>("/cars/from-url", { url }).then((r) => r.data),
    onSuccess: (car) => {
      setLoadedCar(car);
      setValue("car_price_usd", car.price_usd);
      setValue("engine_volume_cc", car.engine_volume_cc);
      setValue("car_year", car.year);
      setValue("horse_power", car.horse_power ?? null);
      setValue("fuel_type", car.fuel_type ?? "");
      setValue("powertrain_kind", car.powertrain_kind ?? "ICE");
      setValue("logistics_cost_rub", resolveDefaultLogisticsCostRub(car.category_id));
      toast.success(`${formatCarTitle(car)} — данные загружены`);
    },
    onError: () => toast.error("Не удалось загрузить авто. Проверьте ссылку."),
  });

  const schema = z.object({
    car_price_usd: z.coerce.number().positive(tErr("required")),
    engine_volume_cc: z.coerce.number().int().min(0),
    car_year: z.coerce
      .number()
      .int()
      .min(1990)
      .max(currentYear),
    horse_power: z.coerce.number().positive(tErr("required")),
    fuel_type: z.string().optional(),
    powertrain_kind: z.enum(["ICE", "OTHER_HYBRID", "EV", "SERIES_HYBRID"]).optional().nullable(),
    logistics_cost_rub: z.coerce.number().min(0),
    rf_analog_price_rub: z.preprocess(parseOptionalNumber, z.number().nullable().optional()),
    note: z.preprocess((value) => value === "" ? null : value, z.string().optional().nullable()),
  }).superRefine((data, ctx) => {
    if (isEngineVolumeRequired(data.powertrain_kind) && data.engine_volume_cc <= 0) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["engine_volume_cc"],
        message: tErr("required"),
      });
    }
  });

  type FormData = z.infer<typeof schema>;

  const { register, handleSubmit, formState: { errors }, setValue, watch } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { logistics_cost_rub: DEFAULT_LOGISTICS_RUB, fuel_type: "", powertrain_kind: "ICE" },
  });

  const powertrainKind = watch("powertrain_kind");
  const powerValue = watch("horse_power");
  const engineVolumeValue = watch("engine_volume_cc");
  const carYearValue = watch("car_year");
  const previousPowertrainKindRef = useRef<FormData["powertrain_kind"]>("ICE");
  const previousNonElectricEngineVolumeRef = useRef<number | null>(null);

  const autoRuAnalogSearchUrl = loadedCar
    ? buildAutoRuAnalogSearchUrl(loadedCar, {
        carYear: carYearValue,
        engineVolumeCc: engineVolumeValue,
        horsePower: powerValue,
        powertrainKind,
      })
    : null;

  useEffect(() => {
    const previousPowertrainKind = previousPowertrainKindRef.current;
    const currentPowertrainKind = powertrainKind ?? "ICE";

    if (
      previousPowertrainKind === currentPowertrainKind
      || powerValue == null
      || Number.isNaN(Number(powerValue))
    ) {
      previousPowertrainKindRef.current = currentPowertrainKind;
      return;
    }

    const numericPowerValue = Number(powerValue);
    const convertedPowerValue = previousPowertrainKind === "EV" && currentPowertrainKind !== "EV"
      ? convertKwToHorsePower(numericPowerValue)
      : previousPowertrainKind !== "EV" && currentPowertrainKind === "EV"
        ? convertHorsePowerToKw(numericPowerValue)
        : numericPowerValue;

    if (convertedPowerValue !== numericPowerValue) {
      setValue("horse_power", convertedPowerValue, { shouldDirty: true, shouldValidate: true });
    }

    previousPowertrainKindRef.current = currentPowertrainKind;
  }, [powerValue, powertrainKind, setValue]);

  useEffect(() => {
    if (isEngineVolumeRequired(powertrainKind) && engineVolumeValue > 0) {
      previousNonElectricEngineVolumeRef.current = engineVolumeValue;
    }
  }, [engineVolumeValue, powertrainKind]);

  useEffect(() => {
    const currentPowertrainKind = powertrainKind ?? "ICE";

    if (isElectricPowertrain(currentPowertrainKind)) {
      if (engineVolumeValue !== 0) {
        setValue("engine_volume_cc", 0, { shouldDirty: true, shouldValidate: true });
      }
      return;
    }

    if (engineVolumeValue === 0 && previousNonElectricEngineVolumeRef.current) {
      setValue("engine_volume_cc", previousNonElectricEngineVolumeRef.current, {
        shouldDirty: true,
        shouldValidate: true,
      });
    }
  }, [engineVolumeValue, powertrainKind, setValue]);

  const calcMutation = useMutation({
    mutationFn: (data: CalculatorRequest) =>
      api.post<CalculatorResult>("/calculator/total", data).then((r) => r.data),
    onError: () => toast.error(tErr("generic")),
  });

  const saveMutation = useMutation({
    mutationFn: (data: CalculatorRequest) =>
      api.post("/history/", data),
    onSuccess: () => toast.success("Расчёт сохранён"),
    onError: () => toast.error(tErr("generic")),
  });

  const lastPayloadRef = useRef<CalculatorRequest | null>(null);

  function onInvalid() {
    toast.error(tErr("required"));
  }

  function onSubmit(data: FormData) {
    const normalizedHorsePower = isElectricPowertrain(data.powertrain_kind)
      ? convertKwToHorsePower(data.horse_power)
      : data.horse_power;

    const payload: CalculatorRequest = {
      ...data,
      engine_volume_cc: isElectricPowertrain(data.powertrain_kind) ? 0 : data.engine_volume_cc,
      horse_power: normalizedHorsePower,
      source_make: loadedCar?.make ?? null,
      source_model: loadedCar?.model ?? null,
      source_model_id: loadedCar?.model_id ?? null,
      powertrain_kind: data.powertrain_kind ?? "ICE",
      is_personal_use: true,
      rf_analog_price_rub: data.rf_analog_price_rub ?? null,
      note: data.note ?? null,
    };
    lastPayloadRef.current = payload;
    calcMutation.mutate(payload);
  }

  return (
    <div className="space-y-6">
      <CurrencyRatesWidget />

      <Card>
        <CardHeader>
          <CardTitle>{t("title")}</CardTitle>
        </CardHeader>
        <CardContent>
          {/* URL input for myauto.ge */}
          <div className="mb-5 space-y-2">
            <Label className="flex items-center gap-1">
              <Link2 className="h-4 w-4" /> {t("urlLabel")}
            </Label>
            <div className="flex gap-2">
              <Input
                placeholder={t("urlPlaceholder")}
                value={carUrl}
                onChange={(e) => setCarUrl(e.target.value)}
                className="flex-1"
              />
              <Button
                type="button"
                variant="secondary"
                disabled={!carUrl || urlMutation.isPending}
                onClick={() => urlMutation.mutate(carUrl)}
              >
                {urlMutation.isPending ? "..." : t("urlLoad")}
              </Button>
            </div>
            {loadedCar && (
              <div className="space-y-3 rounded-md border border-green-200 bg-green-50 p-3 text-sm">
                <div className="flex items-start gap-2">
                  <div className="min-w-0 space-y-1">
                    <span className="block text-green-800 font-medium">
                      {formatCarTitle(loadedCar)}
                    </span>
                    {loadedCar.horse_power ? (
                      <span className="block text-xs text-green-700">
                        {isElectricPowertrain(loadedCar.powertrain_kind)
                          ? t("powerKwDetected", { kw: convertHorsePowerToKw(loadedCar.horse_power) })
                          : t("horsePowerDetected", { hp: loadedCar.horse_power })}
                      </span>
                    ) : null}
                  </div>
                  <Badge variant="outline">${loadedCar.price_usd.toLocaleString()}</Badge>
                  <a href={loadedCar.url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline text-xs ml-auto pt-1">
                    myauto.ge ↗
                  </a>
                  <button type="button" onClick={() => { setLoadedCar(null); setCarUrl(""); }}>
                    <X className="h-4 w-4 text-gray-400 hover:text-gray-700" />
                  </button>
                </div>
                {loadedCar.image_urls && loadedCar.image_urls.length > 0 && (
                  <ListingImageGallery
                    imageUrls={loadedCar.image_urls}
                    alt={formatCarTitle(loadedCar)}
                  />
                )}
              </div>
            )}
          </div>

          <form onSubmit={handleSubmit(onSubmit, onInvalid)} className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label>{t("carPriceUsd")}</Label>
              <Input type="number" step="0.01" {...register("car_price_usd")} />
              {errors.car_price_usd && <p className="text-sm text-red-500">{errors.car_price_usd.message}</p>}
            </div>
            <div>
              <Label>{t("engineVolume")}</Label>
              <Input
                type="number"
                {...register("engine_volume_cc")}
                disabled={!isEngineVolumeRequired(powertrainKind)}
                readOnly={!isEngineVolumeRequired(powertrainKind)}
                placeholder={!isEngineVolumeRequired(powertrainKind) ? t("engineVolumeNotRequiredForEv") : undefined}
              />
              {errors.engine_volume_cc && <p className="text-sm text-red-500">{errors.engine_volume_cc.message}</p>}
            </div>
            <div>
              <Label>{t("carYear")}</Label>
              <Input type="number" min={1990} max={currentYear} {...register("car_year")} />
              {errors.car_year && <p className="text-sm text-red-500">{errors.car_year.message}</p>}
            </div>
            <div>
              <Label>{isElectricPowertrain(powertrainKind) ? t("powerKw") : t("horsePower")}</Label>
              <Input type="number" step="0.01" {...register("horse_power")} />
              {errors.horse_power && <p className="text-sm text-red-500">{errors.horse_power.message}</p>}
            </div>
            <div>
              <Label>{t("fuelType")}</Label>
              <Input {...register("fuel_type")} readOnly placeholder={t("fuelTypeAuto")} />
            </div>
            <div>
              <Label>{t("powertrainKind")}</Label>
              <Select
                value={powertrainKind ?? "ICE"}
                onValueChange={(value) => setValue("powertrain_kind", value as FormData["powertrain_kind"], { shouldDirty: true })}
              >
                <SelectTrigger>
                  <SelectValue placeholder={t("powertrainKind")} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ICE">{t("powertrainKinds.ICE")}</SelectItem>
                  <SelectItem value="OTHER_HYBRID">{t("powertrainKinds.OTHER_HYBRID")}</SelectItem>
                  <SelectItem value="EV">{t("powertrainKinds.EV")}</SelectItem>
                  <SelectItem value="SERIES_HYBRID">{t("powertrainKinds.SERIES_HYBRID")}</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>{t("logisticsCost")}</Label>
              <Input type="number" step="1000" {...register("logistics_cost_rub")} />
            </div>
            <div>
              <Label>{t("rfAnalogPrice")}</Label>
              <div className="space-y-2">
                <Input type="number" step="1000" {...register("rf_analog_price_rub")} />
                <div className="flex flex-wrap gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    disabled={!autoRuAnalogSearchUrl}
                    onClick={() => {
                      if (!autoRuAnalogSearchUrl) {
                        return;
                      }
                      window.open(autoRuAnalogSearchUrl, "_blank", "noopener,noreferrer");
                    }}
                  >
                    <ExternalLink className="mr-1 h-4 w-4" />
                    {t("openAutoRuAnalogSearch")}
                  </Button>
                  {loadedCar ? (
                    <span className="text-xs text-gray-500">
                      {t("autoRuAnalogSearchHint")}
                    </span>
                  ) : null}
                </div>
              </div>
            </div>
            <div>
              <Label>{t("note")}</Label>
              <Input {...register("note")} />
            </div>
            <div className="md:col-span-2 flex gap-3">
              <Button type="submit" disabled={calcMutation.isPending}>
                {calcMutation.isPending ? "..." : t("calculate")}
              </Button>
              {calcMutation.data && (
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => lastPayloadRef.current && saveMutation.mutate(lastPayloadRef.current)}
                  disabled={saveMutation.isPending}
                >
                  {t("saveToHistory")}
                </Button>
              )}
            </div>
          </form>
        </CardContent>
      </Card>

      {calcMutation.data && <CalculatorResults result={calcMutation.data} />}
    </div>
  );
}
