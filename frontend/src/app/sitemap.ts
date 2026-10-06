import type { MetadataRoute } from 'next'
export default function sitemap():MetadataRoute.Sitemap{const base=process.env.NEXT_PUBLIC_SITE_URL ?? 'https://rdp.iniakpothompson.com';return ['','/programme','/mentor','/fees','/faq','/apply','/privacy','/terms'].map(path=>({url:`${base}${path}`,changeFrequency:'monthly',priority:path===''?1:0.7}))}
