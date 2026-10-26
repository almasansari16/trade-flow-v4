"""
End-to-end scenarios (requirements §15 A–H) — customer onboarding, catalogue, sales requests,
internal approval, SAP submission (development mock), role permissions and existing functionality.

Runs against a served build (vite preview / dev server). All users share one browser
context, so they share the prototype's in-browser state — exactly like a stakeholder
demo. Usage:  python3 tests/e2e/scenarios.py [base_url]

Primary demo accounts: Omar (Customer Portal User), Priya (Customer Onboarding Approver + Operations),
Daniel (Sales Representative / Account Manager, Gulf), Marcus (Head of Sales), Elena (Administrator).
Background records used where a second territory is needed: Faisal (Saudi Arabia), Sofia (UK & W. Europe).
"""
import os, re, sys, tempfile
from playwright.sync_api import sync_playwright, expect

BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:4173'
PW = 'TradeFlow@2026'
U = {
    'omar': 'omar.haddad@gulfhorizon.example', 'daniel': 'daniel.okafor@tradeflow.example', 'marcus': 'marcus.chen@tradeflow.example',
    'priya': 'priya.nair@tradeflow.example', 'elena': 'elena.petrova@tradeflow.example',
    'faisal': 'faisal.rahman@tradeflow.example', 'sofia': 'sofia.lindqvist@tradeflow.example',
    'neema': 'neema@lagoonbeauty.example', 'tom': 'tom@auroratrade.example', 'dilshan': 'dilshan@lankaaroma.example',
}
NEW = {'email': 'mariam@pearlbay.example', 'pw': 'Pearl2026!'}
results: list[tuple[str, bool, str]] = []
console_errors: list[str] = []
ctx_data: dict = {}


def scenario(name):
    def wrap(fn):
        def run(page):
            try:
                fn(page)
                results.append((name, True, ''))
                print(f'PASS  {name}')
            except Exception as e:  # noqa: BLE001
                results.append((name, False, f'{type(e).__name__}: ' + ' | '.join(l.strip() for l in str(e).splitlines()[:4])[:400]))
                print(f'FAIL  {name}\n      {results[-1][2]}')
                page.screenshot(path=f'{OUT}/fail-{len(results):02d}.png', full_page=True)
        return run
    return wrap


def logout(page):
    page.goto(BASE + '/app')
    menu = page.get_by_role('button', name='Profile menu')
    for _ in range(30):
        if '/login' in page.url:
            return
        if menu.count():
            break
        page.wait_for_timeout(150)
    if '/login' in page.url:
        return
    menu.click()
    page.get_by_text('Sign out', exact=True).click()
    page.wait_for_url('**/login**')


def login(page, who, password=PW, expect_ok=True):
    logout(page)
    page.goto(BASE + '/login')
    page.get_by_label('Email').fill(U.get(who, who))
    page.locator('input[autocomplete=current-password]').fill(password)
    page.get_by_role('button', name='Sign in', exact=True).click()
    if expect_ok:
        page.wait_for_url('**/app**')
        page.wait_for_timeout(600)


def open_app(page, ref):
    page.goto(BASE + '/app/applications?tab=all')
    page.get_by_placeholder('Search reference, company, city…').fill(ref)
    page.get_by_role('cell', name=ref).first.click()
    page.wait_for_url('**/app/applications/**')


def act(page, button, confirm, fill: dict | None = None, sections=()):
    page.get_by_role('button', name=button, exact=True).click()
    dlg = page.get_by_role('dialog')
    for s in sections:
        dlg.get_by_label(s).check()
    for label, text in (fill or {}).items():
        dlg.get_by_label(label).fill(text)
    dlg.get_by_role('button', name=confirm, exact=True).click()


def status_is(page, status):
    expect(page.locator('header').get_by_text(status, exact=True).first).to_be_visible()


def nav(page):
    return page.get_by_role('navigation', name='Main navigation')

def register(page, email, pw, cr, submit=True):
    page.goto(BASE + '/register')
    page.get_by_label('Sign-in email').fill(email)
    page.locator('input[autocomplete=new-password]').nth(0).fill(pw)
    page.get_by_label('Confirm password').fill(pw)
    page.get_by_role('button', name='Continue').click()
    page.get_by_label('Trading name').fill('Duplicate Test Trading')
    page.get_by_label('Registered legal name').fill('Duplicate Test Trading LLC')
    page.get_by_label('Commercial registration no.').fill(cr)
    page.get_by_label('Tax / VAT number').fill('TRN 999')
    page.get_by_label('Business type').select_option(index=1)
    page.get_by_label('Expected annual volume').select_option(index=2)
    page.get_by_role('button', name='Continue').click()
    page.get_by_label('Country').select_option('United Arab Emirates')
    page.get_by_label('City', exact=False).first.fill('Dubai')
    page.get_by_label('Contact full name').fill('Dup Tester')
    page.get_by_label('Job title').fill('Owner')
    page.get_by_label('Phone').fill('+971 4 000 0000')
    page.get_by_role('button', name='Continue').click()
    page.locator('fieldset label').first.click()
    page.get_by_label(re.compile(r'^Street address')).fill('Street 1')
    page.get_by_role('textbox', name='City').fill('Dubai')
    page.get_by_role('button', name='Continue').click()
    d = tempfile.mkdtemp(); files = []
    for n in ('CR.pdf', 'Tax.pdf'):
        f = os.path.join(d, n); open(f, 'wb').write(b'%PDF-1.4 demo'); files.append(f)
    page.locator('input[type=file]').set_input_files(files)
    page.get_by_label('Type for Tax.pdf').select_option('Tax Certificate')
    page.get_by_role('button', name='Continue').click()
    page.get_by_label('I confirm the information provided is accurate and complete.').check()
    if submit:
        page.get_by_role('button', name='Submit application').click()


