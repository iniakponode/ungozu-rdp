/** Mocked public quotation flow. Never calls a real RDP backend or payment provider. */
import { expect, test, type Page } from '@playwright/test'

const ref = 'URD-MOCK-2026'
const access = 'mock-test-access-token-long-value-only'
const paymentToken = 'mock-test-payment-token-long-value-only'
const status = {
  application_ref: ref, full_name: 'Test Researcher', cohort_label: 'Mock Six-Month Cohort',
  status: 'quote_offered', scholarship_status: null, fee_plan: null,
  acceptance_deadline: '2099-12-31T23:59:00', invoices: [],
}
const quotation = {
  application_ref: ref, quote_id: 17, quote_number: 1, status: 'offered',
  package_name: 'Standard', currency: 'NGN',
  entitlements_snapshot_json: JSON.stringify({schema_version: 1, items: [
    {code:'research-masterclasses', name:'Research masterclasses', quantity:6, unit:'sessions', is_included:true},
    {code:'excluded-item', name:'Excluded item', is_included:false},
  ]}),
  gross_total_subunit: 15000000, scholarship_subunit: 1000000,
  payable_total_subunit: 14000000, effective_date: '2026-10-17',
  expires_at: '2099-12-31T23:59:00', accepted_at: null,
  installments: [{sequence_number:1, amount_subunit:14000000, due_date:'2026-11-02',description:'Payment due'}],
}

async function mockRoutes(page: Page, expired = false) {
  let acceptCount = 0
  await page.route('**/api/rdp/public/application-status?*', async route => {
    const u = new URL(route.request().url())
    expect(u.searchParams.get('ref')).toBe(ref)
    expect(u.searchParams.get('token')).toBe(access)
    await route.fulfill({json: status})
  })
  await page.route('**/api/rdp/public/quotation', async route => {
    expect(route.request().method()).toBe('POST')
    expect(route.request().postDataJSON()).toEqual({application_ref: ref, access_token: access})
    await route.fulfill({json: {
      ...quotation,
      expires_at: expired ? '2020-01-01T00:00:00' : quotation.expires_at,
    }})
  })
  await page.route('**/api/rdp/public/quotations/17/accept', async route => {
    acceptCount++
    expect(route.request().method()).toBe('POST')
    expect(route.request().postDataJSON()).toEqual({application_ref: ref, access_token: access})
    await route.fulfill({json: {application_ref: ref, quote_id: 17,
      quote_status:'accepted', application_status:'payment_due', payment_token: paymentToken,
      invoices:[{sequence:1, amount_subunit:14000000, currency:'NGN', due_date:'2026-11-02',status:'pending'}],
    }})
  })
  await page.route('**/api/rdp/public/payment-summary?*', async route => {
    const u = new URL(route.request().url())
    expect(u.searchParams.get('ref')).toBe(ref)
    expect(u.searchParams.get('token')).toBe(paymentToken)
    await route.fulfill({json: {...status, status:'payment_due',
      invoices:[{id:300,sequence:1,amount_subunit:14000000,currency:'NGN',due_date:'2026-11-02',status:'pending'}]}})
  })
  await page.route('**/api/rdp/public/payment-providers?*', async route =>
    route.fulfill({json:{active_environment:'test',allow_provider_selection:true,providers:[]}}))
  return () => acceptCount
}

test('Applicant reviews, explicitly accepts and reaches payment without payment processing', async ({page}) => {
  const accepts = await mockRoutes(page)
  await page.goto(`/status?ref=${encodeURIComponent(ref)}&token=${encodeURIComponent(access)}`)
  await expect(page.getByText('Review your programme quotation')).toBeVisible()
  await expect(page.getByText('Research masterclasses')).toBeVisible()
  await expect(page.getByText('Excluded item')).toHaveCount(0)
  await expect(page.getByText('Standard', {exact: true})).toBeVisible()
  await expect(page.getByText(/140,000/).first()).toBeVisible()
  await expect(page.getByText('Instalment 1')).toBeVisible()
  const accept = page.getByRole('button',{name:'Accept quotation and continue to payment'})
  await expect(accept).toBeDisabled()
  expect(accepts()).toBe(0)
  await page.getByRole('checkbox').check()
  await expect(accept).toBeEnabled()
  await accept.click()
  await expect(page).toHaveURL(new RegExp(`/payment\\?ref=${ref}&token=${paymentToken}`))
  await expect(page.getByText('Programme fee payment')).toBeVisible()
  expect(accepts()).toBe(1)
})

