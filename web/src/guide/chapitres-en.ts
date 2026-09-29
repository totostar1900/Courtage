// The guide in English: the same chapters as ./chapitres, keyed by id, with their sections and paragraphs in the same
// order. The French text there is the reference; this file follows it paragraph for paragraph.

export interface ChapitreEn { titre: string; resume: string; sections: { titre: string; texte: string[] }[] }

export const GROUPES_EN = {
  "Commencer": "Getting started",
  "Le parcours": "The journey",
  "Comprendre": "Understanding",
  "Référence": "Reference",
} as const;

export const CHAPITRES_EN: Record<string, ChapitreEn> = {
  bienvenue: {
    titre: "What the platform does",
    resume: "Your end-of-service benefit liability, calculated before anything is sold, then put out to competition.",
    sections: [
      { titre: "In one sentence", texte: [
        "You upload your staff list, we calculate what you owe your employees when they retire, and we put insurers in competition on that figure.",
        "You see the calculation BEFORE anyone sells you anything: the opposite of the usual practice, where the study comes from the insurer that wants the contract." ] },
      { titre: "Three principles", texte: [
        "No employee names. The calculation only needs a staff number, two dates and a salary. An employee's identity is used only when their benefit is paid.",
        "Your company decides. It adopts its plan, even one below the collective agreement: the platform flags this clearly, it does not refuse it.",
        "Everything can be verified. An issued report is sealed; anyone can check online that it has not been altered." ] },
      { titre: "Who does what", texte: [
        "The company (the HR director) uploads the staff list, describes and adopts its plan.",
        "The adviser reviews, issues the study and the tender specifications.",
        "Insurers respond to the tender specifications; you compare them on a common basis." ] },
      { titre: "Points for attention", texte: [
        "The file's dashboard lists what is waiting: a study more than 12 months old (a closing date has passed), a staff list that is too old, a draft or plan version pending for more than 30 days, a claim file that has stalled (the insurer is slow to pay, documents are awaited, a refusal), tender specifications past their deadline.",
        "Each point says who acts (the company or the adviser) and leads to the right page. “To handle” comes before “To watch”, then “Good to know”. Nothing needs “closing”: a point disappears once its cause is resolved.",
        "“Your files” counts, for each file, what is to handle and what is to watch." ] },
    ],
  },
  inscription: {
    titre: "Try, sign up, get confirmed",
    resume: "See your figures without an account; sign up in a few minutes; work on everything while awaiting confirmation.",
    sections: [
      { titre: "Try without an account", texte: [
        "“Try without an account” calculates your liability on screen: your staff (300 employees at most), your fund, the collective agreement alone or a model plan.",
        "Nothing is kept on the platform; the estimate is neither sealed nor printable. “Save my results” leads to sign-up, which carries over what you entered." ] },
      { titre: "Signing up", texte: [
        "Your phone and your email address are each verified with a code. You give your name, your position and the company: company name, country, RCCM number (required), size, sector, address. Finally you say what you expect from your broker (place the liability, put your contract out to tender, have your departures handled, get advice): that is your support request, which your adviser turns into a mandate to sign. You accept the terms of use and the privacy policy; the version accepted stays on your account (“My profile”).",
        "The RCCM document can follow: upload it from your file's banner. A company has only one file: an RCCM number already registered points to its administrator." ] },
      { titre: "While awaiting confirmation", texte: [
        "Your adviser contacts you within two working days, checks the company and confirms the sign-up. Until then, all the work is open: staff, plan, comparisons, on-screen studies; your adviser can be reached on WhatsApp, by email or by phone, from “Contact”. An email tells you when something is waiting for you (the confirmation, a message, a mandate to sign); these notices can be turned off in “My profile”, where you can also get them on WhatsApp, at your account's number — the subject and the link, nothing else.",
        "Anything that leaves the platform waits for confirmation: sealed reports, exports, notes, inviting colleagues, the anonymous catalogue, the mandate. An unconfirmed sign-up is erased after 30 days." ] },
    ],
  },
  connexion: {
    titre: "Signing in",
    resume: "Your phone number, a code received by message. No password.",
    sections: [
      { titre: "The code", texte: [
        "Enter your number: a six-digit code arrives by WhatsApp or SMS. It is valid for ten minutes and can be used only once.",
        "Never share it with anyone, not even your adviser: nobody from the platform will ever ask you for it.",
        "After five mistakes, the code stops working: ask for a new one (three per quarter of an hour at most)." ] },
      { titre: "I don't receive anything", texte: [
        "Your number must have been registered by your adviser. For confidentiality reasons, the platform answers in the same way whether it is registered or not.",
        "Check the country code: a Cameroonian number can be entered without +237." ] },
      { titre: "Picking up where you left off", texte: [
        "“Your files” offers to take you back to the last page you opened in a file (a study, your plan…), with the time elapsed: one click and you are there.",
        "This memory stays in this browser, for you alone; a file you no longer follow is not offered.",
        "To go elsewhere without searching the menus: Ctrl+K (⌘K on Mac), or “Go to…” under the file's name.",
        "On every page of a file, “Help on this page” (or the ? key) opens what the guide says about it, and the business terms it uses." ] },
    ],
  },
  personnel: {
    titre: "1. Upload the staff list",
    resume: "A spreadsheet: staff number, date of birth, hiring date, salary. Nothing else.",
    sections: [
      { titre: "The file", texte: [
        "An Excel (.xlsx) or CSV file, one row per employee. Columns are recognised in French or English, in any order.",
        "A “Category” column (Manager, Employee…) is useful if your plan differs by category.",
        "A names column is ignored: it is neither read nor stored." ] },
      { titre: "The checks", texte: [
        "Blocking: a missing field, a zero salary, an impossible age, a duplicate staff number. The study cannot be produced while a blocking point remains.",
        "Warning: many employees born on 1 January (estimated dates?), an employee past retirement age, an employee who accounts for more than 20% of the liability.",
        "Click a file to see its checks; the cross closes the detail." ] },
    ],
  },
  regime: {
    titre: "2. Describe your plan",
    resume: "What you actually pay, category by category, compared with the collective agreement.",
    sections: [
      { titre: "Do you need a plan?", texte: [
        "No: without a plan, the study relies on your sector's collective agreement. Describe a plan if you pay more (company agreement, custom, contracts).",
        "A plan has versions: a new version is added, the old one stays, and a study always says which version it is based on." ] },
      { titre: "Draft or adopted", texte: [
        "A version is either a draft or an adopted version, nothing else. Its dates are written on its card: “applies since”, “will apply from”, “replaced by version N”. The page sorts versions into three areas: in force, drafts, and the history, collapsed.",
        "All of a version's actions are in its ⋮ menu, at the top right of its card. An action that is not possible stays visible, greyed out, with its reason.",
        "A draft can be edited in place, duplicated, reviewed, compared in Simulate, adopted or deleted (its draft studies go with it).",
        "Adopting means communicating: the company's administrator adopts, the version is frozen, and its two notes are produced from its menu: for employees (what the plan pays them) and for insurers (the plan to be insured). To change it, you duplicate it as a draft.",
        "An adopted version can be deleted as long as nothing cites it (issued study, tender specifications, issued note, shared in the catalogue): that is going back on a decision, with a reason. “Clean up” suggests everything that can go.",
        "The analysis sorts its findings into three levels: Blocking, Warning (a plan less favourable than the collective agreement is adopted by confirming it) and Good to know. Its legal and tax points are pointers, to be reviewed with your legal adviser." ] },
      { titre: "Start from a model", texte: [
        "No written plan yet? “Start from a model” offers four scales calculated from your collective agreement: the agreement minimum, the agreement plus 25%, managers favoured (one and a half times the agreement), and a single scale, one rate per year.",
        "Each model is built never to fall below the collective agreement, at any length of service, and it comes from no company: it is a starting point, not someone else's plan.",
        "You take it into the form, adjust it and save it; the usual analysis follows, and you are the one who adopts." ] },
      { titre: "The anonymous catalogue", texte: [
        "“Start from the anonymous catalogue” shows plans that other companies have adopted and agreed to share: their scales, their months of benefit at 10, 20 and 30 years, and their gap with their collective agreement. You take one into the form, like a model plan.",
        "Nobody is named: no company, no document, no date. A plan is only shown in a group of at least five companies; when a group is too small, the catalogue widens it (size, then sector, then country are dropped) rather than show a small box.",
        "Sharing yours is the company's choice: from its adopted version, “Share anonymously”, with your consent. You see what is shared and what is not, and you can withdraw it at any time." ] },
      { titre: "Start from an existing text", texte: [
        "Your company agreement already exists? “Start from an existing text” reads the PDF and proposes the retirement benefit scale, category by category, with the effective date and the salary basis.",
        "Each proposed value cites the passage it comes from, and the platform checks that the passage really is in the text: “not found” means that value must be re-read before anything else.",
        "Nothing is saved without you: “Use in the form” prefills the version, you re-read it, correct it and save it; the usual analysis follows.",
        "For now, texts from CEMAC countries only. Depending on the configuration, the reading is done on the platform (common wordings) or by an AI service (Anthropic), which then asks for your consent before sending; the platform keeps only the document's fingerprint." ] },
      { titre: "The analysis", texte: [
        "“Review” reads your plan against the collective agreement: where it falls below the floor, what it costs in addition, the pitfalls (a badly bounded band, a cap that cancels a benefit).",
        "With a staff list, the analysis puts a figure on what each gap costs for YOUR employees." ] },
      { titre: "Adoption", texte: [
        "The company adopts, never the adviser. A plan below the collective agreement can be adopted by acknowledging it: your employees keep their right to the floor, and the calculation applies it." ] },
    ],
  },
  simulation: {
    titre: "Compare plans",
    resume: "Compare several plan versions, or test an idea, before deciding.",
    sections: [
      { titre: "Compare", texte: [
        "On the Study page, open “Compare plans before the study”. Tick the versions to compare, or “Test a scale idea”: each variant is calculated on the same staff at the same date.",
        "Each card gives the liability, what it adds to the collective agreement, the annual cost, and who benefits: if the addition goes mainly to the best paid, the card says so.",
        "The results open in a panel that the cross closes; your settings stay." ] },
      { titre: "The comparison", texte: [
        "Below the cards, “Compare plans” puts the variants side by side: the liability, the annual cost, the initial contribution and the liability per employee, each with its gap to the collective agreement alone.",
        "The curve shows what each plan pays on departure, in months of salary, by length of service; it opens on the category where the plans differ most. Hover over it (or tap it) to read the months at a given length of service.",
        "“Who gains, who loses” compares, employee by employee, the benefit on departure from one plan to the other: how many gain, how many lose, by how much on average, and the biggest gap, by staff number. Choose the point of comparison and the category.",
        "“View the table” gives all these figures in one table." ] },
    ],
  },
  etude: {
    titre: "3. The study and the report",
    resume: "The valuation at a closing date, then a sealed report.",
    sections: [
      { titre: "Starting a study", texte: [
        "Choose the file, the valuation date (a month end, your closing date) and the fund already invested. The study is a draft at first, and can be edited.",
        "The assumptions (discount rate, salary growth, turnover, retirement age) have default values; any change is justified and appears in the report." ] },
      { titre: "Reading the four figures", texte: [
        "Actuarial liability + annual cost − accumulated fund = net contribution. Net contribution + insurer's fees = contribution to pay.",
        "The “From liability to contribution” table shows each line to the last franc: the four cards always reconcile." ] },
      { titre: "Issuing", texte: [
        "The adviser issues the study when it is complete. It is then frozen, and its PDF report is sealed and numbered (RL-…).",
        "The report opens with a summary: the figures in sentences (what the company owes, what the year costs, what should be paid in, when the money goes out), then the decision to be taken. Then come the plan's curve against the collective agreement, the age and length-of-service pyramid, each assumption with its role and effect, the payment schedule in charts against the accumulated fund, the sensitivities and the link to the methodology note.",
        "“Export to Excel” gives the study as a workbook: the summary and the assumptions, the payment schedule (totals and shares as formulas), the categories, the sensitivities, and the calculation employee by employee, by staff number." ] },
    ],
  },
  financer: {
    titre: "4. Funding the liability",
    resume: "Insurance or in-house provision, under several return scenarios.",
    sections: [
      { titre: "Comparing offers", texte: [
        "Enter the terms of each offer: guaranteed rate, profit sharing, fees on contributions and on assets. The in-house provision is always added for comparison.",
        "Each offer is projected over the chosen horizon, under three return scenarios: prudent (3.5%), central (5%) and favourable (6.5%). The cheapest in the central scenario is marked.",
        "Also look at the “years without sufficient fund”: a cheaper offer that leaves the fund short in the year of a large departure is not the best one." ] },
    ],
  },
  cahier: {
    titre: "5. The tender specifications",
    resume: "Putting insurers in competition, without ever revealing an employee.",
    sections: [
      { titre: "What they contain", texte: [
        "Your liability (taken from an issued study), your plan, and your minimum requirements: guaranteed rate, profit sharing, maximum fees, transfer terms, payment deadline.",
        "Staff are described in groups of at least three employees, departures by five-year periods: nobody can be identified." ] },
      { titre: "The insurers' responses", texte: [
        "Each response is entered in the tender specifications grid, with the insurer's offer as a PDF if attached. What the insurer did not state stays blank: it is flagged, not guessed.",
        "The platform checks each response against the requested terms, criterion by criterion — compliant, deviating, or not stated — and flags a response received after the deadline.",
        "Responses are ranked by their net present cost, the same calculation as the offer comparison. The recommended one is the cheapest of the COMPLIANT ones: a cheaper offer that imposes a transfer penalty is not compliant.",
        "Your adviser consults each insurer from the specifications page: the insurer receives a personal link by email, valid until the deadline, reads the specifications and uploads its grid with its offer as a PDF, without an account. Its response joins the others, marked “uploaded by the insurer”; “Insurers consulted” shows who was consulted, when, who opened and who answered — the proof of a fair tender.",
        "Your adviser can also enter a response received otherwise; you read them and choose. Choosing an offer other than the recommended one is allowed, with a reason: the reason is kept in the file. Awarded tender specifications are closed; the adviser then records the contract." ] },
      { titre: "Changing insurer", texte: [
        "Transfer terms (notice, penalty) are part of the requirements: they are what will let you change insurer later without losing your fund.",
        "Responses can be exported to Excel: the ranking, compliance criterion by criterion, and the projection under the three return scenarios." ] },
    ],
  },
  contrat: {
    titre: "Brokerage",
    resume: "The platform is your broker: appointed by you, free for you.",
    sections: [
      { titre: "A single service", texte: [
        "The platform is your broker: you give it a mandate, it consults insurers, places your liability, then handles your benefit payments with the chosen insurer.",
        "The mandate is free for the company: the broker is paid only by the chosen insurer's commission, whose rate it discloses on request.",
        "The brokerage contract starts when the mandate is signed; the “Contract” screen shows it, with the insurer once the contract is placed." ] },
      { titre: "Signing the mandate", texte: [
        "From “Support”, the company says what it expects: placing its liability, putting its contract back out to competition, having its departures handled, advice on its plan.",
        "The adviser proposes a brokerage mandate: the assignments, the effective date, the term, the notice period, exclusivity. The full text is shown on the page.",
        "The administrator reads it and signs it online, on the text shown, saying in what capacity: legal representative of the company, or delegate — who then uploads the delegation of authority, which the adviser checks. The signed mandate is sealed and can be verified by its number. Nothing is binding before signature." ] },
      { titre: "When an employee leaves", texte: [
        "Under a mandate: you declare the departure, we prepare the file, send it and follow the payment. For this file only, we collect the beneficiary's identity.",
        "Without a mandate on the day of departure, the payment was handled between the company and its insurer: you keep the sealed calculation sheet and declare what was paid, without a name.",
        "In both cases, the recorded departure feeds the actual experience in your reports." ] },
    ],
  },
  placement: {
    titre: "Placement: policy, premiums, transfers",
    resume: "From the chosen offer to the policy in force; premiums are paid by bank transfer, never on the platform.",
    sections: [
      { titre: "The policy", texte: [
        "Once the offer is chosen, the adviser creates the policy. It moves forward through facts, each with its proof: policy received (the document is uploaded), signed with the insurer (you record the date), first premium received (the insurer's receipt), then in force on its effective date.",
        "Nothing is ticked by hand: the timeline reads the documents and dates. Riders are added to the policy." ] },
      { titre: "Paying a premium", texte: [
        "The platform pays nothing and receives nothing. The insurer sends a premium call with its bank details; the adviser records it here; you transfer from your bank to the insurer's account, then declare the transfer (date, amount, reference) and attach your bank's advice.",
        "The adviser uploads the insurer's receipt and confirms it: the call moves from “paid (declared)” to “received (confirmed)”. A due date passed with no declared transfer shows as overdue." ] },
      { titre: "Bank details, against fraud", texte: [
        "Each call is checked against the account the broker registered for that insurer, after having it confirmed by phone. A different or unknown account shows in red: “Do not pay”. The adviser then calls the insurer back on the number they know, never the one on the call received, and records who confirmed.",
        "Bank details are never sent by email: the notice only says a call is waiting. A “new bank account” received by email is not paid before being confirmed here." ] },
      { titre: "Fund statements", texte: [
        "The adviser uploads the insurer's statements with the fund amount. The page reconciles them with the premiums received and the fund your latest study uses: a difference is a finding to explain, never a blocking error." ] },
    ],
  },
  annee: {
    titre: "The file's year",
    resume: "The liability is re-measured every year, on the same date: the platform keeps the calendar and sends reminders.",
    sections: [
      { titre: "The calendar", texte: [
        "The latest issued study sets the date of the next valuation: the same date, one year later. Then come, in order, updating the staff list to that date (one month to do it), the insurer's annual statement if the contract is in force, then the year's valuation (two months).",
        "Before the policy's anniversary, your adviser reviews the contract with you: terms, return credited, whether to put it back out to tender." ] },
      { titre: "Nothing to tick", texte: [
        "Each step is read from your data: a staff file dated at the valuation date, an uploaded statement, an issued study. When the year's valuation is issued, the calendar moves on to the next year by itself.",
        "“The file's year”, on the dashboard, shows each step with its due date: done, upcoming, soon, late." ] },
      { titre: "Reminders", texte: [
        "An email tells you when a step becomes due soon, then if it is late — once for each, never more. It says nothing about your file: the step, the due date and the link. You can turn these notices off in “My profile”." ] },
    ],
  },
  departs: {
    titre: "Departures and history",
    resume: "Record each departure by staff number; the platform recalculates what was due.",
    sections: [
      { titre: "Declaring a departure", texte: [
        "The page opens once the insurance contract is signed and in force (policy received, signed, first premium received; or the contract your adviser recorded): the insurer will pay, and your adviser will handle the claim. Before that, it says what is missing.",
        "Staff number, reason, hiring and departure dates, monthly reference salary: “Calculate the amount due” shows what the rule in force on that day granted, and where the figure comes from (your plan, or the collective agreement).",
        "You declare what was paid. Less than the amount due is flagged — the employee was entitled to it; more is allowed — the company decides.",
        "A departure other than retirement (resignation, dismissal, death) costs no IFC, but it measures your actual staff turnover." ] },
      { titre: "Loading the history", texte: [
        "A spreadsheet of departures over the last five years, with what was paid and what the fund paid. The platform reads the file, calculates each amount due and shows everything before saving.",
        "A single blocking point (an unreadable date, an unknown reason, a departure already recorded) and nothing is saved: correct the file and start again.",
        "A names column is ignored, as in the staff list." ] },
      { titre: "Correcting without erasing", texte: [
        "A line cannot be edited: “Correct” adds a line that replaces the previous one and says why; so does “Cancel”. The history stays readable." ] },
      { titre: "Benefit payment claims, under brokerage", texte: [
        "On a retirement, “Request the benefit payment” opens a claim file: the amount requested from the fund, the beneficiary's identity and payment method, then the documents (certificate of employment, departure certificate…).",
        "Your adviser checks it — or tells you what is missing —, seals it (number PC-…) and sends it to the insurer. They record its response: paid, and the payment is entered on the departure; or refused, with the reason, and the file can be sent again.",
        "Once the payment deadline required in the tender specifications has passed (30 days otherwise), the insurer's delay is flagged.",
        "The identity and the documents are erased twelve months after payment. The file number can still be verified: its public seal carries no personal data." ] },
      { titre: "A departure without a mandate", texte: [
        "Without a mandate on the day of departure, the company dealt with its insurer. “Calculation sheet and payment” gives the sealed calculation sheet (number FC-…, with no personal data) and records what the insurer paid, without a name." ] },
      { titre: "What the reports do with them", texte: [
        "The study reads the departures recorded at its date: the retirements the previous study expected against those that took place, year by year — sealed with the study.",
        "The observed turnover (resignations and dismissals, relative to headcount) is compared with the assumption. With at least five departures and a gap of half a point, it is PROPOSED; never applied automatically: adopting it is done in a new study, with a justification that appears in the report.",
        "An employee recorded as having left but still present in the staff list is flagged: the liability would count them.",
        "The tender specifications show insurers past retirements by grouped years — at least three per period — and the payment times observed on the files followed." ] },
    ],
  },
  equipe: {
    titre: "The file's team",
    resume: "Who follows the file, what each person can do, and how to add someone.",
    sections: [
      { titre: "Rights and a position", texte: [
        "Each member has rights, what they can do, and a position, what they are (HR director, CEO, CFO, accountant… free text).",
        "Company administrator: decides (adopts the plan, chooses the insurer) and manages colleagues. Contributor: uploads the staff list, prepares plans and studies, without adopting. Read only: sees everything. Adviser: follows the file, issues studies, manages the whole team.",
        "On the company side, you see your colleagues; the adviser appears separately, as a contact. The company administrator adds, edits and removes colleagues; they never grant adviser rights." ] },
      { titre: "Add, edit, remove", texte: [
        "“Add someone”: a name, a position, rights, a phone number. The person then signs in with that number, with a code received by message.",
        "A member's ⋮ menu edits them (name, position, rights) or removes them from the file; what they did stays in the log, under their name. The last company administrator and the last adviser stay.",
        "The number is the sign-in identity: to change it, remove the person and add them again with the new number." ] },
      { titre: "The file's status", texte: [
        "A file is open, suspended, closed or archived. Only the adviser changes its status, from the Team page, always with a dated and signed reason; the history keeps it, and a banner shows it on every page.",
        "Suspended (unpaid, dispute, documents awaited): everything can be read and exported, but no study is issued and no tender specifications go out until it resumes.",
        "Closed (end of mandate, change of broker, cessation of business): read only for everyone. The adviser can still reopen it for 90 days; after that, the file is archived.",
        "Archived: the uploaded staff lists are erased and the file no longer opens. Studies, sealed reports and the log are kept: each document can still be verified by its number.",
        "Only an empty file, opened by mistake, can be deleted. As soon as a document has been issued, its number is in circulation: the file is closed, it does not disappear." ] },
    ],
  },
  comprendre: {
    titre: "How the liability is calculated",
    resume: "The projected method, step by step, on one employee.",
    sections: [
      { titre: "For each employee", texte: [
        "1. The IFC at retirement: the salary projected to retirement × the months due for the total length of service they will have by then.",
        "2. The likelihood that they receive it: being alive (CIMA table) and still with the company (staff turnover).",
        "3. Bring it back to today with the discount rate: this is the PVFB.",
        "4. The liability is the share of the PVFB already earned: PVFB × current length of service ÷ total length of service. The annual cost is one more year: PVFB ÷ total length of service." ] },
      { titre: "What moves the figure", texte: [
        "The discount rate, first of all: the study shows what the liability becomes with one point less.",
        "Employees close to retirement with long service weigh the most: their IFC is near, large, and almost certain." ] },
    ],
  },
  methode: {
    titre: "The actuarial method in detail",
    resume: "The formulas, the assumptions and their default values, funding, and what the calculation does not do.",
    sections: [
      { titre: "The method", texte: [
        "The platform applies the projected unit credit method, with entitlements attributed on a straight-line basis in proportion to length of service. The calculation is done employee by employee, then added up. Calculations are done without intermediate rounding; totals are rounded to the franc.",
        "Age and length of service are counted in completed years, plus the days elapsed since the last anniversary divided by 365 (like DATEDIF in a spreadsheet)." ] },
      { titre: "The formulas, for one employee", texte: [
        "Remaining years n = retirement age − age. Total length of service A = the length of service they will have at retirement.",
        "Final salary (monthly) = annual salary ÷ 12 × ((1 + inflation) × (1 + salary growth))ⁿ.",
        "Months due = the scale applied to A (rounded in completed years or in months, depending on the plan), zero below the minimum length of service, capped by the ceiling; with a plan, the collective agreement remains the floor and the more favourable of the two is used.",
        "IFC = final salary × months due.",
        "Survival = l(retirement age) ÷ l(current age), read from the TV CIMA F mortality table.",
        "Presence = the product, from the current age to the eve of retirement, of (1 − turnover rate).",
        "PVFB = IFC × survival × presence × (1 + discount rate)⁻ⁿ.",
        "Liability = PVFB × current length of service ÷ A. Annual cost = PVFB ÷ A." ] },
      { titre: "From the total to the contribution", texte: [
        "Net contribution = liability + annual cost − fund already accumulated (never negative).",
        "Total contribution = net contribution × (1 + contribution fees). The study shows this reconciliation line by line." ] },
      { titre: "The default assumptions", texte: [
        "Discount rate 3.5%. Salary growth 2%. Inflation 0%. Retirement at 60. Turnover 2% a year at all ages. TV CIMA F table. Contribution fees 4%.",
        "All of them are set in the “Assumptions” section of the study form, collapsed by default: each one gives its default value, its role, its effect and how to set it, and “Reset to default values” cancels everything. Turnover can be given by age band there.",
        "Departing from a default value requires a justification. It is printed in the sealed report.",
        "The study recalculates the liability with the discount rate, salary growth and turnover one point lower and one point higher: these are the sensitivities." ] },
      { titre: "Funding", texte: [
        "Each year, the company contributes: the annual cost indexed to salaries, plus a share of the initial deficit (liability − fund) amortised over the chosen number of years. The insurer deducts its fees, credits the fund at the guaranteed rate plus its profit sharing, then the year's expected benefits are paid by the fund, up to what it holds.",
        "Three return scenarios: prudent 3.5%, central 5%, favourable 6.5%. Offers are compared on their net present cost, in the central scenario: discounted contributions and shortfalls, less the fund remaining at the horizon." ] },
      { titre: "Actual experience", texte: [
        "The observed turnover is the number of resignations and dismissals ÷ (years × headcount), over five years at most. It is only credible from five departures, and proposed only if it differs by at least half a point. It is never applied automatically." ] },
      { titre: "What the calculation does not do", texte: [
        "Only retirement is costed; the other events covered by a plan (early departure, economic dismissal, death) are flagged, not valued.",
        "A single mortality table for everyone, the female table: a prudent assumption, since women live longer in it.",
        "Uniform salary growth, with no age scale. A plan based on the average of the last 12 months is valued on the projected current salary, and this is flagged.",
        "The study is a decision-support calculation, not legal or tax advice." ] },
    ],
  },
  conventions: {
    titre: "The pre-filled collective agreements",
    resume: "The built-in scales for the CEMAC countries, their sources and how far they have been verified.",
    sections: [
      { titre: "How to read them", texte: [
        "For now the platform covers the six CEMAC countries: Cameroon, Gabon, Congo, Chad, Central African Republic, Equatorial Guinea. A country without a pre-filled collective agreement is shown as such.",
        "Each collective agreement is dated: a revised version does not replace the old one, which remains the reference for an earlier study.",
        "“Validated”: rates consistent across several sources. “To be validated”: the platform could not confirm the scale; a study cannot be issued on a collective agreement still to be validated.",
        "The verification says honestly what was read: several scales come from consistent secondary sources, the official text not having been available." ] },
    ],
  },
  verifier: {
    titre: "Verifying a document",
    resume: "An issued report can be verified online, without an account.",
    sections: [
      { titre: "How", texte: [
        "Each page of a report carries its number (RL-…) and the verification address. Enter the number on “Verify a document”: the platform says who issued it and when.",
        "Upload the PDF file itself: the platform says whether it is the original, byte for byte. Change a single character, and it no longer is." ] },
    ],
  },
};
