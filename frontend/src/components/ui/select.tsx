import * as React from "react";
import { cn } from "@/lib/utils";

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> { options?: { value: string; label: string }[] }
export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(({ className, options, children, ...props }, ref) => <select ref={ref} className={cn("flex h-9 w-full rounded-md border border-input bg-card px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50", className)} {...props}>{options?.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}{children}</select>);
Select.displayName = "Select";
