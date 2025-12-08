import * as React from "react";
import { cn } from "@/lib/utils";

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {
  error?: boolean;
  errorMessage?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  (
    { className, type, error, errorMessage, leftIcon, rightIcon, ...props },
    ref
  ) => {
    return (
      <div className='relative w-full'>
        {leftIcon && (
          <div className='absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground'>
            {leftIcon}
          </div>
        )}
        <input
          type={type}
          className={cn(
            "flex h-11 w-full rounded-xl border bg-background px-4 py-2 text-sm shadow-sm transition-all duration-200",
            "placeholder:text-muted-foreground",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:border-transparent",
            "disabled:cursor-not-allowed disabled:opacity-50",
            error
              ? "border-destructive focus-visible:ring-destructive"
              : "border-input",
            leftIcon && "pl-10",
            rightIcon && "pr-10",
            className
          )}
          ref={ref}
          {...props}
        />
        {rightIcon && (
          <div className='absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground'>
            {rightIcon}
          </div>
        )}
        {error && errorMessage && (
          <p className='mt-1.5 text-sm text-destructive'>{errorMessage}</p>
        )}
      </div>
    );
  }
);
Input.displayName = "Input";

export { Input };
