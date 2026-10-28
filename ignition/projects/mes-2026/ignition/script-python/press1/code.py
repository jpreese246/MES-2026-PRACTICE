# press1 -- Press 1 SCADA view (VIS-001). Raw PLC data only; no MES logic, no history.
#
# A gateway timer (ignition/timer/press1Tick, 2000 ms fixed delay) calls tick(), which
# reads the 16 MQTT Engine string tags, unwraps the UNS Studio envelope, casts once and
# appends one row to a rolling in-memory buffer. Perspective bindings call the read
# functions at the bottom; views never parse JSON or compute events themselves.
#
# State lives in system.util.getGlobals()[STORE_KEY], which persists for the JVM's
# lifetime (shared by gateway scripts and Perspective sessions). Only plain dicts,
# lists, numbers and strings go in it. The buffer is lost on a gateway restart.

from java.time import Instant

# The single place a tag path starts from. MQTT Engine custom namespace "All", no root folder.
ROOT = '[MQTT Engine]40Printing/Dallas/Press Room/Press 1'

# (key, sub-path, cast)
TAGS = [
	('conn',   'PLC/Connected',                   'bool'),
	('state',  'PLC/MachineState',                'int'),
	('fault',  'PLC/FaultCode',                   'int'),
	('product','PLC/ProductCode',                 'int'),
	('lanes',  'PLC/WebLanes',                    'int'),
	('good',   'PLC/GoodMeters',                  'float'),
	('reject', 'PLC/RejectMeters',                'float'),
	('rto',    'PLC/RTOInhibit',                  'bool'),
	('tenU',   'Unwind/WebTension',               'float'),
	('tenR',   'Rewind/WebTension',               'float'),
	('speed',  'Print Section/LineSpeed',         'float'),
	('reg',    'Print Section/RegistrationError', 'float'),
	('visc',   'Print Section/InkViscosity',      'float'),
	('z1',     'Tunnel Dryer/Zone1Temp',          'float'),
	('z2',     'Tunnel Dryer/Zone2Temp',          'float'),
	('z3',     'Tunnel Dryer/Zone3Temp',          'float'),
]
KEYS = [k for k, _, _ in TAGS]
PATHS = [ROOT + '/' + p for _, p, _ in TAGS]

MAX_ROWS = 1800     # 60 min at 2 s
MAX_EVENTS = 200    # closed events kept, newest first (matches the reference dashboard)
MAX_JOBS = 50       # jobs kept; the table shows the newest 12 (matches the reference dashboard)
DEBOUNCE = 2        # consecutive samples in the same (state, fault) before an event opens
STALE_S = 10        # no new sample for this long -> header shows NO DATA
GAP_S = 10          # rows further apart than this are a sampling break (e.g. the host slept)
TEMP_LIMIT = 200    # degF display line only, not a PLC setpoint
STORE_VERSION = 2
STORE_KEY = 'press1.v%d' % STORE_VERSION  # versioned key: a stale copy of older code (e.g. an open Designer) can't clobber the live store

STATE_NAME = {1: 'Running', 2: 'Setup', 3: 'Faulted'}
FAULT_NAME = {101: 'Web break', 102: 'Tunnel over-temp', 103: 'RTO inhibit'}

log = system.util.getLogger('press1')


# ---------- store ----------

def _store():
	g = system.util.getGlobals()
	st = g.get(STORE_KEY)
	if st is None:
		st = {
			'version': STORE_VERSION,
			'started': system.date.toMillis(system.date.now()),
			'rows': [],          # one dict per sample, oldest first
			'events': [],        # closed events, newest first
			'open_event': None,
			'run': None,         # current run of identical (state, fault): key, start, n
			'jobs': [],          # contiguous ProductCode runs since gateway start, oldest first
			'warned': {},        # tag key -> True once a bad read has been logged
			'browsed': False,
		}
		g[STORE_KEY] = st
	return st


# ---------- ingest ----------

def _cast(raw, kind):
	if raw is None:
		return None
	if kind == 'bool':
		if isinstance(raw, basestring):
			s = raw.strip().lower()
			if s in ('true', '1'):
				return True
			if s in ('false', '0'):
				return False
			return None
		return bool(raw)
	if kind == 'int':
		return int(round(float(raw)))
	return float(raw)


def _epoch_ms(iso):
	# ISO 8601 UTC with microseconds, e.g. 2026-10-20T19:00:51.377788Z
	return Instant.parse(iso).toEpochMilli()


