"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import type { CalculationOut } from "@/lib/types";

function fmt(n: number) {
  return new Intl.NumberFormat("ru-RU", { style: "currency", currency: "RUB", maximumFractionDigits: 0 }).format(n);
}

export function HistoryList() {
  const t = useTranslations("history");
  const tErr = useTranslations("errors");
  const qc = useQueryClient();

  const { data, isLoading } = useQuery<CalculationOut[]>({
    queryKey: ["history"],
    queryFn: () => api.get("/history/").then((r) => r.data),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/history/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["history"] });
      toast.success("Расчёт удалён");
    },
    onError: () => toast.error(tErr("generic")),
  });

  if (isLoading) return <p className="text-gray-400">Загрузка...</p>;
  if (!data || data.length === 0) return <p className="text-gray-500">{t("empty")}</p>;

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">{t("title")}</h1>
      <Card>
        <CardContent className="p-0 overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t("date")}</TableHead>
                <TableHead>USD</TableHead>
                <TableHead>{t("year")}</TableHead>
                <TableHead>{t("engine")} (сс)</TableHead>
                <TableHead>{t("horsePower")}</TableHead>
                <TableHead>{t("total")}</TableHead>
                <TableHead></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.map((c) => (
                <TableRow key={c.id}>
                  <TableCell className="text-sm text-gray-500">
                    {new Date(c.created_at).toLocaleDateString("ru-RU")}
                  </TableCell>
                  <TableCell>${c.car_price_usd.toLocaleString()}</TableCell>
                  <TableCell>{c.car_year}</TableCell>
                  <TableCell>{c.engine_volume_cc}</TableCell>
                  <TableCell>{c.horse_power ?? "-"}</TableCell>
                  <TableCell className="font-medium">{fmt(c.total_cost_rub)}</TableCell>
                  <TableCell>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => deleteMutation.mutate(c.id)}
                      disabled={deleteMutation.isPending}
                    >
                      <Trash2 className="h-4 w-4 text-red-500" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
