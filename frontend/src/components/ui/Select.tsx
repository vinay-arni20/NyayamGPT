import * as React from "react";
import { cn } from "@/lib/utils";

export interface SelectProps
  extends React.SelectHTMLAttributes<HTMLSelectElement> {
  error?: boolean;
  errorMessage?: string;
  options: { value: string; label: string }[];
}

const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, error, errorMessage, options, ...props }, ref) => {
    return (
      <div className='relative w-full'>
        <select
          className={cn(
            "flex h-11 w-full rounded-xl border bg-background px-4 py-2 text-sm shadow-sm transition-all duration-200",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:border-transparent",
            "disabled:cursor-not-allowed disabled:opacity-50",
            "appearance-none cursor-pointer",
            error
              ? "border-destructive focus-visible:ring-destructive"
              : "border-input",
            className
          )}
          ref={ref}
          {...props}
        >
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <div className='absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-muted-foreground'>
          <svg
            xmlns='http://www.w3.org/2000/svg'
            width='16'
            height='16'
            viewBox='0 0 24 24'
            fill='none'
            stroke='currentColor'
            strokeWidth='2'
            strokeLinecap='round'
            strokeLinejoin='round'
          >
            <path d='m6 9 6 6 6-6' />
          </svg>
        </div>
        {error && errorMessage && (
          <p className='mt-1.5 text-sm text-destructive'>{errorMessage}</p>
        )}
      </div>
    );
  }
);
Select.displayName = "Select";

export { Select };