# ─── Scenarios ─────────────────────────────────────────────────────────────

@scenario('A1 Five demo accounts on the sign-in page; a new customer registers (account + Customer Application) and gets a reference + secure link')
def s01(page):
    logout(page)
    page.goto(BASE + '/login')
    expect(page.locator('#demo-accounts').locator('xpath=ancestor::section').locator('ul.space-y-2 > li')).to_have_count(5)
    page.goto(BASE + '/register')
    expect(page.get_by_role('heading', name='Customer registration')).to_be_visible()
    page.get_by_label('Sign-in email').fill(NEW['email'])
    page.locator('input[autocomplete=new-password]').nth(0).fill(NEW['pw'])
    page.get_by_label('Confirm password').fill(NEW['pw'])
    page.get_by_role('button', name='Continue').click()
    page.get_by_label('Trading name').fill('Pearl Bay Fragrances')
    page.get_by_label('Registered legal name').fill('Pearl Bay Fragrances W.L.L.')
    page.get_by_label('Commercial registration no.').fill('QA-CR-77812')
    page.get_by_label('Tax / VAT number').fill('TIN 6002118')
    page.get_by_label('Business type').select_option(index=1)
    page.get_by_label('Expected annual volume').select_option(index=2)
    page.get_by_role('button', name='Continue').click()
    page.get_by_label('Country').select_option('Qatar')
    page.get_by_label('City', exact=False).first.fill('Doha')
    page.get_by_label('Contact full name').fill('Mariam Al-Thani')
    page.get_by_label('Job title').fill('Managing Director')
    expect(page.get_by_label('Business email')).to_have_value(NEW['email'])
    page.get_by_label('Phone').fill('+974 4444 0100')
    page.get_by_role('button', name='Continue').click()
    page.locator('fieldset label').first.click()
    page.get_by_label(re.compile(r'^Street address')).fill('West Bay, Tower 3')
    page.get_by_role('textbox', name='City').fill('Doha')
    page.get_by_role('button', name='Continue').click()
    d = tempfile.mkdtemp()
    files = []
    for n in ('CR_Extract.pdf', 'Tax_Card.pdf'):
        f = os.path.join(d, n); open(f, 'wb').write(b'%PDF-1.4 demo'); files.append(f)
    page.locator('input[type=file]').set_input_files(files)
    page.get_by_label('Type for Tax_Card.pdf').select_option('Tax Certificate')
    page.get_by_role('button', name='Continue').click()
    page.get_by_label('I confirm the information provided is accurate and complete.').check()
    page.get_by_role('button', name='Submit application').click()
    expect(page.get_by_role('heading', name='Customer application received')).to_be_visible(timeout=8000)
    ctx_data['ref'] = page.locator('span.font-mono').first.inner_text()
    ctx_data['link'] = page.locator('code').first.inner_text()
    assert re.match(r'APP-\d{4}-\d{4}', ctx_data['ref']), ctx_data['ref']
    assert '/track?ref=' in ctx_data['link'] and 'token=' in ctx_data['link']


@scenario('A2 Public Track Application (reference + registered email): status, stage, dates — no staff names or internal data')
def s02(page):
    logout(page)
    page.goto(BASE + '/track')
    page.get_by_label('Application reference').fill(ctx_data['ref'])
    page.get_by_label('Registered email address').fill(NEW['email'])
    page.get_by_role('button', name='Check status').click()
    expect(page.get_by_text('Submitted — waiting for review')).to_be_visible()
    expect(page.get_by_text('Onboarding review (1 of 1)')).to_be_visible()
    body = page.locator('main').inner_text()
    for leak in ('Priya', 'Daniel', 'Internal', 'u-sc'):
        assert leak not in body, f'leaked "{leak}"'


@scenario('A3 Secure time-limited link works; wrong email / tampered token / reference alone are rejected generically')
def s03(page):
    page.goto(ctx_data['link'].replace('http://localhost:4173', BASE))
    expect(page.get_by_text(ctx_data['ref']).first).to_be_visible()
    page.goto(BASE + '/track?ref=' + ctx_data['ref'] + '&token=deadbeef')
    expect(page.get_by_text('We could not find an application matching those details')).to_be_visible()
    page.goto(BASE + '/track')
    page.get_by_label('Application reference').fill(ctx_data['ref'])
    page.get_by_label('Registered email address').fill('someone@else.example')
    page.get_by_role('button', name='Check status').click()
    expect(page.get_by_text('We could not find an application matching those details')).to_be_visible()
    page.goto(BASE + '/track?ref=' + ctx_data['ref'])
    expect(page.get_by_role('button', name='Check status')).to_be_visible()
    expect(page.get_by_text('Onboarding review (1 of 1)')).to_have_count(0)


