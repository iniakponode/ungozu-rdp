import type { Metadata } from 'next'
import { ThemeProvider } from '@/components/theme-provider'
import { Toaster } from 'sonner'
import './globals.css'
export const metadata: Metadata = {
  title:{default:'Ungozu R & D Researcher Development Programme',template:'%s | Ungozu R & D'},
  description:'12-month early career researcher mentoring, capacity building and career development programme.',
  metadataBase:new URL(process.env.NEXT_PUBLIC_SITE_URL ?? 'http://localhost:3010'),
  robots:{index:true,follow:true},
}
export default function RootLayout({children}:{children:React.ReactNode}){
 return <html lang="en" suppressHydrationWarning><body className="font-sans antialiased"><ThemeProvider attribute="class" defaultTheme="system" enableSystem>{children}<Toaster richColors position="top-right"/></ThemeProvider></body></html>
}
