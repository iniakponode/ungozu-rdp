/** Static guards for the applicant preference implementation. */
const fs=require('node:fs'); const path=require('node:path');
const root=path.join(__dirname,'..');
function read(p){return fs.readFileSync(path.join(root,p),'utf8')}
const pairs=[
 ['src/app/(public)/apply/page.tsx',['ApplicationPackagePreference','preferred_package_id','preferred_fee_plan_id','setPreferredPackage(null)','setPreferredPlan(null)']],
 ['src/components/rdp/application-package-preference.tsx',['preferred-package','preferred-fee-plan','does not reserve a place','selectedPlan']],
 ['src/app/admin/applications/[id]/page.tsx',['preferred_fee_plan_id','preferenceText','decisionNotes.trim()']],
 ['src/lib/rdp-api.ts',['getRdpQuotation','acceptRdpQuotation','preferred_fee_plan_name']],
 ['src/components/rdp/quotation-review.tsx',['preferred_package_name','Your original preference']]
];
let bad=0;
for (const [name,terms] of pairs){const content=read(name);for(const term of terms){if(!content.includes(term)){console.error('MISSING',name,term);bad++}}}
if(bad) process.exit(1);
console.log('PASS: Applicant package/plan preferences and quotation components wired');
