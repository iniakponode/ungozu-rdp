import type { MetadataRoute } from 'next'
export default function robots():MetadataRoute.Robots{const base=process.env.NEXT_PUBLIC_SITE_URL ?? 'https://rdp.iniakpothompson.com';return {rules:[{userAgent:'*',allow:'/',disallow:['/admin/','/portal/','/status','/payment','/set-password','/api/']}],sitemap:`${base}/sitemap.xml`}}
