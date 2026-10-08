"""Synthetic source-layout tests; no copied publisher descriptions or HTML."""
import pytest
from scripts.collect_genova_tosse import (INDEX_URL, SAMPLE_URLS, collect, detail_url,
                                         parse_detail, parse_index)
from scripts.probe_giardini_luzzati import ProbeSkipped, _Response
URL = SAMPLE_URLS[2]

def page(rows):
    return '<h1>Fixture performance</h1><p>15/10/2026 14:00 promotional time</p><h2>Programmazione</h2><table>' + rows + '</table><h2>Altri spettacoli</h2><table><tr><td>01/12/2030</td><td>09:00</td><td>La Claque</td></tr></table>'

def row(date, clock='20:30', venue='Sala Aldo Trionfo'):
    return f'<tr><td>{date}</td><td>{clock}</td><td>€10</td><td>{venue}</td><td>Prenota</td></tr>'

def test_separate_showtimes_no_range_expansion_or_related_events():
    html = page(''.join(row(f'{day}/10/2026', '18:30' if day in (18,25) else '20:30') for day in (15,16,17,18,20,21,22,23,24,25)))
    report = parse_detail(html, URL)
    assert len(report['events']) == 10
    assert len({e['source_uid'] for e in report['events']}) == 10
    assert all(e['url'] == URL and e['start_time'].endswith('+01:00' if e['start_time'][8:10] == '25' else '+02:00') for e in report['events'])
    assert all(e['start_time'][8:10] != '19' for e in report['events'])
    assert all('description' not in e and 'html' not in e and '€' not in str(e) for e in report['events'])

def test_missing_year_time_and_unknown_venue():
    assert not parse_detail(page(row('15/10', '20:30')), URL)['events']
    assert not parse_detail(page(row('15/10/2026', '')), URL)['events']
    report = parse_detail(page(row('15/10/2026', venue='Unknown room')), URL)
    assert report['events'][0]['location'] is None
    assert 'location_missing_or_unsupported' in report['unresolved_reasons']

@pytest.mark.parametrize('date,clock,expected', [('15/01/2027','20:30','+01:00'),('15/07/2027','20:30','+02:00'),('29/02/2027','20:30',None),('29/03/2026','02:30',None),('25/10/2026','02:30',None)])
def test_calendar_and_dst(date,clock,expected):
    events = parse_detail(page(row(date,clock)), URL)['events']
    assert (events[0]['start_time'][-6:] if events else None) == expected

def test_responsive_schedule_date_intervals_and_duplicate_rows():
    html = '<h1>Fixture music</h1><h2>Programmazione</h2><div>15/10/2026 20:30 La Claque</div><div>16/10/2026 18:30 La Claque</div><h2>Altri spettacoli</h2><p>17/10/2026 09:00</p>'
    report = parse_detail(html, URL)
    assert len(report['events']) == 2
    assert report['events'][0]['category'] == 'music'
    assert len(parse_detail(page(row('15/10/2026')*2), URL)['events']) == 1

@pytest.mark.parametrize('url',[INDEX_URL,'http://teatrodellatosse.it/eventi/show.htm','https://other.test/eventi/show.htm',SAMPLE_URLS[0]+'?x=1','https://teatrodellatosse.it/eventi/../bad.htm','https://teatrodellatosse.it:443/eventi/show.htm'])
def test_url_allowlist(url):
    assert not detail_url(url)

def test_index_only_detail_links_deduplicated():
    html = f'<a href="{URL}">Fixture</a><a href="{URL}">Image</a><a href="/eventi/">Index</a><a href="https://other.test/eventi/x.htm">Foreign</a>'
    assert parse_index(html) == [URL]

def test_bounded_sample_mode_no_index_fetch():
    requests=[]
    def get(url):
        requests.append(url)
        return _Response(200,url,b'User-agent: *\nAllow: /\n' if url.endswith('robots.txt') else page(row('15/10/2026')).encode())
    report = collect(get=get,sleeper=lambda _:None,detail_limit=2,sample_only=True)
    assert INDEX_URL not in requests
    assert report['access']['request_count'] == 3
    assert report['persistence'] == 'none'

def test_index_cap_and_stop_on_rate_limit():
    requests=[]
    def get(url):
        requests.append(url)
        if url.endswith('robots.txt'):
            return _Response(200,url,b'User-agent: *\nAllow: /')
        if url == INDEX_URL:
            return _Response(200,url,''.join(f'<a href="{u}">Event</a>' for u in SAMPLE_URLS).encode())
        return _Response(429,url,b'')
    with pytest.raises(ProbeSkipped, match='429'):
        collect(get=get,sleeper=lambda _:None,detail_limit=3)
    assert len(requests) == 3

def test_robots_denial_prevents_detail_request():
    requests=[]
    def get(url):
        requests.append(url)
        return _Response(200,url,b'User-agent: *\nDisallow: /eventi/')
    with pytest.raises(ProbeSkipped,match='disallows'):
        collect(get=get,sleeper=lambda _:None,sample_only=True)
    assert len(requests)==1

@pytest.mark.parametrize('limit',[0,4,True,-1])
def test_invalid_cap_no_network(limit):
    with pytest.raises(ProbeSkipped):
        collect(get=lambda _:pytest.fail('unexpected network'), detail_limit=limit)
