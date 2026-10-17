// Generated from the approved administrator handbook. Edit the manual and these online sections together.
export type HelpBlock = {kind:'paragraph'|'bullet'|'subheading'|'note'|'table';text?:string;rows?:string[][]}
export type HelpSection = {id:string;title:string;href:string;linkLabel:string;blocks:HelpBlock[]}
export const adminHelpSections:HelpSection[] = [
  {
    "id": "section-01",
    "title": "01. Overview and essential safeguards",
    "href": "/admin",
    "linkLabel": "Open dashboard",
    "blocks": [
      {
        "kind": "paragraph",
        "text": "The administrator interface is accessed at /admin/login. The application is organized around programmes, versioned curriculum, cohorts, packages, fee plans, admission applications, payment records, participant delivery, and evidence-based certification."
      },
      {
        "kind": "note",
        "text": "Critical distinction  Creating a programme is NOT the same as publishing it. Publishing a programme version freezes its curriculum/package/rubric configuration; publishing a cohort makes it publicly discoverable and opens applications only within the configured application dates."
      },
      {
        "kind": "bullet",
        "text": "A legacy cohort may already exist without a programme_version_id. Do not delete it, convert it manually, or recreate its records without checking production data. Legacy cohorts are deliberately excluded from Programme Builder editing."
      },
      {
        "kind": "bullet",
        "text": "Subsections are conditional. A blank Programme dropdown leaves the rest of the Builder hidden. Choose an existing programme or create one, then choose a version."
      },
      {
        "kind": "bullet",
        "text": "Administrator changes are not a sandbox. Plan/fee changes, publication, admissions and certificate revocation can affect real applicants or immutable financial records."
      },
      {
        "kind": "bullet",
        "text": "Keep Paystack/Stripe in TEST until the signed webhook, invoice, quote acceptance and reconciliation checks pass. Never put credentials into screenshots, Git, participant emails or public files."
      }
    ]
  },
  {
    "id": "section-02",
    "title": "02. Sign in, navigate and operate the dashboard",
    "href": "/admin",
    "linkLabel": "Open dashboard",
    "blocks": [
      {
        "kind": "bullet",
        "text": "Open https://rdp.iniakpothompson.com/admin/login and sign in with the designated RDP administrator account. Never share administrator passwords."
      },
      {
        "kind": "bullet",
        "text": "Select Dashboard. Use Administrative cohort to switch the cohort whose applications, participants and payments you are reviewing."
      },
      {
        "kind": "bullet",
        "text": "Use the Applications tab to search applicants by name, email or reference and select Review."
      },
      {
        "kind": "bullet",
        "text": "Use Participants → Open mentoring record to inspect individual development plans, check-ins and completion evidence."
      },
      {
        "kind": "bullet",
        "text": "Use Payments to inspect reference, invoice number, payment provider, currency, status and paid date; check Verified revenue by currency."
      },
      {
        "kind": "table",
        "rows": [
          [
            "Menu",
            "Purpose / primary actions"
          ],
          [
            "Dashboard",
            "Cohort selector; application counts, capacity, scholarship totals, payments, participants; search and drill down."
          ],
          [
            "Programme Builder",
            "Programmes, versions, curriculum, packages, entitlements, cohorts, fees and instalment schedules."
          ],
          [
            "Assessment Rubrics",
            "Version-bound completion criteria, score thresholds and evidence expectations."
          ],
          [
            "Events & Resources",
            "Create/publish/delete portal events and resource links; current page has an important cohort-targeting limit."
          ],
          [
            "Payment Gateways",
            "TEST/LIVE provider settings; masked credentials, connection test, health and audit trail."
          ],
          [
            "Main website / Sign out",
            "Return to main site and end administrative session."
          ]
        ]
      }
    ]
  },
  {
    "id": "section-03",
    "title": "03. Programme Builder — create the programme and version",
    "href": "/admin/builder#builder-programme",
    "linkLabel": "Open programme setup",
    "blocks": [
      {
        "kind": "subheading",
        "text": "3.1 Creating or selecting a programme"
      },
      {
        "kind": "bullet",
        "text": "Go to Programme Builder → 1. Programme and open “Choose programme”."
      },
      {
        "kind": "bullet",
        "text": "If your programme already exists, select it. If it does not, press New programme."
      },
      {
        "kind": "bullet",
        "text": "Enter Programme name, Public slug (lowercase letters/digits/hyphens), Category (optional), and Description; press Save."
      },
      {
        "kind": "bullet",
        "text": "After saving, SELECT the programme from the dropdown; the form closing does not automatically select the new record."
      },
      {
        "kind": "note",
        "text": "Slug rule  A programme slug must match ^[a-z0-9]+(?:-[a-z0-9]+)*$ (example: ungozu-researcher-development). Keep it stable once public links or applications exist."
      },
      {
        "kind": "subheading",
        "text": "3.2 Create and manage a programme version"
      },
      {
        "kind": "bullet",
        "text": "After selecting a programme, open 2. Version → New version. Enter Version title, Overview, Duration and Duration unit (weeks/months/years), and Learning outcomes."
      },
      {
        "kind": "bullet",
        "text": "Press Save. Then select the saved draft from “Choose programme version”."
      },
      {
        "kind": "bullet",
        "text": "Draft versions can be edited. A published version cannot be edited. Use Clone version to prepare changes for future cohorts; clone carries curriculum, rubric and entitlements, but not cohort dates/prices."
      },
      {
        "kind": "bullet",
        "text": "Do not press Publish version until all curriculum, package entitlements and required assessment criteria have been reviewed."
      },
      {
        "kind": "paragraph",
        "text": "Publication has practical consequences: the backend requires at least one active module, one active curriculum item and one active package with an included entitlement; once published, the version becomes read-only. Rubrics should be entered before publication because certificate approval requires a required criterion, even where the version-publish action itself does not enforce it."
      }
    ]
  },
  {
    "id": "section-04",
    "title": "04. Curriculum, packages and entitlements",
    "href": "/admin/builder#builder-curriculum",
    "linkLabel": "Open curriculum setup",
    "blocks": [
      {
        "kind": "subheading",
        "text": "4.1 Curriculum modules and items"
      },
      {
        "kind": "bullet",
        "text": "Select a draft programme version. In 3. Curriculum modules and items, choose Add module."
      },
      {
        "kind": "bullet",
        "text": "Enter module Order, Title, Summary, Learning outcomes, Completion criteria, Required module and Status (active or draft)."
      },
      {
        "kind": "bullet",
        "text": "Select the saved module, then click Add item. Enter Item type (for example assignment), Title, Description, Instructions, Estimated minutes, Completion required and Status."
      },
      {
        "kind": "bullet",
        "text": "Keep necessary participant evidence items marked Completion required, because administrators must review all required items before approving completion."
      },
      {
        "kind": "bullet",
        "text": "Use Edit module or Edit item only while the version is a draft. Review numbering for a sensible progression."
      },
      {
        "kind": "subheading",
        "text": "4.2 Packages and entitlements"
      },
      {
        "kind": "bullet",
        "text": "Under 4. Packages and entitlements, click Add package. Enter Code, Package name, Description, optional Package capacity, Display order and Active."
      },
      {
        "kind": "bullet",
        "text": "Select each package; add entitlements for programme benefits such as mentoring sessions, masterclasses, review cycles and resource access."
      },
      {
        "kind": "bullet",
        "text": "An entitlement contains Code, Name, Quantity, Unit, Limit value, Limit unit, Period, Description, Display order and Included."
      },
      {
        "kind": "bullet",
        "text": "Set capacity for limited tiers, e.g. Premium capacity 3. Leave Standard capacity empty if Standard may fill any remaining places in the 10-person cohort."
      },
      {
        "kind": "note",
        "text": "Important  Entitlement entries describe promised benefits and feed the public catalogue; they do not automatically schedule mentoring meetings or count review usage. Maintain an operational fulfilment register."
      }
    ]
  },
  {
    "id": "section-05",
    "title": "05. Assessment rubrics and publication",
    "href": "/admin/assessments",
    "linkLabel": "Open Assessment Rubrics",
    "blocks": [
      {
        "kind": "subheading",
        "text": "5.1 Configure version-bound rubrics BEFORE publishing"
      },
      {
        "kind": "bullet",
        "text": "Open Assessment Rubrics and choose the same draft version."
      },
      {
        "kind": "bullet",
        "text": "Add an assessment criterion: lower-case unique code, title, category, maximum score, passing score, evidence expectations, sort order, and Required for completion."
      },
      {
        "kind": "bullet",
        "text": "Provide clear evidence and scoring standards; the score per criterion cannot exceed the maximum and the passing score cannot exceed the maximum."
      },
      {
        "kind": "bullet",
        "text": "Record the minimum evidence in each description. Ensure at least one criterion is Required; otherwise participants cannot later be approved for completion."
      },
      {
        "kind": "bullet",
        "text": "Return to Programme Builder and verify all draft objects; then Publish version."
      },
      {
        "kind": "paragraph",
        "text": "The system checks required criteria independently: every required criterion must be assessed and meet its pass_score. There is no single combined-score pass calculation in the completion gate."
      },
      {
        "kind": "subheading",
        "text": "5.2 Create a cohort linked to the published version"
      },
      {
        "kind": "bullet",
        "text": "Once a version is published, section 5. Cohorts and fee plans permits Create cohort."
      },
      {
        "kind": "bullet",
        "text": "Enter Cohort name, Cohort slug, Public label, Applications open, Application deadline, Programme starts, Graduation, Programme ends, Maximum participants, and Public summary."
      },
      {
        "kind": "bullet",
        "text": "Chronology must satisfy: applications open ≤ deadline < start ≤ graduation ≤ end."
      },
      {
        "kind": "bullet",
        "text": "Save and select the cohort from the dropdown; it starts unpublished. Cohort configuration becomes frozen after its first application, even if subsequently unpublished."
      }
    ]
  },
  {
    "id": "section-06",
    "title": "06. Configure fee plans and instalment schedules",
    "href": "/admin/builder#builder-cohorts",
    "linkLabel": "Open cohorts and fee plans",
    "blocks": [
      {
        "kind": "paragraph",
        "text": "Fee plans are attached to a cohort AND a package. Create them after the cohort is saved and before publishing the cohort. Each payment arrangement is a separate fee plan; for example, Standard Upfront and Standard 3 Instalments link to the same Standard package."
      },
      {
        "kind": "table",
        "rows": [
          [
            "Builder field",
            "Meaning / example"
          ],
          [
            "Code",
            "Unique, stable alphanumeric / hyphen / underscore value: std-full-ngn."
          ],
          [
            "Region",
            "e.g. Nigeria."
          ],
          [
            "Name",
            "Public fee-plan label, e.g. Standard — Upfront."
          ],
          [
            "Currency",
            "Three uppercase ISO letters; NGN in the proposed first cohort."
          ],
          [
            "Total (minor units)",
            "NGN amounts in kobo: ₦150,000 = 15000000, not 150000."
          ],
          [
            "Package",
            "Select corresponding Standard or Premium package."
          ],
          [
            "Instalment lines",
            "Positive amounts; consecutive order; offsets in days from offer/effective date; sum exactly to plan total."
          ],
          [
            "Active",
            "Only active plans are eligible for publishing/admission selection."
          ]
        ]
      },
      {
        "kind": "bullet",
        "text": "Open section 5, select an unpublished cohort, and click New fee plan."
      },
      {
        "kind": "bullet",
        "text": "Select a package, enter Code, Region, Name, Currency and Total (minor units)."
      },
      {
        "kind": "bullet",
        "text": "Add one or more lines with positive Amount (minor units), Days after offer and Label. The totals MUST equal the plan total; offsets must be nondecreasing."
      },
      {
        "kind": "bullet",
        "text": "Save each fee plan; review the listed plan amount, currency, number of instalments and active state."
      },
      {
        "kind": "bullet",
        "text": "After all required active plans are configured, select Publish cohort. This enables public discovery; accepting applications still requires the current date to fall within opening and deadline."
      },
      {
        "kind": "note",
        "text": "Financial safety  When a fee plan has already been used in applications, quotations or invoices, the server prevents modifying the referenced plan. Treat quoted financial terms as immutable; create new future terms through a controlled process."
      }
    ]
  },
  {
    "id": "section-07",
    "title": "07. Public catalogue, application availability and URLs",
    "href": "/programme",
    "linkLabel": "View public catalogue",
    "blocks": [
      {
        "kind": "table",
        "rows": [
          [
            "Public route",
            "Use"
          ],
          [
            "/programme",
            "Lists published programme/cohort details, modules, packages and available participation information."
          ],
          [
            "/fees",
            "Shows published fee plans and costs."
          ],
          [
            "/apply?cohort=COHORT-SLUG",
            "Application form preselects a published cohort; must be within configured application dates."
          ],
          [
            "/status",
            "Private application-status experience accessed via a reference and token."
          ],
          [
            "/scholarship",
            "Optional financial support request using an applicant’s private token."
          ],
          [
            "/portal",
            "Authenticated participant development plan, check-ins, modules and completion view."
          ],
          [
            "/verify/TOKEN",
            "Public certificate verification without revealing private assessment data."
          ]
        ]
      },
      {
        "kind": "paragraph",
        "text": "Public catalogue eligibility requires the cohort to be published and linked to a published version (legacy published cohorts are retained). Application acceptance additionally requires cohort status applications_open and a date between the opening and deadline, inclusive."
      }
    ]
  },
  {
    "id": "section-08",
    "title": "08. Admissions, five-part scoring, scholarships and quotations",
    "href": "/admin",
    "linkLabel": "Open applications",
    "blocks": [
      {
        "kind": "subheading",
        "text": "8.1 Review and decision"
      },
      {
        "kind": "bullet",
        "text": "Dashboard → choose the correct Administrative cohort → Applications → Review."
      },
      {
        "kind": "bullet",
        "text": "Read background, research interests, goals, challenges, outputs and commitment."
      },
      {
        "kind": "bullet",
        "text": "Score Motivation, Development need, Programme fit, Commitment and Potential: 0–20 each, 100 maximum overall. Enter reviewer notes and a recommendation (hold, shortlist, accept, waitlist or decline)."
      },
      {
        "kind": "bullet",
        "text": "Save review before entering a decision. To accept, select the approved fee plan and enter an acceptance/payment deadline in the date-time field."
      },
      {
        "kind": "bullet",
        "text": "Click Accept, Shortlist, Waitlist or Decline as appropriate. Do not repeatedly click Accept if there was a slow response; refresh the record first."
      },
      {
        "kind": "paragraph",
        "text": "For programme-version cohorts, acceptance issues an immutable quotation (status quote_offered); the applicant accepts the quotation before invoices/payment activation. Legacy cohorts retain the older direct-payment pathway. Capacity checks include package-specific limits and reserved places."
      },
      {
        "kind": "subheading",
        "text": "8.2 Scholarships"
      },
      {
        "kind": "bullet",
        "text": "For an applicant who requested support, open Scholarship / subsidy request."
      },
      {
        "kind": "bullet",
        "text": "Review the need and evidence; select under review, approved, partially approved or declined; set currency/approved amount when applicable."
      },
      {
        "kind": "bullet",
        "text": "Save; verify resulting payable terms before the applicant accepts/starts payment. Financial recalculation is restricted after payment processing begins."
      },
      {
        "kind": "note",
        "text": "Confidentiality  Applicant reference, private status token, acceptance link and payment token must be treated as secrets. Send them only to the applicant; do not place them in a public programme announcement."
      }
    ]
  },
  {
    "id": "section-09",
    "title": "09. Payment gateway administration and financial reconciliation",
    "href": "/admin/settings/payments",
    "linkLabel": "Open Payment Gateways",
    "blocks": [
      {
        "kind": "bullet",
        "text": "Go to Payment Gateways → use TEST credentials first. Configure Paystack and/or Stripe for the appropriate provider and environment."
      },
      {
        "kind": "bullet",
        "text": "Set display name, priority, supported currencies, public/publishable key and the secret key (and Stripe webhook signing secret). Leave secret fields blank to retain existing stored values."
      },
      {
        "kind": "bullet",
        "text": "Save configuration, use Test connection and inspect status, last webhook, successful/failed payments and audit trail."
      },
      {
        "kind": "bullet",
        "text": "Confirm signed webhooks and provider-side verification; a browser callback alone is not proof of payment."
      },
      {
        "kind": "bullet",
        "text": "Check exact invoice ID, provider, currency, amount and reference against the gateway dashboard; verify no duplicate enrolment or repeated payment application."
      },
      {
        "kind": "bullet",
        "text": "Switch TEST → LIVE only after separate security, SMTP, real-money reconciliation and production-acceptance approval. Changing LIVE settings requires administrator reauthentication in the UI."
      },
      {
        "kind": "paragraph",
        "text": "Do not copy full transaction payloads, API keys or payment tokens into support tickets. A successful SMTP test or a 200 health endpoint does not certify live gateway processing."
      }
    ]
  },
  {
    "id": "section-10",
    "title": "10. Enrolment, mentoring and participant delivery",
    "href": "/admin",
    "linkLabel": "Open participants",
    "blocks": [
      {
        "kind": "bullet",
        "text": "Dashboard → Administrative cohort → Participants → Open mentoring record."
      },
      {
        "kind": "bullet",
        "text": "Check enrolment/payment status and fee instalments. Participant portal access and completion have payment-related eligibility checks."
      },
      {
        "kind": "bullet",
        "text": "Review the Individual Researcher Development Plan (IRDP): researcher identity, programme development goal (internally retained as twelve_month_goal for legacy compatibility), publication/methods/funding/network/impact goals."
      },
      {
        "kind": "bullet",
        "text": "Write mentor feedback and select Save IRDP feedback to mark it reviewed."
      },
      {
        "kind": "bullet",
        "text": "Review monthly check-ins for progress, outputs, obstacles, next actions and requested support; provide feedback and mark each reviewed."
      },
      {
        "kind": "bullet",
        "text": "Participants submit evidence for required curriculum items through the portal. Administrators review submitted evidence (Approve evidence or Request revision)."
      },
      {
        "kind": "paragraph",
        "text": "The portal has monthly check-ins; the planned 12 fortnightly touchpoints are mentoring activities, not a separate fortnightly form in the current interface. They must be scheduled/tracked operationally."
      }
    ]
  },
  {
    "id": "section-11",
    "title": "11. Completion decisions and certificates",
    "href": "/admin",
    "linkLabel": "Open participants",
    "blocks": [
      {
        "kind": "bullet",
        "text": "In a participant’s mentoring record, open Assessment and completion. Read any Outstanding approval requirements listed by the system."
      },
      {
        "kind": "bullet",
        "text": "Review all required curriculum-item evidence; items must reach Reviewed, not merely Submitted."
      },
      {
        "kind": "bullet",
        "text": "Record a score, evidence reference and assessor feedback for each required assessment criterion. The current gate requires each required criterion to meet its threshold."
      },
      {
        "kind": "bullet",
        "text": "Verify the IRDP has been reviewed, at least one monthly check-in reviewed, and enrolment is fully paid/active."
      },
      {
        "kind": "bullet",
        "text": "Write a reasoned completion rationale (at least 10 characters). Select Approve completion only when the system permits it; otherwise choose Needs work / Not approved as warranted."
      },
      {
        "kind": "bullet",
        "text": "After approval, select Issue certificate. Inspect the certificate number, public verification page and printable certificate."
      },
      {
        "kind": "bullet",
        "text": "Only use Revoke certificate for a defensible administrative reason (minimum 10 characters); revocation is recorded and cannot be silently reissued."
      },
      {
        "kind": "note",
        "text": "Certificate rule  A legacy enrolment without a programme version cannot use version-specific certification until an explicit compatibility/migration policy exists. Never bypass the backend completion blockers or issue certificates manually."
      }
    ]
  },
  {
    "id": "section-12",
    "title": "12. Events, resources and an important cohort limitation",
    "href": "/admin/content",
    "linkLabel": "Open Events & Resources",
    "blocks": [
      {
        "kind": "paragraph",
        "text": "The Events & Resources page allows an administrator to create a title, event type, delivery mode, start/end times, meeting URL, description, and published status. Resources support title, type, URL, month number, description and published status. They appear in the authenticated participant portal for the associated cohort."
      },
      {
        "kind": "note",
        "text": "The Events & Resources page now provides an explicit cohort selector. Select the intended cohort and verify it before creating, publishing or deleting content. New content is sent to the selected cohort, not an implicit cohort 1."
      },
      {
        "kind": "paragraph",
        "text": "Content workflow: select the correct cohort from Events & Resources, prepare and review event/resource details, then publish the entries for that cohort. Verify participant portal visibility with a controlled test account before releasing a real schedule."
      }
    ]
  },
  {
    "id": "section-13",
    "title": "13. Email, troubleshooting, security and release control",
    "href": "/admin/settings/payments",
    "linkLabel": "Open Payment Gateways",
    "blocks": [
      {
        "kind": "subheading",
        "text": "13.1 Transactional email"
      },
      {
        "kind": "paragraph",
        "text": "SMTP is configured server-side via backend/.env, not through the Programme Builder. The existing FastAPI email function uses aiosmtplib and returns True upon SMTP submission (not guaranteed inbox delivery). The configured Brevo sender has passed SPF, DKIM and DMARC for the user’s own test, but Gmail classified that one test as Spam while a university Outlook recipient received it in Inbox."
      },
      {
        "kind": "bullet",
        "text": "Send application confirmation, admission, quote acceptance, payment and password-setup tests to controlled addresses before accepting real applicants."
      },
      {
        "kind": "bullet",
        "text": "Monitor delivery logs and bounces; the current email helper logs failures but does not provide a durable retry queue."
      },
      {
        "kind": "subheading",
        "text": "13.2 Troubleshooting map"
      },
      {
        "kind": "table",
        "rows": [
          [
            "Symptom",
            "Likely cause / next action"
          ],
          [
            "Only 1. Programme visible",
            "Nothing selected. Open the Programme dropdown; select/create a programme and then a version."
          ],
          [
            "Earlier Milestone A footer",
            "Outdated wording was replaced by a link to this live handbook. Refresh or check deployment version if the old message remains."
          ],
          [
            "Version cannot be edited",
            "Published version is immutable; clone to create a draft successor."
          ],
          [
            "Cannot publish version",
            "Add active module + item + active package + included entitlement; define a required rubric before publication."
          ],
          [
            "Cannot publish cohort",
            "Link a published version; add at least one valid active fee plan."
          ],
          [
            "Fee total rejected",
            "Amounts are minor units; lines must sum to total, be positive and have ascending day offsets."
          ],
          [
            "Application unavailable",
            "Cohort not published, outside date window, closed or incorrect slug."
          ],
          [
            "Certificate blocked",
            "Check full payment, reviewed IRDP/check-in, reviewed required items and passing required assessments."
          ],
          [
            "New cohort events missing",
            "Check the selected administrative cohort on Events & Resources and confirm each event/resource is published to that cohort."
          ],
          [
            "Email accepted but not seen",
            "Review provider delivery logs, spam folder, authenticated sender, email content and recipient address."
          ],
          [
            "Service error",
            "Check `systemctl status ungozu-rdp-api ungozu-rdp-web` and `journalctl -u …`; do not paste secrets."
          ]
        ]
      },
      {
        "kind": "subheading",
        "text": "13.3 Operational security"
      },
      {
        "kind": "bullet",
        "text": "Use named administrator accounts and strong passwords; keep high-privilege access limited."
      },
      {
        "kind": "bullet",
        "text": "Keep production database, environment secrets and the encryption key backed up separately and encrypted; never place secrets under web-served paths or in Git."
      },
      {
        "kind": "bullet",
        "text": "Before changes to financial records or schema, verify the target database, take and integrity-check backups, and plan recovery."
      },
      {
        "kind": "bullet",
        "text": "Build and deploy through the Git branch/review process. A live production database migration is not automatically reversible on MariaDB."
      },
      {
        "kind": "bullet",
        "text": "Review payment/audit records after any gateway setting change. Use TEST mode for all demonstration transactions."
      }
    ]
  },
  {
    "id": "section-appendix-a",
    "title": "Appendix A — Daily / weekly administrative routine",
    "href": "/admin",
    "linkLabel": "Open dashboard",
    "blocks": [
      {
        "kind": "table",
        "rows": [
          [
            "When",
            "Actions"
          ],
          [
            "Each morning",
            "Confirm public health, Brevo transaction failures, new applications, pending scholarship decisions, and provider webhook errors."
          ],
          [
            "Twice weekly",
            "Review cohort occupancy, Premium capacity, outstanding quotations, overdue fee instalments and participant support requests."
          ],
          [
            "Each mentoring week",
            "Confirm meeting links, record attendance outside the current entitlement module, review submitted curriculum evidence."
          ],
          [
            "Monthly",
            "Review IRDP/check-ins, document feedback, reconcile gateway statements and unpaid invoices; export administrative report."
          ],
          [
            "Before graduation",
            "Audit all required items, assessments, check-ins, payment status, identity spelling, certificate approval and verification."
          ]
        ]
      }
    ]
  },
  {
    "id": "section-appendix-b",
    "title": "Appendix B — Pre-publication and go-live gate",
    "href": "/admin/builder",
    "linkLabel": "Open Builder",
    "blocks": [
      {
        "kind": "paragraph",
        "text": "☐ Programme and draft version metadata correct"
      },
      {
        "kind": "paragraph",
        "text": "☐ Six modules and required curriculum items present"
      },
      {
        "kind": "paragraph",
        "text": "☐ Standard/Premium packages and benefits checked"
      },
      {
        "kind": "paragraph",
        "text": "☐ Premium capacity 3, cohort capacity 10"
      },
      {
        "kind": "paragraph",
        "text": "☐ Assessment rubric entered and reviewed BEFORE version publication"
      },
      {
        "kind": "paragraph",
        "text": "☐ Programme version published deliberately"
      },
      {
        "kind": "paragraph",
        "text": "☐ Cohort chronology and dates reviewed"
      },
      {
        "kind": "paragraph",
        "text": "☐ Fee plan totals, instalment sums and currency verified"
      },
      {
        "kind": "paragraph",
        "text": "☐ TEST payment provider and webhook paths verified"
      },
      {
        "kind": "paragraph",
        "text": "☐ Public catalogue and application window checked"
      },
      {
        "kind": "paragraph",
        "text": "☐ Transactional emails tested with real providers"
      },
      {
        "kind": "paragraph",
        "text": "☐ Events/Resources cohort-routing defect resolved before publishing six-month cohort events"
      },
      {
        "kind": "paragraph",
        "text": "☐ Legacy cohort 1 and its real applications/payments untouched"
      }
    ]
  }
]
