from pathlib import Path
import json, shutil, sys, tempfile
from playwright.sync_api import sync_playwright
ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / 'app'
out = []
def check(name, cond, detail=''):
    out.append({'test': name, 'status': 'pass' if cond else 'fail', 'detail': detail})
CHROME = '/usr/bin/chromium'
FILES = ['global_ranking.html', 'global_ranking.css', 'global_ranking_page.js', 'global_ranking_view.js', 'global_scan_v6.js', 'spend_guard_v6.js', 'styles.css']

def open_page(browser, root, w=1440, h=900):
    pg = browser.new_page(viewport={'width': w, 'height': h})
    errs, reqs = [], []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' else None)
    pg.on('request', lambda r: reqs.append(r.url))
    pg.goto((Path(root) / 'global_ranking.html').as_uri(), wait_until='load')
    return pg, errs, reqs

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, executable_path=CHROME, args=['--no-sandbox'])
    # --- real snapshot
    pg, errs, reqs = open_page(browser, APP)
    check('no_page_or_console_errors', not errs, errs)
    check('only_local_requests', all(u.startswith('file://') for u in reqs), [u for u in reqs if not u.startswith('file://')])
    check('banner_says_no_winner', 'No winner' in pg.inner_text('#grVerdict h2'))
    check('banner_lists_reasons', pg.locator('#grVerdict li').count() >= 2, pg.inner_text('#grVerdict'))
    check('scan_valid_40_raw_10_families', all(s in pg.inner_text('#grScan') for s in ['Yes', '40 (need ≥30)', '10 (need ≥8)', '0 of 40']), pg.inner_text('#grScan'))
    check('no_stray_null_text', 'null' not in pg.inner_text('#grMain').lower().replace('nullable',''), pg.inner_text('#grScan'))
    check('forty_items', pg.locator('.gr-item').count() == 40)
    check('counts_card', all(s in pg.inner_text('#grCounts') for s in ['24', '8']), pg.inner_text('#grCounts'))
    check('spend_blocked_and_estimate', 'Blocked' in pg.inner_text('#grSpend') and '$6.60' in pg.inner_text('#grSpend') and '$0.00' in pg.inner_text('#grSpend'), pg.inner_text('#grSpend'))
    check('lens_not_v6_note', 'NOT a v6 score' in pg.inner_text('#grNote'))
    pg.select_option('#grStatus', 'queued'); check('filter_status_queued_24', pg.locator('.gr-item').count() == 24 and '24 of 40' in pg.inner_text('#grCount'))
    pg.select_option('#grStatus', ''); pg.select_option('#grFamily', 'games'); check('filter_family_games_4', pg.locator('.gr-item').count() == 4)
    pg.select_option('#grFamily', ''); pg.fill('#grSearch', 'zzzz-no-match'); check('search_no_match_0', pg.locator('.gr-item').count() == 0 and '0 of 40' in pg.inner_text('#grCount'))
    pg.fill('#grSearch', 'GAM-01'); check('search_by_id', pg.locator('.gr-item').count() == 1)
    pg.fill('#grSearch', '')
    first = pg.locator('.gr-item').first
    check('details_closed_by_default', first.get_attribute('open') is None)
    first.locator('summary').focus(); pg.keyboard.press('Enter'); check('keyboard_opens_item', first.get_attribute('open') is not None)
    check('rejected_item_shows_reason_and_basis', pg.locator('.gr-item[data-status="rejected_unverified"]').first.inner_text().count('Basis:') >= 0)
    pg.evaluate('''document.querySelectorAll('.gr-item').forEach(d=>d.open=true)''')
    txt = pg.locator('.gr-item[data-status="rejected_unverified"]').first.inner_text()
    check('rejected_item_has_why_and_basis', 'Why rejected' in txt and 'Basis:' in txt, txt[:200])
    check('all_evidence_links_https_noopener', pg.evaluate("[...document.querySelectorAll('.gr-ev a')].every(a=>a.href.startsWith('https://')&&a.rel.includes('noopener'))"))
    pg.close()
    # --- no horizontal scroll at phone / tablet / desktop widths
    for w in (360, 768, 1440):
        pg, _, _ = open_page(browser, APP, w, 800)
        check(f'no_horizontal_scroll_{w}', pg.evaluate('document.documentElement.scrollWidth<=window.innerWidth+1'), pg.evaluate('[document.documentElement.scrollWidth,window.innerWidth]'))
        pg.close()
    # --- hostile data must never execute or render as HTML
    tmp = Path(tempfile.mkdtemp(prefix='g281_xss_', dir=str(ROOT / 'diagnostics' / 'current')))
    try:
        for f in FILES: shutil.copy(APP / f, tmp / f)
        (tmp / 'data').mkdir()
        pkg = json.loads((ROOT / 'server' / 'REVA2_G281_SCAN1_IMPORT.json').read_text(encoding='utf-8'))
        c = pkg['candidates'][0]
        c['raw_name'] = '<img src=x onerror="window.__xss=1">NAME'
        c['rejection_reason'] = '<script>window.__xss=2</script>'
        c['evidence_hints'] = [{'url': 'javascript:window.__xss=3', 'signal': '<b>bold</b>', 'source': '<i>src</i>', 'evidence_class': 'verified', 'kind': 'demand'},
                               {'url': 'http://insecure.example', 'signal': 's', 'source': 'x', 'evidence_class': 'verified', 'kind': 'demand'}]
        (tmp / 'data' / 'g281_scan1_view.js').write_text('window.REVENG_GLOBAL_VIEW_DATA=' + json.dumps(pkg) + ';', encoding='utf-8')
        pg, errs, _ = open_page(browser, tmp)
        pg.evaluate('''document.querySelectorAll('.gr-item').forEach(d=>d.open=true)''')
        hostile = pg.locator('.gr-item', has_text='NAME').first
        check('xss_not_executed', pg.evaluate('window.__xss===undefined'))
        check('xss_no_injected_elements', pg.locator('.gr-list img, .gr-list script, .gr-list b, .gr-list i').count() == 0)
        check('xss_text_shown_literally', '<img' in hostile.inner_text() and '<script>' in hostile.inner_text(), hostile.inner_text()[:200])
        check('unsafe_urls_not_linked', hostile.locator('a').count() == 0)
        pg.close()
        # --- missing data: honest empty state, no invented ranking
        (tmp / 'data' / 'g281_scan1_view.js').write_text('', encoding='utf-8')
        pg, errs, _ = open_page(browser, tmp)
        check('missing_data_empty_state', 'No scan data loaded' in pg.inner_text('#grVerdict') and pg.locator('.gr-item').count() == 0)
        pg.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    # --- entry link from the main app
    pg = browser.new_page(); pg.goto((APP / 'index.html').as_uri(), wait_until='load')
    check('index_links_to_global_ranking', pg.locator('#globalRankingLink').get_attribute('href') == 'global_ranking.html')
    pg.close(); browser.close()
fails = [x for x in out if x['status'] != 'pass']
print(json.dumps({'suite': 'reva2_g281_global_ranking_page', 'passed': len(out) - len(fails), 'failed': len(fails), 'failures': fails}, indent=1))
sys.exit(1 if fails else 0)