@scenario('A4 Customer Onboarding Approver starts the review; decisions are blocked until started')
def s04(page):
    login(page, 'priya')
    page.goto(BASE + '/app/applications?tab=action')
    expect(page.get_by_role('cell', name=ctx_data['ref'])).to_be_visible()
    open_app(page, ctx_data['ref'])
    expect(page.get_by_role('button', name='Approve registration')).to_be_disabled()
    expect(page.get_by_text('Start the review first.').first).to_be_visible()
    act(page, 'Start review', 'Start review')
    status_is(page, 'Under Review')


@scenario('A5 Approver returns to the customer (instructions + sections mandatory)')
def s05(page):
    page.get_by_role('button', name='Return to requester', exact=True).click()
    dlg = page.get_by_role('dialog')
    dlg.get_by_role('button', name='Return to requester', exact=True).click()
    expect(dlg.get_by_role('alert')).to_contain_text('at least 10 characters')
    dlg.get_by_label('Instructions for the applicant').fill('Please correct the tax card number and upload a current CR extract.')
    dlg.get_by_role('button', name='Return to requester', exact=True).click()
    expect(dlg.get_by_role('alert')).to_contain_text('Select at least one section')
    dlg.get_by_label('Company details').check()
    dlg.get_by_label('Supporting documents').check()
    dlg.get_by_label('Internal remarks (optional)').fill('INTERNAL-NOTE: CR extract looked stale.')
    dlg.get_by_role('button', name='Return to requester', exact=True).click()
    status_is(page, 'Returned for Information')


@scenario('A6 Customer corrects only the re-opened sections and resubmits; revision 2 goes back to the same reviewer')
def s06(page):
    login(page, NEW['email'], NEW['pw'])
    page.goto(BASE + '/app/my-applications')
    page.get_by_role('cell', name=ctx_data['ref']).click()
    expect(page.get_by_text('Please correct the tax card number').first).to_be_visible()
    assert 'INTERNAL-NOTE' not in page.locator('main').inner_text()
    page.get_by_role('link', name='Correct and resubmit').click()
    page.get_by_label('Tax / VAT number').fill('TIN 6002119')
    page.get_by_role('button', name='Continue').click()
    expect(page.get_by_text('Contact & territory is not open for correction')).to_be_visible()
    expect(page.get_by_label('Contact full name')).to_be_disabled()
    page.get_by_role('button', name='Continue').click()
    page.get_by_role('button', name='Continue').click()
    d = tempfile.mkdtemp(); f = os.path.join(d, 'CR_Extract_2026.pdf'); open(f, 'wb').write(b'%PDF demo')
    page.get_by_role('button', name='Replace / withdraw').first.click()
    page.locator('input[type=file]').set_input_files([f])
    page.get_by_role('button', name='Continue').click()
    page.get_by_label('Message to the reviewer (optional)').fill('Tax number corrected and new extract attached.')
    page.get_by_label('I confirm the information provided is accurate and complete.').check()
    page.get_by_role('button', name='Resubmit application').click()
    page.wait_for_url('**/app/my-applications/*')
    expect(page.get_by_text('Resubmitted — waiting for review')).to_be_visible()
    login(page, 'priya')
    open_app(page, ctx_data['ref'])
    status_is(page, 'Resubmitted')
    page.get_by_role('tab', name=re.compile('Revisions')).click()
    expect(page.get_by_text('Revision 2', exact=True)).to_be_visible()
    expect(page.get_by_role('cell', name='TIN 6002119')).to_be_visible()
    page.get_by_role('tab', name=re.compile('Documents')).click()
    expect(page.get_by_text('Superseded (kept for audit)')).to_be_visible()


@scenario('A7 Request clarification → customer answers → back with the same reviewer')
def s07(page):
    act(page, 'Start review', 'Start review')
    act(page, 'Request clarification', 'Send request', {'Question for the applicant': 'Which warehouse will you use for Kuwait deliveries?'})
    status_is(page, 'Returned for Information')
    login(page, NEW['email'], NEW['pw'])
    page.goto(BASE + '/app/my-applications')
    page.get_by_role('cell', name=ctx_data['ref']).click()
    page.get_by_label('Your answer').fill('Our bonded warehouse in Shuwaikh.')
    page.get_by_role('button', name='Send answer').click()
    expect(page.get_by_text('Resubmitted — waiting for review')).to_be_visible()
    login(page, 'priya')
    page.goto(BASE + '/app/applications?tab=action')
    expect(page.get_by_role('cell', name=ctx_data['ref'])).to_be_visible()



