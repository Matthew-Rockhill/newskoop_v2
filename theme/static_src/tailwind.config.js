/**
 * Tailwind CSS configuration for Newskoop project
 */

module.exports = {
    content: [
      // Templates within theme app
      '../templates/**/*.html',
      // Main templates directory
      '../../templates/**/*.html',
      // Templates in other django apps
      '../../**/templates/**/*.html',
    ],
    safelist: [
      'bg-green-100',
      'text-green-700',
      'hover:text-green-800',
      'bg-red-100',
      'text-red-700',
      'hover:text-red-800',
      'bg-yellow-100',
      'text-yellow-700',
      'hover:text-yellow-800',
      'bg-blue-100',
      'text-blue-700',
      'hover:text-blue-800',
      'bg-gray-100',
      'text-gray-700',
      'hover:text-gray-800',
    ],
    theme: {
      extend: {
        colors: {
          // Primary brand colors
          primary: {
            DEFAULT: '#6fb316',
            dark: '#5a9012',
            light: '#8bc34a',
            50: 'rgba(111, 179, 22, 0.05)',
            100: 'rgba(111, 179, 22, 0.1)',
            200: 'rgba(111, 179, 22, 0.2)',
          },
          // Gray palette
          gray: {
            50: '#f9fafb',
            100: '#f3f4f6',
            200: '#e5e7eb',
            300: '#d1d5db',
            400: '#9ca3af',
            500: '#6b7280',
            600: '#4b5563',
            700: '#374151',
            800: '#1f2937',
            900: '#111827',
          },
          // Status colors
          success: {
            DEFAULT: '#10b981',
            light: '#d1fae5',
          },
          warning: {
            DEFAULT: '#f59e0b',
            light: '#fef3c7',
          },
          danger: {
            DEFAULT: '#ef4444',
            light: '#fee2e2',
          },
          info: {
            DEFAULT: '#3b82f6',
            light: '#dbeafe',
          },
          // Custom color classes
          bg: {
            warning: '#fef3c7',
            info: '#dbeafe',
            success: '#d1fae5',
            danger: '#fee2e2',
          },
        },
        fontFamily: {
          sans: [
            'Inter',
            'ui-sans-serif',
            'system-ui',
            '-apple-system',
            'BlinkMacSystemFont',
            'Segoe UI',
            'Roboto',
            'Helvetica Neue',
            'Arial',
            'sans-serif',
          ],
        },
        borderRadius: {
          sm: '0.125rem', // 2px
          DEFAULT: '0.375rem', // 6px
          md: '0.5rem', // 8px
          lg: '0.75rem', // 12px
          xl: '1rem', // 16px
        },
        boxShadow: {
          sm: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
          DEFAULT:
            '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)',
          md: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
          lg: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
          xl: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
        },
      },
    },
    plugins: [
      require('@tailwindcss/forms'),
      require('@tailwindcss/typography'),
      require('@tailwindcss/aspect-ratio'),
    ],
  }
  