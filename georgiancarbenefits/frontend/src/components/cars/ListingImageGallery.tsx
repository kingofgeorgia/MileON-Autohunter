"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import { createPortal } from "react-dom";
import { useTranslations } from "next-intl";
import { ChevronLeft, ChevronRight, Expand, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type ListingImageGalleryProps = {
  imageUrls?: string[] | null;
  alt: string;
  className?: string;
  aspectClassName?: string;
  thumbnailClassName?: string;
};

export function ListingImageGallery({
  imageUrls,
  alt,
  className,
  aspectClassName = "aspect-[16/10]",
  thumbnailClassName = "h-16 w-24",
}: ListingImageGalleryProps) {
  const t = useTranslations("gallery");
  const images = imageUrls?.filter(Boolean) ?? [];
  const [activeIndex, setActiveIndex] = useState(0);
  const [isFullscreenOpen, setIsFullscreenOpen] = useState(false);

  useEffect(() => {
    setActiveIndex(0);
    setIsFullscreenOpen(false);
  }, [imageUrls]);

  useEffect(() => {
    if (!isFullscreenOpen) {
      return undefined;
    }

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setIsFullscreenOpen(false);
        return;
      }

      if (event.key === "ArrowLeft") {
        setActiveIndex((current) => (current === 0 ? images.length - 1 : current - 1));
      }

      if (event.key === "ArrowRight") {
        setActiveIndex((current) => (current === images.length - 1 ? 0 : current + 1));
      }
    }

    window.addEventListener("keydown", handleKeyDown);

    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [images.length, isFullscreenOpen]);

  if (images.length === 0) {
    return null;
  }

  function showPrevious() {
    setActiveIndex((current) => (current === 0 ? images.length - 1 : current - 1));
  }

  function showNext() {
    setActiveIndex((current) => (current === images.length - 1 ? 0 : current + 1));
  }

  const fullscreen = isFullscreenOpen && typeof document !== "undefined"
    ? createPortal(
        <div
          className="fixed inset-0 z-[100] bg-black/90 px-4 py-6 sm:px-8"
          onClick={() => setIsFullscreenOpen(false)}
        >
          <button
            type="button"
            aria-label={t("close")}
            className="absolute top-4 right-4 rounded-full bg-white/10 p-2 text-white transition hover:bg-white/20"
            onClick={() => setIsFullscreenOpen(false)}
          >
            <X className="h-5 w-5" />
          </button>

          <div className="mx-auto flex h-full max-w-7xl flex-col justify-center gap-4">
            <div className="relative flex min-h-0 flex-1 items-center justify-center" onClick={(event) => event.stopPropagation()}>
              {images.length > 1 && (
                <Button
                  type="button"
                  variant="secondary"
                  size="icon"
                  className="absolute left-2 top-1/2 z-10 -translate-y-1/2 bg-white/15 text-white hover:bg-white/25"
                  onClick={showPrevious}
                  aria-label={t("previous")}
                >
                  <ChevronLeft />
                </Button>
              )}

              <Image
                src={images[activeIndex]}
                alt={`${alt} ${activeIndex + 1}`}
                width={1600}
                height={1000}
                className="max-h-[78vh] w-auto max-w-full rounded-xl object-contain"
                unoptimized
              />

              {images.length > 1 && (
                <Button
                  type="button"
                  variant="secondary"
                  size="icon"
                  className="absolute right-2 top-1/2 z-10 -translate-y-1/2 bg-white/15 text-white hover:bg-white/25"
                  onClick={showNext}
                  aria-label={t("next")}
                >
                  <ChevronRight />
                </Button>
              )}
            </div>

            {images.length > 1 && (
              <div className="flex gap-2 overflow-x-auto pb-1" onClick={(event) => event.stopPropagation()}>
                {images.map((imageUrl, index) => (
                  <button
                    key={`${imageUrl}-${index}`}
                    type="button"
                    className={cn(
                      "relative h-16 w-24 shrink-0 overflow-hidden rounded-md border border-white/20",
                      index === activeIndex && "border-white"
                    )}
                    aria-label={t("photoNumber", { current: index + 1, total: images.length })}
                    onClick={() => setActiveIndex(index)}
                  >
                    <Image
                      src={imageUrl}
                      alt={`${alt} ${index + 1}`}
                      fill
                      className="object-cover"
                      unoptimized
                    />
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>,
        document.body
      )
    : null;

  return (
    <>
      <div className={cn("space-y-2", className)}>
        <div className="relative overflow-hidden rounded-md border bg-white">
          <button
            type="button"
            className="block w-full text-left"
            onClick={() => setIsFullscreenOpen(true)}
            aria-label={t("open")}
          >
            <div className={cn("relative w-full bg-gray-100", aspectClassName)}>
              <Image
                src={images[activeIndex]}
                alt={alt}
                fill
                className="object-cover"
                unoptimized
              />
            </div>
            <span className="absolute top-2 right-2 inline-flex items-center gap-1 rounded-full bg-black/55 px-2 py-1 text-xs text-white">
              <Expand className="h-3.5 w-3.5" />
              {activeIndex + 1}/{images.length}
            </span>
          </button>

          {images.length > 1 && (
            <>
              <Button
                type="button"
                variant="secondary"
                size="icon-sm"
                className="absolute top-1/2 left-2 -translate-y-1/2"
                onClick={showPrevious}
                aria-label={t("previous")}
              >
                <ChevronLeft />
              </Button>
              <Button
                type="button"
                variant="secondary"
                size="icon-sm"
                className="absolute top-1/2 right-2 -translate-y-1/2"
                onClick={showNext}
                aria-label={t("next")}
              >
                <ChevronRight />
              </Button>
            </>
          )}
        </div>

        {images.length > 1 && (
          <div className="flex gap-2 overflow-x-auto pb-1">
            {images.map((imageUrl, index) => (
              <button
                key={`${imageUrl}-${index}`}
                type="button"
                className={cn(
                  "relative shrink-0 overflow-hidden rounded-md border border-green-200",
                  thumbnailClassName,
                  index === activeIndex && "border-green-600"
                )}
                aria-label={t("photoNumber", { current: index + 1, total: images.length })}
                onClick={() => setActiveIndex(index)}
              >
                <Image
                  src={imageUrl}
                  alt={`${alt} ${index + 1}`}
                  fill
                  className="object-cover"
                  unoptimized
                />
              </button>
            ))}
          </div>
        )}
      </div>

      {fullscreen}
    </>
  );
}