@scenario('A8 Internal comment (reviewers only); approve → customer account activated, Customer Portal User role assigned, audit recorded')
def a8(page):
    login(page, 'priya')
    open_app(page, ctx_data['ref'])
    act(page, 'Start review', 'Start review')
    page.get_by_label('Internal comment').fill('INTCOMMENT-42: trade licence verified against registry.')
    page.get_by_role('button', name='Add comment').click()
    expect(page.get_by_text('INTCOMMENT-42').first).to_be_visible()
    page.get_by_role('button', name='Approve registration').click()
    dlg = page.get_by_role('dialog')
    dlg.get_by_role('button', name='Approve and activate account').click()
    status_is(page, 'Approved')
    page.get_by_role('tab', name=re.compile('Workflow history')).click()
    expect(page.get_by_text(re.compile('Customer Portal User role assigned')).first).to_be_visible()
    # applicant-safe view: no internal comment
    page.goto(ctx_data['link'].replace('http://localhost:4173', BASE))
    body = page.locator('main').inner_text()
    assert 'INTCOMMENT-42' not in body and 'Priya' not in body
    login(page, NEW['email'], NEW['pw'])
    expect(nav(page).get_by_role('link', name='My Customer Profile')).to_be_visible()
    expect(nav(page).get_by_role('link', name='Request Approvals')).to_have_count(0)  # customer approval ≠ sales approval rights
    page.goto(BASE + '/app/account')
    expect(page.get_by_role('heading', name='Pearl Bay Fragrances')).to_be_visible()
    login(page, 'elena')
    page.goto(BASE + '/app/admin/audit')
    page.get_by_label('Search audit trail').fill('Pearl Bay')
    expect(page.get_by_role('cell', name='Customer account activated from approved registration')).to_be_visible()


@scenario('A9 Duplicate registration: a registration number that already belongs to a customer is refused (no duplicate account)')
def a9(page):
    logout(page)
    register(page, 'dup.tester@example.com', 'Dup2026!x', 'DXB-CR-884213')
    expect(page.get_by_text(re.compile('already exists'))).to_be_visible()
    expect(page.get_by_role('heading', name='Customer application received')).to_have_count(0)


@scenario('B1 Reject needs a mandatory reason; the reason is shown to the applicant')
def b1(page):
    login(page, 'priya')
    open_app(page, 'APP-2026-0314')
    act(page, 'Start review', 'Start review')
    page.get_by_role('button', name='Reject', exact=True).click()
    dlg = page.get_by_role('dialog')
    dlg.get_by_role('button', name='Reject application').click()
    expect(dlg.get_by_role('alert')).to_contain_text('at least 10 characters')
    dlg.get_by_label('Reason shown to the applicant').fill('Online-only retail does not meet our selective distribution criteria.')
    dlg.get_by_role('button', name='Reject application').click()
    status_is(page, 'Rejected')
    logout(page)
    page.goto(BASE + '/track')
    page.get_by_label('Application reference').fill('APP-2026-0314')
    page.get_by_label('Registered email address').fill(U['tom'])
    page.get_by_role('button', name='Check status').click()
    expect(page.get_by_text('Online-only retail does not meet').first).to_be_visible()


@scenario('C1 Catalogue: images with labelled fallback, price per UoM, stock with UoM, honest stock-source label, over-stock warning')
def c1(page):
    login(page, 'omar')
    page.goto(BASE + '/app/catalog')
    expect(page.get_by_text('Prices & stock: demo data — not live SAP')).to_be_visible()
    page.get_by_placeholder('Search name, SKU or notes…').fill('Éclat')
    card = page.locator('li.card').filter(has_text='Éclat de Minuit')
    expect(card.get_by_text('Illustration', exact=True)).to_be_visible()
    expect(card.get_by_text(re.compile(r'per EA'))).to_be_visible()
    expect(card.get_by_text(re.compile(r'85 EA available'))).to_be_visible()
    card.get_by_label('Quantity of Éclat de Minuit', exact=True).fill('120')
    expect(card.get_by_text(re.compile('exceeds available stock'))).to_be_visible()
    # a product image URL that fails to load falls back to a labelled illustration
    page.evaluate("""() => { const k = 'tradeflow-demo-state'; const st = JSON.parse(localStorage.getItem(k));
        st.products.find(p => p.sku === 'LN-EDP-90-ECL').imageUrl = '/missing-product-image.png'; localStorage.setItem(k, JSON.stringify(st)); }""")
    page.reload()
    page.get_by_placeholder('Search name, SKU or notes…').fill('Éclat')
    expect(page.locator('li.card').filter(has_text='Éclat de Minuit').get_by_text('Image unavailable', exact=True)).to_be_visible()
    page.evaluate("""() => { const k = 'tradeflow-demo-state'; const st = JSON.parse(localStorage.getItem(k));
        delete st.products.find(p => p.sku === 'LN-EDP-90-ECL').imageUrl; localStorage.setItem(k, JSON.stringify(st)); }""")


