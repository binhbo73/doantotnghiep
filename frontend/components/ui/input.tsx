import React from 'react';

export interface InputProps
    extends React.InputHTMLAttributes<HTMLInputElement> {
    label?: string;
    error?: string;
    helperText?: string;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
    ({ className = '', error, helperText, label, ...props }, ref) => {
        return (
            <div className="w-full">
                {label && (
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                        {label}
                    </label>
                )}
                <input
                    ref={ref}
                    className={`
            w-full px-4 py-3 border rounded-lg
            focus:outline-none focus:ring-2 focus:ring-blue-500
            transition-colors duration-200
            disabled:bg-gray-100 disabled:cursor-not-allowed
            placeholder:text-gray-400
            ${error ? 'border-red-500 focus:ring-red-500' : 'border-gray-300'}
            ${className}
          `}
                    {...props}
                />
                {error && (
                    <p className="text-red-600 text-xs mt-1">{error}</p>
                )}
                {helperText && !error && (
                    <p className="text-gray-500 text-xs mt-1">{helperText}</p>
                )}
            </div>
        );
    }
);

Input.displayName = 'Input';
