import type { Config } from "tailwindcss"

const config: Config = {
  darkMode: ["class"],
  content: [
    "./pages/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./app/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    container: { center: true, padding: "2rem", screens: { "2xl": "1400px" } },
    extend: {
      colors: {
        border:      "hsl(var(--border))",
        input:       "hsl(var(--input))",
        ring:        "hsl(var(--ring))",
        background:  "hsl(var(--background))",
        foreground:  "hsl(var(--foreground))",
        primary: {
          DEFAULT:    "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT:    "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT:    "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT:    "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT:    "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        card: {
          DEFAULT:    "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        popover: {
          DEFAULT:    "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      fontFamily: {
        mono: ["'JetBrains Mono'", "Menlo", "monospace"],
      },
      backgroundImage: {
        "gradient-radial": "radial-gradient(var(--tw-gradient-stops))",
        "gold-shimmer":    "linear-gradient(135deg, hsl(38,95%,52%) 0%, hsl(45,95%,60%) 50%, hsl(38,95%,52%) 100%)",
      },
      keyframes: {
        "fade-in":   { from: { opacity: "0", transform: "translateY(8px)" }, to: { opacity: "1", transform: "none" } },
        "slide-in":  { from: { opacity: "0", transform: "translateX(-12px)" }, to: { opacity: "1", transform: "none" } },
        shimmer:     { "0%,100%": { opacity: "1" }, "50%": { opacity: "0.5" } },
        blink:       { "0%,100%": { opacity: "1" }, "50%": { opacity: "0" } },
      },
      animation: {
        "fade-in":  "fade-in 0.3s ease-out",
        "slide-in": "slide-in 0.3s ease-out",
        shimmer:    "shimmer 2s ease-in-out infinite",
        blink:      "blink 1s step-start infinite",
      },
    },
  },
  plugins: [],
}

export default config