@scenario('D1 Customer creates a sales request: products with prices & stock, totals, review/confirm → reference, status Pending Approval (not SAP)')
def d1(page):
    login(page, 'omar')
    page.goto(BASE + '/app/requests/new')
    page.get_by_placeholder('Search name, SKU or notes…').fill('Iris')
    page.get_by_role('button', name='Add Iris Poudré').click()
    page.get_by_role('button', name='Continue').click()
    expect(page.get_by_text(re.compile(r'/ EA')).first).to_be_visible()
    page.get_by_role('button', name='Continue').click()
    expect(page.get_by_text('Not calculated in prototype')).to_be_visible()
    expect(page.get_by_text('Estimated total (excl. tax & freight)')).to_be_visible()
    page.get_by_role('button', name='Continue').click()
    page.get_by_role('button', name='Continue').click()
    page.get_by_role('button', name='Submit for approval').click()
    page.get_by_role('dialog').get_by_role('button', name='Submit request').click()
    expect(page.get_by_role('heading', name='Request submitted')).to_be_visible(timeout=8000)
    expect(page.get_by_text('Prototype — saved in this browser only')).to_be_visible()
    ref = page.locator('span.font-mono').first.inner_text()
    assert re.match(r'SOR-\d{4}-\d{4}', ref), ref
    ctx_data['sor'] = ref
    page.get_by_role('link', name='Track request').click()
    status_is(page, 'Pending Approval')
    ctx_data['sor_url'] = page.url
    expect(page.get_by_role('button', name='Approve')).to_have_count(0)  # customer has no approval rights
    expect(page.get_by_role('heading', name='SAP submission')).to_have_count(0)


@scenario('E1 Sales rep approves → Approved · Pending SAP Submission (no SAP document); invoice blocked; submit to SAP → SAP Confirmed (mock)')
def e1(page):
    login(page, 'daniel')
    page.goto(BASE + '/app/approvals')
    expect(page.get_by_role('button', name=re.compile('Submitted to SAP'))).to_be_visible()  # KPI is a real filter
    page.get_by_placeholder('Request or customer…').fill(ctx_data['sor'])
    page.get_by_role('cell', name=ctx_data['sor']).click()
    page.get_by_role('button', name='Approve', exact=True).click()
    dlg = page.get_by_role('dialog')
    expect(dlg.get_by_text(re.compile('Approval alone does not create an SAP order'))).to_be_visible()
    dlg.get_by_label(re.compile('Submit to SAP straight after approval')).uncheck()
    dlg.get_by_role('button', name='Approve', exact=True).click()
    page.goto(ctx_data['sor_url'])
    expect(page.get_by_text('Pending SAP Submission').first).to_be_visible()
    expect(page.get_by_text('Not yet sent to SAP — no SAP document exists.')).to_be_visible()
    login(page, 'priya')
    page.goto(ctx_data['sor_url'])
    expect(page.get_by_role('button', name='Issue proforma invoice')).to_have_count(0)
    login(page, 'daniel')
    page.goto(ctx_data['sor_url'])
    page.get_by_role('button', name='Submit to SAP').click()
    expect(page.get_by_text('SAP Confirmed').first).to_be_visible(timeout=8000)
    expect(page.get_by_text(re.compile(r'MOCK-SO-\d+')).first).to_be_visible()
    expect(page.get_by_text('SAP: development mock — not connected').first).to_be_visible()
    login(page, 'priya')
    page.goto(ctx_data['sor_url'])
    expect(page.get_by_role('button', name='Issue proforma invoice')).to_be_visible()
    login(page, 'omar')
    page.goto(ctx_data['sor_url'])
    expect(page.get_by_text('Accepted for processing. Quantities confirmed.')).to_be_visible()
    expect(page.get_by_role('button', name=re.compile('Retry SAP|Submit to SAP'))).to_have_count(0)


@scenario('E2 Reject a sales request needs a mandatory reason')
def e2(page):
    login(page, 'daniel')
    page.goto(BASE + '/app/approvals/r-137')
    page.get_by_role('button', name='Reject', exact=True).click()
    dlg = page.get_by_role('dialog')
    dlg.get_by_role('button', name='Reject request').click()
    expect(dlg.get_by_text(re.compile('at least'))).to_be_visible()
    dlg.get_by_label('Reason for rejection').fill('Credit limit exceeded for this quarter — please resubmit next month.')
    dlg.get_by_role('button', name='Reject request').click()
    page.goto(BASE + '/app/requests/r-137')
    status_is(page, 'Rejected')


@scenario('E3 Failed SAP submission is recorded with the error and can be retried (SOR-2026-0127)')
def e3(page):
    login(page, 'priya')
    page.goto(BASE + '/app/approvals?tab=sap')
    expect(page.get_by_role('cell', name='SOR-2026-0127')).to_be_visible()
    page.goto(BASE + '/app/requests/r-127')
    expect(page.get_by_text(re.compile('Last attempt failed · GW-TIMEOUT'))).to_be_visible()
    expect(page.get_by_role('button', name='Issue proforma invoice')).to_have_count(0)
    page.get_by_role('button', name='Retry SAP submission').click()
    expect(page.get_by_text('SAP Confirmed').first).to_be_visible(timeout=8000)
    expect(page.get_by_role('button', name='Issue proforma invoice')).to_be_visible()
    page.goto(BASE + '/app/admin/integration')
    expect(page.get_by_text('SOR-2026-0127').first).to_be_visible()