def _warn_once(st, key, msg):
	if not st['warned'].get(key):
		st['warned'][key] = True
		log.warn('%s: %s' % (key, msg))


def _read(st):
	"""One aligned snapshot of all 16 tags -> (values dict, state timestamp ms or None)."""
	qvs = system.tag.readBlocking(PATHS)
	vals = {}
	ts = None
	bad = 0
	for (key, sub, kind), qv in zip(TAGS, qvs):
		vals[key] = None
		if not qv.quality.isGood() or qv.value is None:
			bad += 1
			_warn_once(st, key, 'bad read %s at %s/%s' % (qv.quality, ROOT, sub))
			continue
		try:
			env = system.util.jsonDecode(qv.value)
			vals[key] = _cast(env.get('value'), kind)
			if key == 'state':
				ts = _epoch_ms(env.get('timestamp'))
		except Exception, e:
			_warn_once(st, key, 'cannot parse %r (%s)' % (qv.value, e))
	if bad == len(TAGS) and not st['browsed']:
		# First total failure: log what the provider actually holds, so the path can be fixed.
		st['browsed'] = True
		try:
			found = [str(r['fullPath']) for r in system.tag.browse('[MQTT Engine]').getResults()]
			log.warn('all reads bad; [MQTT Engine] top level: %s' % found)
		except Exception, e:
			log.warn('all reads bad; browse failed: %s' % e)
	return vals, ts


def _meter_delta(cur, prev):
	"""(delta, restart). A drop means the sim restarted: delta 0, not negative production."""
	if cur is None or prev is None:
		return 0.0, False
	if cur >= prev:
		return cur - prev, False
	return 0.0, True


def _close_event(st, t):
	ev = st['open_event']
	if ev is None:
		return
	ev['end'] = t
	ev['dur_s'] = (t - ev['start']) / 1000.0
	st['events'].insert(0, ev)
	del st['events'][MAX_EVENTS:]
	st['open_event'] = None


def _events(st, row):
	key = [row['state'], row['fault'] if row['state'] == 3 else 0]
	run = st['run']
	if run is None or run['key'] != key:
		# First sample that differs closes the open event (a fault-code change inside Faulted too).
		_close_event(st, row['t'])
		run = st['run'] = {'key': key, 'start': row['t'], 'n': 0}
	run['n'] += 1
	if run['n'] == DEBOUNCE and key[0] in (2, 3):
		st['open_event'] = {
			'start': run['start'],   # backdated to the first of the debounce samples
			'end': None,
			'dur_s': None,
			'kind': 'Alarm' if key[0] == 3 else 'Setup',
			'code': key[1] if key[0] == 3 else None,
			'product': row['product'],
		}


def _jobs(st, row, gap=False):
	jobs = st['jobs']
	if row['product'] is None:
		return
	job = jobs[-1] if jobs else None
	# After a sampling break start a new entry even on the same ProductCode; the gap row's deltas go nowhere.
	if job is None or gap or job['product'] != row['product']:
		jobs.append({'product': row['product'], 'lanes': row['lanes'], 'first': row['t'], 'last': row['t'],
					 'good': 0.0, 'reject': 0.0, 'reset': False})
		del jobs[:-MAX_JOBS]
		return
	job['last'] = row['t']
	job['lanes'] = row['lanes']
	job['good'] += row['dg']
	job['reject'] += row['dr']
	if row['restart']:
		job['reset'] = True


def tick():
	st = _store()
	vals, ts = _read(st)
	if ts is None or vals['state'] is None:
		return
	rows = st['rows']
	prev = rows[-1] if rows else None
	# De-duplicate on the MachineState envelope timestamp: timer and sim drift around 2 s.
	if prev is not None and ts <= prev['t']:
		return
	gap = False
	if prev is not None and ts - prev['t'] > GAP_S * 1000:
		# Sampling break: close at the last sample before the gap, not the first after it, and restart the debounce.
		_close_event(st, prev['t'])
		st['run'] = None
		gap = True
	row = dict(vals)
	row['t'] = ts
	dg, rg = _meter_delta(vals['good'], prev['good'] if prev else None)
	dr, rr = _meter_delta(vals['reject'], prev['reject'] if prev else None)
	row['dg'] = dg
	row['dr'] = dr
	row['restart'] = rg or rr
	rows.append(row)
	if len(rows) > MAX_ROWS:
		del rows[:len(rows) - MAX_ROWS]
	_events(st, row)
	_jobs(st, row, gap)


