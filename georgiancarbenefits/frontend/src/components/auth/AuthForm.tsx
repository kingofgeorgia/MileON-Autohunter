"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useTranslations, useLocale } from "next-intl";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import Link from "next/link";
import { api } from "@/lib/api";
import type { TokenResponse } from "@/lib/types";

interface AuthFormProps {
  mode: "login" | "register";
}

export function AuthForm({ mode }: AuthFormProps) {
  const t = useTranslations("auth");
  const tErr = useTranslations("errors");
  const locale = useLocale();
  const router = useRouter();

  const schema = z.object({
    email: z.string().min(1, tErr("required")).email(tErr("invalidEmail")),
    password: z.string().min(8, tErr("minPassword")),
  });

  type FormData = z.infer<typeof schema>;

  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  async function onSubmit(data: FormData) {
    try {
      const endpoint = mode === "login" ? "/auth/login" : "/auth/register";
      const res = await api.post<TokenResponse>(endpoint, data);
      localStorage.setItem("access_token", res.data.access_token);
      router.push(`/${locale}`);
    } catch {
      toast.error(tErr("generic"));
    }
  }

  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>{mode === "login" ? t("loginTitle") : t("registerTitle")}</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div>
              <Label htmlFor="email">{t("email")}</Label>
              <Input id="email" type="email" {...register("email")} />
              {errors.email && <p className="text-sm text-red-500 mt-1">{errors.email.message}</p>}
            </div>
            <div>
              <Label htmlFor="password">{t("password")}</Label>
              <Input id="password" type="password" {...register("password")} />
              {errors.password && <p className="text-sm text-red-500 mt-1">{errors.password.message}</p>}
            </div>
            <Button type="submit" className="w-full" disabled={isSubmitting}>
              {mode === "login" ? t("loginAction") : t("registerAction")}
            </Button>
            <p className="text-sm text-center text-gray-500">
              {mode === "login" ? (
                <>
                  {t("noAccount")}{" "}
                  <Link href={`/${locale}/register`} className="text-green-600 hover:underline">
                    {t("signUp")}
                  </Link>
                </>
              ) : (
                <>
                  {t("hasAccount")}{" "}
                  <Link href={`/${locale}/login`} className="text-green-600 hover:underline">
                    {t("signIn")}
                  </Link>
                </>
              )}
            </p>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