@scenario('G1 Permissions: onboarding ≠ sales approval; typed URLs and direct actions are refused, not just hidden')
def g1(page):
    login(page, 'priya')  # onboarding approver: no sales approvals
    page.goto(BASE + '/app/approvals/r-136')
    expect(page.get_by_role('button', name='Approve', exact=True)).to_have_count(0)
    login(page, 'daniel')  # sales rep: territory applications are read-only
    page.goto(BASE + '/app/applications/a-007')
    expect(page.get_by_role('button', name='Approve registration')).to_have_count(0)
    expect(page.get_by_role('button', name='Start review')).to_have_count(0)
    page.goto(BASE + '/app/applications/a-001')  # outside his territories
    expect(page.get_by_text('Application not found')).to_be_visible()
    login(page, 'marcus')  # head of sales: reads all applications, decides none
    page.goto(BASE + '/app/applications/a-001')
    expect(page.get_by_role('button', name='Approve registration')).to_have_count(0)
    login(page, 'omar')
    for url in ('/app/approvals', '/app/applications', '/app/admin/users'):
        page.goto(BASE + url)
        expect(page.get_by_text('Error 403')).to_be_visible()
    page.goto(BASE + '/app/requests/r-124')  # another customer's request
    expect(page.get_by_text('Request not available')).to_be_visible()


@scenario('F1 First approval level has no previous approver — action disabled with reason')
def f1(page):
    login(page, 'daniel')
    page.goto(BASE + '/app/approvals/r-136')
    expect(page.get_by_role('button', name='Return to previous approver')).to_be_disabled()
    expect(page.locator('span[title*="no previous approver"]')).to_have_count(1)


@scenario('F2 Head of Sales returns a request to the Account Manager; earlier decision kept')
def f2(page):
    login(page, 'marcus')
    page.goto(BASE + '/app/approvals/r-145')
    page.get_by_role('button', name='Return to previous approver').click()
    d = page.get_by_role('dialog')
    d.get_by_label('Findings for the previous approver').fill('Please re-check the allocation against Q4 forecast.')
    d.get_by_role('button', name='Return to approver').click()
    login(page, 'daniel')
    page.goto(BASE + '/app/approvals')
    expect(page.get_by_role('cell', name=re.compile('SOR-2026-0145'))).to_be_visible()
    page.goto(BASE + '/app/approvals/r-145')
    page.get_by_role('tab', name='Approval history').click()
    expect(page.get_by_text('Earlier decisions at this level (1)').first).to_be_visible()


@scenario('G2 Missing application id shows a safe not-found state')
def g2(page):
    login(page, 'marcus')
    page.goto(BASE + '/app/applications/does-not-exist')
    expect(page.get_by_text('Application not found')).to_be_visible()


@scenario('G3 Invalid tracking reference with a valid email is rejected with the same generic message')
def g3(page):
    logout(page)
    page.goto(BASE + '/track')
    page.get_by_label('Application reference').fill('APP-2026-9999')
    page.get_by_label('Registered email address').fill(U['neema'])
    page.get_by_role('button', name='Check status').click()
    expect(page.get_by_text('We could not find an application matching those details')).to_be_visible()



# ─── H: existing functionality ─────────────────────────────────────────────

@scenario('H1 Customer Portal: edit own contacts (validated), statement with balance, sales history, inquiries — own data only')
def s11(page):
    login(page, 'omar')
    page.goto(BASE + '/app/account')
    page.get_by_role('textbox', name='Phone').first.fill('abc')
    page.get_by_role('button', name='Save changes').click()
    expect(page.get_by_role('alert')).to_contain_text('valid phone number')
    page.get_by_role('textbox', name='Phone').first.fill('+971 4 555 0999')
    page.get_by_role('button', name='Save changes').click()
    expect(page.get_by_text('Profile updated')).to_be_visible()
    page.get_by_role('tab', name=re.compile('Statement')).click()
    expect(page.get_by_text('Closing balance')).to_be_visible()
    page.get_by_role('tab', name=re.compile('Sales history')).click()
    expect(page.get_by_role('cell', name='SOR-2026-0136')).to_be_visible()
    page.get_by_role('tab', name=re.compile('Inquiries')).click()
    expect(page.get_by_role('link', name='New inquiry')).to_be_visible()
    page.goto(BASE + '/app/customers/c-002')
    expect(page.get_by_text('Customer not available')).to_be_visible()
    page.goto(BASE + '/app/customers')
    expect(page.get_by_text('Error 403')).to_be_visible()
    login(page, 'daniel')  # TSM is notified of the profile change
    page.goto(BASE + '/app/notifications')
    expect(page.get_by_text('Gulf Horizon Trading updated their profile')).to_be_visible()