# ---------- formatting helpers (display text only) ----------

def _fmt_time(ms):
	return system.date.format(system.date.fromMillis(long(ms)), 'HH:mm:ss')


def _fmt_dur(s):
	if s is None:
		return '-'
	if s >= 60:
		return '%dm %ds' % (int(s // 60), int(round(s % 60)))
	return '%ds' % int(round(s))


def _now_ms():
	return system.date.toMillis(system.date.now())


def _window(st, window_min):
	rows = list(st['rows'])
	if not window_min:
		return rows
	cutoff = _now_ms() - int(window_min) * 60000
	return [r for r in rows if r['t'] >= cutoff]


def _alarm_name(code):
	return FAULT_NAME.get(code, 'Unclassified alarm')


# ---------- read API (called from Perspective bindings) ----------

def latest():
	"""Latest buffer row plus the display text and flags the views bind to."""
	st = _store()
	rows = st['rows']
	if not rows:
		return {'ok': False, 'banner': 'WAITING FOR DATA', 'state_cls': 'state-0', 'job': u'Job - \u00b7 --wide',
				'live_text': 'NO DATA', 'live_cls': 'pill-bad', 'rto_text': 'RTO -', 'rto_cls': 'pill-bad',
				'conn_text': 'PLC -', 'conn_cls': 'pill-bad', 'rto_permissive': '-'}
	r = dict(rows[-1])
	s, code = r['state'], r['fault']
	if s == 1:
		banner = 'RUNNING'
	elif s == 2:
		banner = u'SETUP \u2014 changeover'
	elif s == 3:
		banner = u'FAULTED \u2014 ' + _alarm_name(code) + (' (code %d)' % code if code else '')
	else:
		banner = 'Unknown'
	age_s = (_now_ms() - r['t']) / 1000.0
	if age_s > STALE_S:
		live_text, live_cls = 'NO DATA', 'pill-bad'
	elif r['conn']:
		live_text, live_cls = 'LIVE', 'pill-good'
	else:
		live_text, live_cls = 'PLC DISCONNECTED', 'pill-bad'
	good, rej = r['good'], r['reject']
	scrap = rej / (good + rej) * 100.0 if good is not None and rej is not None and good + rej > 0 else None
	web_fault = s == 3 and code == 101
	heat_fault = s == 3 and code in (102, 103)

	def num(v, d):
		return '-' if v is None else ('%.' + str(d) + 'f') % v

	def commas(v):
		return '-' if v is None else '{:,}'.format(int(round(v)))

	def hot(v):
		return v is not None and v >= TEMP_LIMIT

	r.update({
		'ok': True,
		'age_s': age_s,
		'banner': banner,
		'state_cls': 'state-%d' % s if s in STATE_NAME else 'state-0',
		'job': u'Job %s \u00b7 %s-wide' % (r['product'] if r['product'] is not None else '-',
										  r['lanes'] if r['lanes'] is not None else '-'),
		'live_text': live_text,
		'live_cls': live_cls,
		'rto_text': 'RTO INHIBIT ACTIVE' if r['rto'] else 'RTO CLEAR',
		'rto_cls': 'pill-bad' if r['rto'] else 'pill-good',
		'rto_permissive': u'INHIBIT \u2014 press cannot run' if r['rto'] else 'Clear',
		'conn_text': 'PLC CONNECTED' if r['conn'] else 'PLC DISCONNECTED',
		'conn_cls': 'pill-good' if r['conn'] else 'pill-bad',
		'speed_t': num(r['speed'], 1), 'reg_t': num(r['reg'], 2), 'visc_t': num(r['visc'], 1),
		'tenU_t': num(r['tenU'], 1), 'tenR_t': num(r['tenR'], 1),
		'z1_t': num(r['z1'], 1), 'z2_t': num(r['z2'], 1), 'z3_t': num(r['z3'], 1),
		'product_t': '-' if r['product'] is None else str(r['product']),
		'lanes_t': '-' if r['lanes'] is None else str(r['lanes']),
		'good_t': commas(good), 'reject_t': commas(rej),
		'scrap': scrap, 'scrap_t': num(scrap, 1),
		'scrap_cls': 'val-warn' if scrap is not None and scrap > 4 else 'val',
		'web_fault': web_fault, 'heat_fault': heat_fault,
		'unwind_cls': 'section-fault' if web_fault else 'section-' + ('state-%d' % s if s in STATE_NAME else 'state-0'),
		'rewind_cls': 'section-fault' if web_fault else 'section-' + ('state-%d' % s if s in STATE_NAME else 'state-0'),
		'print_cls': 'section-' + ('state-%d' % s if s in STATE_NAME else 'state-0'),
		'dryer_cls': 'section-fault' if heat_fault else 'section-' + ('state-%d' % s if s in STATE_NAME else 'state-0'),
		'tension_cls': 'row-val-bad' if web_fault else 'row-val',
		'z1_cls': 'row-val-bad' if hot(r['z1']) else 'row-val',
		'z2_cls': 'row-val-bad' if hot(r['z2']) else 'row-val',
		'z3_cls': 'row-val-bad' if hot(r['z3']) else 'row-val',
		'z1_pct': 0 if r['z1'] is None else max(0, min(100, r['z1'] / 250.0 * 100)),
		'z2_pct': 0 if r['z2'] is None else max(0, min(100, r['z2'] / 250.0 * 100)),
		'z3_pct': 0 if r['z3'] is None else max(0, min(100, r['z3'] / 250.0 * 100)),
		'z1_bar': 'bar-bad' if hot(r['z1']) else 'bar-good',
		'z2_bar': 'bar-bad' if hot(r['z2']) else 'bar-good',
		'z3_bar': 'bar-bad' if hot(r['z3']) else 'bar-good',
		'z1_big': 'zone-val-bad' if hot(r['z1']) else 'zone-val',
		'z2_big': 'zone-val-bad' if hot(r['z2']) else 'zone-val',
		'z3_big': 'zone-val-bad' if hot(r['z3']) else 'zone-val',
	})
	return r


def rows(window_min, keys=None):
	"""Rows in the window as [{'time': ms, key: value, ...}], oldest first, for the Time Series Chart."""
	st = _store()
	keys = keys or KEYS
	out = []
	for r in _window(st, window_min):
		d = {'time': r['t']}
		for k in keys:
			v = r.get(k)
			d[k] = None if v is None else float(v)
		out.append(d)
	return out


def events():
	"""Event log, newest first: the open event (if any) then closed events."""
	st = _store()
	evs = list(st['events'])
	if st['open_event'] is not None:
		evs.insert(0, st['open_event'])
	out = []
	for e in evs:
		alarm = e['kind'] == 'Alarm'
		out.append({
			'start': _fmt_time(e['start']),
			'type': e['kind'],
			'type_cls': 'td-alarm' if alarm else 'td-setup',
			'detail': (_alarm_name(e['code']) + (' (%d)' % e['code'] if e['code'] else '')) if alarm else 'Changeover',
			'job': '-' if e['product'] is None else str(e['product']),
			'duration': 'active' if e['end'] is None else _fmt_dur(e['dur_s']),
		})
	return out


def alarm_summary(window_min=None):
	"""Count and total time per alarm class since gateway start (window_min is ignored; see VIS-001)."""
	st = _store()
	alarms = [e for e in st['events'] if e['kind'] == 'Alarm']
	ev = st['open_event']
	rows_ = st['rows']
	if ev is not None and ev['kind'] == 'Alarm':
		# An active alarm counts, with its time so far up to the latest sample.
		alarms.append({'code': ev['code'], 'dur_s': (rows_[-1]['t'] - ev['start']) / 1000.0 if rows_ else 0})
	out = []
	for code in (101, 102, 103, None):
		if code is None:
			sel = [a for a in alarms if a['code'] not in FAULT_NAME]
		else:
			sel = [a for a in alarms if a['code'] == code]
		out.append({
			'code': 'other' if code is None else str(code),
			'alarm': _alarm_name(code),
			'count': len(sel),
			'total': _fmt_dur(sum([a['dur_s'] or 0 for a in sel])),
		})
	return out


def state_percent(window_min):
	"""% of time in each state over the window, weighted by sample timestamps."""
	st = _store()
	rs = _window(st, window_min)
	secs = {1: 0.0, 2: 0.0, 3: 0.0}
	total = 0.0
	for a, b in zip(rs, rs[1:]):
		dt = (b['t'] - a['t']) / 1000.0
		if dt > GAP_S:
			continue  # a sampling break counts toward neither a state nor the total
		total += dt
		if a['state'] in secs:
			secs[a['state']] += dt
	pct = lambda s: '-' if total <= 0 else '%.0f' % (secs[s] / total * 100)
	return {'running': pct(1), 'setup': pct(2), 'faulted': pct(3)}


def jobs(limit=12):
	"""Jobs observed since gateway start, newest first, as table rows."""
	st = _store()
	out = []
	js = list(st['jobs'])
	for i, j in enumerate(list(reversed(js))[:limit]):
		out.append({
			'product': str(j['product']) + ('  (current)' if i == 0 else ''),
			'lanes': '-' if j['lanes'] is None else str(j['lanes']),
			'first': _fmt_time(j['first']),
			'last': _fmt_time(j['last']),
			'good': '-' if j['reset'] else '{:,}'.format(int(round(j['good']))),
			'reject': '-' if j['reset'] else '{:,}'.format(int(round(j['reject']))),
		})
	return out


def cells(rows_, fields, empty):
	"""Flex Repeater instances for a Press1/Parts table row: text c0..cN and style class k0..kN.
	A field's class comes from '<field>_cls' when the row has one, else 'td'."""
	if not rows_:
		d = dict([('c%d' % i, '') for i in range(len(fields))] + [('k%d' % i, 'td') for i in range(len(fields))])
		d['c0'] = empty
		return [d]
	out = []
	for r in rows_:
		d = {}
		for i, f in enumerate(fields):
			d['c%d' % i] = r[f]
			d['k%d' % i] = r.get(f + '_cls', 'td')
		out.append(d)
	return out


def buffer_info(window_min=None):
	"""Sample counts for trend footers and the header note."""
	st = _store()
	rows_ = st['rows']
	n = len(_window(st, window_min)) if window_min else len(rows_)
	return {
		'samples': n,
		'total': len(rows_),
		'started': _fmt_time(st['started']),
		'footer': 'gateway buffer, %d samples' % n,
		'note': 'Trends come from a rolling in-memory buffer on the gateway (60 min max, %d samples since %s). '
				'The buffer is lost on a gateway restart.' % (len(rows_), _fmt_time(st['started'])),
	}


def trend(window_min, keys, names=None):
	"""One chart's data and footer in a single call. Columns are keyed by display name so the legend reads well."""
	keys = [str(k) for k in keys]
	names = [unicode(n) for n in names] if names else keys
	data = []
	for r in rows(window_min, keys):
		d = {'time': r['time']}
		for k, n in zip(keys, names):
			d[n] = r[k]
		data.append(d)
	return {'series': [{'name': 'buffer', 'data': data}], 'footer': 'gateway buffer, %d samples' % len(data)}


SERIES = {'a': 'var(--p1-series-a)', 'b': 'var(--p1-series-b)', 'c': 'var(--p1-series-c)',
		  'd': 'var(--p1-series-d)', 'e': 'var(--p1-series-e)'}  # hex values live only in the project stylesheet
AXIS_FONT = {'color': 'var(--p1-muted)', 'size': 11}


def plots(p):
	"""Time Series Chart plots for one Trend part, from its view params."""
	try:
		names = [unicode(n) for n in p['names']]
		cols = [{'key': n, 'color': SERIES.get(str(c), SERIES['a'])} for n, c in zip(names, p['colors'])]
		trends = [{'type': 'line', 'series': 'buffer', 'axis': 'y', 'visible': True,
				   'interpolation': 'curveStepAfter' if p['step'] else 'curveLinear', 'breakLine': True, 'columns': cols}]
		markers = []
		if p['limit'] is not None:
			markers.append({'type': 'line', 'axis': 'y', 'value': p['limit'], 'visible': True,
							'line': {'color': 'var(--p1-faulted)', 'width': 1.5, 'opacity': 1, 'dashArray': '5 4',
									 'label': {'text': 'display limit %d' % int(p['limit']), 'position': 'right',
											   'font': {'color': 'var(--p1-faulted)', 'size': 10}}}})
		axis = {'name': 'y', 'min': p['min'], 'max': p['max'], 'alignment': 'left', 'width': 56,
				'label': {'visible': bool(p['axisLabel']), 'text': p['axisLabel'], 'font': AXIS_FONT},
				'tick': {'color': 'var(--p1-border)', 'label': {'font': AXIS_FONT}}}
		return [{'relativeWeight': 1, 'trends': trends, 'axes': [axis], 'markers': markers}]
	except:
		import traceback
		log.error('plots failed: ' + traceback.format_exc())
		raise
