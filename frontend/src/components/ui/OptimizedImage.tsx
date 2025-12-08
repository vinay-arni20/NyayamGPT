/**
 * NyayamGPT Optimized Image Component
 * =====================================
 * WebP-first with fallback and lazy loading
 */

import { useState, useRef, useEffect } from "react";
import { cn } from "@/lib/utils";

interface OptimizedImageProps {
  srcWebp?: string;
  srcFallback: string;
  alt: string;
  width?: number | string;
  height?: number | string;
  className?: string;
  lazy?: boolean;
  priority?: boolean;
  placeholder?: "blur" | "empty";
  blurDataUrl?: string;
  onLoad?: () => void;
  onError?: () => void;
}

export function OptimizedImage({
  srcWebp,
  srcFallback,
  alt,
  width,
  height,
  className,
  lazy = true,
  priority = false,
  placeholder = "empty",
  blurDataUrl,
  onLoad,
  onError,
}: OptimizedImageProps) {
  const [isLoaded, setIsLoaded] = useState(false);
  const [hasError, setHasError] = useState(false);
  const imgRef = useRef<HTMLImageElement>(null);

  // Use Intersection Observer for lazy loading
  useEffect(() => {
    if (!lazy || priority) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting && imgRef.current) {
            const img = imgRef.current;
            const picture = img.closest("picture");

            if (picture) {
              const sources = picture.querySelectorAll("source");
              sources.forEach((source) => {
                const dataSrcset = source.getAttribute("data-srcset");
                if (dataSrcset) {
                  source.srcset = dataSrcset;
                }
              });
            }

            const dataSrc = img.getAttribute("data-src");
            if (dataSrc) {
              img.src = dataSrc;
            }

            observer.unobserve(img);
          }
        });
      },
      {
        rootMargin: "50px",
        threshold: 0.01,
      }
    );

    if (imgRef.current) {
      observer.observe(imgRef.current);
    }

    return () => {
      observer.disconnect();
    };
  }, [lazy, priority]);

  const handleLoad = () => {
    setIsLoaded(true);
    onLoad?.();
  };

  const handleError = () => {
    setHasError(true);
    onError?.();
  };

  const containerStyle = {
    ...(width && { width: width }),
    ...(height && { height: height }),
    ...(placeholder === "blur" &&
      blurDataUrl && { backgroundImage: `url(${blurDataUrl})` }),
  };

  return (
    <div
      className={cn(
        "relative overflow-hidden",
        !isLoaded &&
          placeholder === "blur" &&
          "animate-pulse bg-gray-200 dark:bg-gray-700",
        placeholder === "blur" && blurDataUrl && "image-blur-placeholder",
        className
      )}
      {...(Object.keys(containerStyle).length > 0 && { style: containerStyle })}
    >
      <picture>
        {/* WebP Source */}
        {srcWebp && (
          <source
            type='image/webp'
            srcSet={priority || !lazy ? srcWebp : undefined}
            data-srcset={lazy && !priority ? srcWebp : undefined}
          />
        )}

        {/* Fallback Image */}
        <img
          ref={imgRef}
          src={priority || !lazy ? srcFallback : undefined}
          data-src={lazy && !priority ? srcFallback : undefined}
          alt={alt}
          width={typeof width === "number" ? width : undefined}
          height={typeof height === "number" ? height : undefined}
          loading={priority ? "eager" : "lazy"}
          decoding={priority ? "sync" : "async"}
          onLoad={handleLoad}
          onError={handleError}
          className={cn(
            "transition-opacity duration-300 image-container",
            isLoaded ? "opacity-100" : "opacity-0",
            hasError && "hidden"
          )}
        />
      </picture>

      {/* Error Fallback */}
      {hasError && (
        <div
          className={cn(
            "flex items-center justify-center",
            "bg-gray-100 dark:bg-gray-800",
            "text-gray-400 dark:text-gray-600 w-full h-full"
          )}
        >
          <svg
            className='image-fallback-icon'
            fill='none'
            stroke='currentColor'
            viewBox='0 0 24 24'
          >
            <path
              strokeLinecap='round'
              strokeLinejoin='round'
              strokeWidth={1.5}
              d='M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z'
            />
          </svg>
        </div>
      )}

      {/* Loading Skeleton */}
      {!isLoaded && !hasError && placeholder === "empty" && (
        <div
          className={cn(
            "absolute inset-0",
            "bg-gray-200 dark:bg-gray-700",
            "animate-pulse"
          )}
        />
      )}
    </div>
  );
}

export default OptimizedImage;