@scenario('H2 Account Manager: only own-territory customers, records a visit, sees it on the customer and in activities')
def s12(page):
    login(page, 'daniel')
    page.goto(BASE + '/app/customers')
    expect(page.get_by_role('cell', name=re.compile('Al Noor'))).to_have_count(0)  # Saudi Arabia (Faisal)
    expect(page.get_by_role('cell', name=re.compile('Muscat Royal'))).to_be_visible()
    page.get_by_role('cell', name=re.compile('Muscat Royal')).click()
    page.get_by_role('button', name='Log visit / activity').click()
    d = page.get_by_role('dialog')
    d.get_by_label('Subject').fill('Merchandising visit — Muscat Grand Mall')
    d.get_by_label('Notes').fill('Gondola testers replenished.')
    d.get_by_role('button', name='Save activity').click()
    page.get_by_role('tab', name=re.compile('Visits & activities')).click()
    expect(page.get_by_text('Merchandising visit — Muscat Grand Mall')).to_be_visible()
    page.get_by_role('tab', name=re.compile('Sales history')).click()
    expect(page.get_by_role('cell', name='SOR-2026-0137')).to_be_visible()
    page.goto(BASE + '/app/activities')
    expect(page.get_by_text('Merchandising visit — Muscat Grand Mall')).to_be_visible()
    expect(page.get_by_text('Flagship store opening preparation')).to_have_count(0)  # Faisal's activity


@scenario('H3 Territory performance: Account Manager sees only own territories; Head of Sales compares all territories and managers')
def s13(page):
    login(page, 'daniel')
    page.goto(BASE + '/app/performance')
    rows = page.locator('table').first.locator('tbody tr')
    expect(rows).to_have_count(2)
    expect(page.get_by_label('Manager')).to_have_count(0)
    login(page, 'marcus')
    page.goto(BASE + '/app/performance')
    expect(page.locator('table').first.locator('tbody tr')).to_have_count(8)
    page.get_by_label('Manager').select_option(label='Daniel Okafor')
    expect(page.locator('table').first.locator('tbody tr')).to_have_count(2)
    page.get_by_label('Period').select_option('custom')
    expect(page.get_by_label('From date')).to_be_visible()
    expect(page.get_by_role('heading', name='Account Managers')).to_be_visible()


@scenario('H4 Moving a customer to another territory keeps its account and history; visibility follows the new territory')
def s14(page):
    login(page, 'marcus')
    page.goto(BASE + '/app/customers/c-010')
    page.get_by_role('tab', name='Territory').click()
    page.get_by_role('button', name='Move to another territory').click()
    d = page.get_by_role('dialog')
    d.get_by_label('New territory').select_option('t-ksa')
    d.get_by_label('Reason').fill('Kuwait accounts consolidated under the Riyadh sales office.')
    d.get_by_role('button', name='Move customer').click()
    expect(page.get_by_text('Kuwait accounts consolidated under the Riyadh sales office.')).to_be_visible()
    login(page, 'daniel')
    page.goto(BASE + '/app/customers/c-010')
    expect(page.get_by_text('Customer not available')).to_be_visible()
    login(page, 'faisal')
    page.goto(BASE + '/app/customers/c-010')
    page.get_by_role('tab', name=re.compile('Sales history')).click()
    expect(page.get_by_role('cell', name='SOR-2026-0144')).to_be_visible()  # history moved with the account


@scenario('H5 Head of Sales: consolidated access and order approvals but no system administration or onboarding decisions')
def s15(page):
    login(page, 'marcus')
    for hidden in ('Users', 'Roles & Permissions', 'Authorization Matrix', 'Audit Trail'):
        expect(nav(page).get_by_role('link', name=hidden, exact=True)).to_have_count(0)
    page.goto(BASE + '/app/admin/users')
    expect(page.get_by_text('Error 403')).to_be_visible()
    page.goto(BASE + '/app/customers')
    expect(page.get_by_role('cell', name=re.compile('Al Noor'))).to_be_visible()
    login(page, 'elena')  # administrator sees records but cannot decide applications
    page.goto(BASE + '/app/applications/a-001')
    expect(page.get_by_role('button', name='Approve registration')).to_have_count(0)


