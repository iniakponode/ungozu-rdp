/* Static safeguards for the quotation acceptance frontend integration.
 * This does NOT replace a browser test against an isolated database.
 */
const fs = require('node:fs')
const path = require('node:path')
const root = path.resolve(__dirname, '..')
function read(p) {return fs.readFileSync(path.join(root, p), 'utf8')}
function check(ok, message) {if (!ok) throw new Error(`FAIL: ${message}`); console.log(`PASS: ${message}`)}
const api = read('src/lib/rdp-api.ts')
const status = read('src/app/(public)/status/status-client.tsx')
const ui = read('src/components/rdp/quotation-review.tsx')
const apply = read('src/app/(public)/apply/page.tsx')
check(api.includes("pub<RDPQuotation>('/quotation'") && api.includes('getRdpQuotation'), 'Quotation review API connected')
check(api.includes('`/quotations/${quote_id}/accept`') && api.includes('acceptRdpQuotation'), 'Existing acceptance endpoint connected')
check(api.includes("method: 'POST', cache: 'no-store'") && api.includes('body: JSON.stringify({application_ref, access_token})'), 'Quotation credentials submitted in POST body with no-store')
check(status.includes("data.status==='quote_offered' && <QuotationReview"), 'Quotation review appears at quote-offered status')
check(ui.includes("quotation.status !== 'offered' || !agreed || expired || busy"), 'Acceptance guarded by review confirmation, expiry and pending state')
check(ui.includes('result.payment_token') && ui.includes('window.location.assign(next)'), 'Payment link constructed only from successful acceptance result')
check(ui.includes('quotation.installments.map') && ui.includes('servicesFromSnapshot'), 'Review includes installments and snapshotted entitlements')
check(!apply.includes('SMTP is configured'), 'Development-only SMTP text removed')
for (const name of [
  'src/app/(public)/privacy/page.tsx', 'src/app/(public)/terms/page.tsx',
]) {
  const content = read(name)
  check(!content.includes('Draft for operational use and legal review.') && !content.includes('before production launch'), `Public draft wording removed from ${name}`)
}
console.log('SUCCESS: Quotation UI wiring and public-copy static checks passed')
