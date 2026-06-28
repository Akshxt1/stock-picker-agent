import type { Metadata } from "next"
import { Inter } from "next/font/google"
import "./globals.css"
import { ThemeProvider }    from "@/lib/theme-provider"
import { AuthProvider }     from "@/lib/auth-context"
import { RunProvider }      from "@/lib/run-context"
import { SettingsProvider } from "@/lib/settings-context"
import AppShell             from "@/components/app-shell"

const inter = Inter({ subsets: ["latin"] })

export const metadata: Metadata = {
  title:       "The Great Ponzi",
  description: "AI-powered stock analysis — India & US markets",
  icons: {
    icon:     "/logo-icon.png",
    shortcut: "/logo-icon.png",
    apple:    "/logo-icon.png",
  },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>
        <ThemeProvider attribute="class" defaultTheme="dark" enableSystem={false}>
          <AuthProvider>
            <SettingsProvider>
              <RunProvider>
                <AppShell>{children}</AppShell>
              </RunProvider>
            </SettingsProvider>
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  )
}