@scenario('H6 Login validation, generic invalid-credentials error, show/hide password, lockout; protected URL → sign-in with return path')
def s16(page):
    logout(page)
    page.goto(BASE + '/login')
    page.get_by_role('button', name='Sign in', exact=True).click()
    expect(page.get_by_text('Enter your email address.')).to_be_visible()
    page.get_by_label('Email').fill(U['dilshan'])
    pw = page.locator('input[autocomplete=current-password]')
    pw.fill('wrong-password-1')
    page.get_by_role('button', name='Show password').click()
    expect(pw).to_have_attribute('type', 'text')
    page.get_by_role('button', name='Sign in', exact=True).click()
    expect(page.get_by_text('Incorrect email or password.')).to_be_visible()
    page.get_by_label('Email').fill('nobody@nowhere.example'); pw.fill('whatever1')
    page.get_by_role('button', name='Sign in', exact=True).click()
    expect(page.get_by_text('Incorrect email or password.')).to_be_visible()
    page.get_by_label('Email').fill(U['dilshan'])
    for i in range(4):
        pw.fill(f'wrong-{i}x'); page.get_by_role('button', name='Sign in', exact=True).click(); page.wait_for_timeout(450)
    expect(page.get_by_text('Too many failed sign-in attempts')).to_be_visible()
    page.goto(BASE + '/app/admin/users')
    page.wait_for_url('**/login?next=*')
    page.get_by_label('Email').fill(U['elena'])
    page.locator('input[autocomplete=current-password]').fill(PW)
    page.get_by_role('button', name='Sign in', exact=True).click()
    page.wait_for_url('**/app/admin/users')


@scenario('H7 Typed URLs outside a role’s permissions show 403 and menus hide them (customer)')
def s17(page):
    login(page, 'omar')
    for hidden in ('Users', 'Customer Onboarding', 'Request Approvals', 'Territory Performance', 'Visits & Activities'):
        expect(nav(page).get_by_role('link', name=hidden, exact=True)).to_have_count(0)
    for url in ('/app/admin/users', '/app/applications', '/app/approvals', '/app/performance', '/app/activities', '/app/admin/territories'):
        page.goto(BASE + url)
        expect(page.get_by_text('Error 403')).to_be_visible()


@scenario('H8 Admin: multi-role user with assignments; permissions are data (matrix revoke/grant, critical locks); config changes audited')
def s18(page):
    login(page, 'elena')
    page.goto(BASE + '/app/admin/users')
    page.get_by_role('button', name='Add user').click()
    d = page.get_by_role('dialog')
    d.get_by_label('Full name').fill('Omari Test')
    d.get_by_label('Email (sign-in)').fill('omari.test@tradeflow.example')
    d.get_by_label('Temporary password').fill('Welcome2026')
    d.get_by_label(re.compile(r'^Sales Representative / Account Manager')).check()
    d.get_by_label(re.compile(r'^Read-only Auditor')).check()
    d.get_by_label('East Africa').check()
    d.get_by_role('button', name='Create user').click()
    login(page, 'omari.test@tradeflow.example', 'Welcome2026')
    expect(nav(page).get_by_role('link', name='Audit Trail')).to_be_visible()
    expect(nav(page).get_by_role('link', name='Territory Performance')).to_be_visible()
    login(page, 'elena')
    page.goto(BASE + '/app/admin/authorization')
    page.get_by_label('Search permissions').fill('View catalog')
    page.get_by_role('checkbox', name='View catalog — Customer Portal User: granted').click()
    page.get_by_label('Search permissions').fill('Manage users')
    expect(page.get_by_role('checkbox', name=re.compile('Manage users — Administrator'))).to_have_count(0)
    login(page, 'omar')
    expect(nav(page).get_by_role('link', name='Product Catalog')).to_have_count(0)
    login(page, 'elena')
    page.goto(BASE + '/app/admin/authorization')
    page.get_by_label('Search permissions').fill('View catalog')
    page.get_by_role('checkbox', name='View catalog — Customer Portal User: not granted').click()
    page.goto(BASE + '/app/admin/workflow')
    page.get_by_role('switch', name=re.compile('Credit & compliance check.* active')).click()
    page.get_by_role('button', name='Save workflow').click()
    expect(page.get_by_text(re.compile('No active user has the role'))).to_be_visible()  # optional Finance role has no users
    page.goto(BASE + '/app/admin/audit')
    page.get_by_label('Search audit trail').fill('catalog.view')
    expect(page.get_by_role('cell', name='Permission revoked')).to_be_visible()
    page.get_by_label('Search audit trail').fill('Kuwait accounts')
    expect(page.get_by_role('cell', name='Customer moved to another territory')).to_be_visible()


OUT = os.environ.get('OUT', tempfile.mkdtemp())
with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context(viewport={'width': 1440, 'height': 1000})
    page = context.new_page()
    page.set_default_timeout(8000)
    page.on('pageerror', lambda e: console_errors.append(str(e)))
    page.on('console', lambda m: m.type == 'error' and 'ERR_TUNNEL' not in m.text and 'fonts.g' not in m.text and 'missing-product-image' not in (m.location or {}).get('url', '') and console_errors.append(m.text))
    page.goto(BASE + '/login')
    page.evaluate('localStorage.clear()')
    for fn in (s01, s02, s03, s04, s05, s06, s07, a8, a9, b1, c1, d1, e1, e2, e3, f1, f2, g1, g2, g3, s11, s12, s13, s14, s15, s16, s17, s18):
        fn(page)
    browser.close()

passed = sum(1 for r in results if r[1])
print(f'\n{passed}/{len(results)} passed · console errors: {len(console_errors)}')
for e in console_errors[:10]:
    print('  console:', e[:200])
sys.exit(0 if passed == len(results) and not console_errors else 1)