test('Expired quotation blocks acceptance even if a checkbox is selected', async ({page}) => {
  const accepts = await mockRoutes(page, true)
  await page.goto(`/status?ref=${encodeURIComponent(ref)}&token=${encodeURIComponent(access)}`)
  await expect(page.getByText('This quotation has expired.')).toBeVisible()
  await expect(page.getByRole('button',{name:'Accept quotation and continue to payment'})).toHaveCount(0)
  expect(accepts()).toBe(0)
})

const mockCatalogue = [
  {
    cohort: {id:4,name:'Cohort A',slug:'mock-cohort-a',label:'Cohort A',application_open_date:'2026-10-01',application_deadline:'2026-11-10',start_date:'2026-12-03',graduation_date:'2027-05-29',end_date:'2027-06-02',capacity:10,status:'applications_open',public_summary:''},
    programme:{id:1,name:'Mentoring Programme',slug:'mentoring-programme',category:null,description:null},
    version:{id:3,version_number:1,title:'Six Month Research Track',overview:null,duration_value:6,duration_unit:'months',learning_outcomes:null},
    modules:[],
    packages:[
      {id:10,code:'standard',name:'Standard',description:'Core mentoring',capacity:null,entitlements:[{code:'masterclass',name:'Research masterclasses',quantity:6,unit:'sessions',limit_value:null,limit_unit:null,period:'Programme',description:null}]},
      {id:11,code:'premium',name:'Premium',description:'Additional one-to-one support',capacity:3,entitlements:[]},
    ],
    fee_plans:[
      {id:30,package_id:10,code:'standard-upfront',region:'NG',name:'Standard Upfront',currency:'NGN',total_amount_subunit:15000000,installment_count:1,description:'One payment',installments:[{sequence_number:1,amount_subunit:15000000,due_offset_days:0,description:null}]},
      {id:31,package_id:10,code:'standard-3',region:'NG',name:'Standard Three Instalments',currency:'NGN',total_amount_subunit:18000000,installment_count:3,description:'Three payments',installments:[{sequence_number:1,amount_subunit:6000000,due_offset_days:0,description:null},{sequence_number:2,amount_subunit:6000000,due_offset_days:30,description:null},{sequence_number:3,amount_subunit:6000000,due_offset_days:60,description:null}]},
      {id:32,package_id:11,code:'premium-upfront',region:'NG',name:'Premium Upfront',currency:'NGN',total_amount_subunit:30000000,installment_count:1,description:null,installments:[]},
    ],
    accepting_applications:true,
  },
]

test('Applicant explicitly selects a package and payment plan; preferences are submitted without charging', async ({page}) => {
  await page.route('**/api/rdp/public/catalogue', route => route.fulfill({json:mockCatalogue}))
  let submitted:Record<string,unknown>|undefined
  await page.route('**/api/rdp/public/applications', async route => {
    submitted = route.request().postDataJSON() as Record<string,unknown>
    await route.fulfill({status:201,json:{application_ref:'URD-TEST-PREF',access_token:access,status:'submitted',message:'Application received'}})
  })
  await page.goto('/apply?cohort=mock-cohort-a')
  await expect(page.getByText('Choose your preferred mentoring package')).toBeVisible()
  await page.locator('input[name=preferred-package][value="10"]').check()
  await page.locator('input[name=preferred-fee-plan][value="31"]').check()
  await expect(page.getByText(/180,000/).last()).toBeVisible()
  const inputs:Record<string,string> = {
    full_name:'Preference Test Researcher',email:'researcher-pref@example.test',country:'Nigeria',
    institution:'Example University',career_stage:'Early career researcher',discipline:'Computer Science',
    research_interests:'Researching robust scholarly evaluation frameworks',
    goals:'Improve research methods and publication development skills',
    challenges:'Time constraints and limited local mentoring networks',
    commitment:'I can attend sessions and complete all required research tasks',
  }
  for(const [id,value] of Object.entries(inputs)) await page.locator(`#${id}`).fill(value)
  await page.locator('input[type=checkbox][required]').check()
  await page.getByRole('button',{name:'Submit application'}).click()
  await expect(page.getByText('Application received')).toBeVisible()
  expect(submitted?.preferred_package_id).toBe(10)
  expect(submitted?.preferred_fee_plan_id).toBe(31)
})
