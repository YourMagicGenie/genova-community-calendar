import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';
import { romeInstants } from './submission-time.mjs';

const list = document.querySelector('#submissions-list');
const message = document.querySelector('#submissions-message');
const refresh = document.querySelector('#refresh-submissions');
let client;
let authorized = false;

function localTime(iso) {
  if (!iso) return '';
  const parts = Object.fromEntries(new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Europe/Rome', year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
  }).formatToParts(new Date(iso)).filter(p => p.type !== 'literal').map(p => [p.type, p.value]));
  return `${parts.year}-${parts.month}-${parts.day}T${parts.hour}:${parts.minute}`;
}
function instant(wall, previous) {
  if (!wall) return null;
  const matches = romeInstants(wall);
  if (matches.length === 1) return matches[0];
  if (matches.length === 2 && previous && matches.includes(new Date(previous).toISOString())) return previous;
  throw new Error('Clarify a missing or repeated Europe/Rome clock-change time.');
}
function field(form, label, name, value, type = 'text') {
  const wrapper = document.createElement('label');
  wrapper.textContent = label;
  const input = name === 'description' ? document.createElement('textarea') : document.createElement('input');
  if (name !== 'description') input.type = type;
  input.name = name;
  input.value = value ?? '';
  if (['title', 'start_time', 'description'].includes(name)) input.required = true;
  wrapper.append(input); form.append(wrapper);
}
function button(label, action) {
  const element = document.createElement('button');
  element.type = action === 'save' ? 'submit' : 'button';
  element.dataset.action = action;
  element.textContent = label;
  return element;
}
function render(rows) {
  list.replaceChildren();
  if (!rows.length) { list.textContent = 'No submissions to review.'; return; }
  for (const row of rows) {
    const form = document.createElement('form');
    form.className = 'submission-card';
    const heading = document.createElement('h3');
    heading.textContent = `${row.status.toUpperCase()} · ${row.title}`;
    form.append(heading);
    const meta = document.createElement('p');
    meta.textContent = `Sent ${new Date(row.created_at).toLocaleString('it-IT', {timeZone:'Europe/Rome'})} · ${row.submitter_name || 'Anonymous'} · ${row.contact_email || 'No contact email'}`;
    form.append(meta);
    field(form, 'Event name', 'title', row.title);
    field(form, 'Start (Europe/Rome)', 'start_time', localTime(row.start_time), 'datetime-local');
    field(form, 'End (Europe/Rome)', 'end_time', localTime(row.end_time), 'datetime-local');
    field(form, 'Description', 'description', row.description);
    field(form, 'Venue', 'location', row.location);
    field(form, 'Event link', 'url', row.url, 'url');
    const actions = document.createElement('div'); actions.className = 'actions';
    actions.append(button('Save edits', 'save'));
    if (row.status === 'pending') actions.append(button('Approve and publish', 'approve'), button('Reject', 'reject'));
    if (row.status === 'approved') actions.append(button('Withdraw', 'withdraw'));
    form.append(actions);
    form.addEventListener('submit', (event) => { event.preventDefault(); act(row, form, 'save'); });
    actions.addEventListener('click', (event) => {
      const action = event.target.dataset?.action;
      if (action && action !== 'save') act(row, form, action);
    });
    list.append(form);
  }
}
async function act(row, form, action) {
  if (!authorized || !client) return;
  if (action === 'reject' || action === 'withdraw') {
    if (!window.confirm(`${action === 'reject' ? 'Reject' : 'Withdraw'} this event?`)) return;
  }
  const buttons = form.querySelectorAll('button');
  buttons.forEach(b => { b.disabled = true; });
  message.textContent = 'Saving…';
  try {
    if (action === 'save' || action === 'approve') {
      if (!form.reportValidity()) return;
      const data = new FormData(form);
      const start = instant(String(data.get('start_time')), row.start_time);
      const end = instant(String(data.get('end_time')), row.end_time);
      if (end && end <= start) throw new Error('End must be after start.');
      const payload = {
        title: String(data.get('title')).trim(), start_time: start, end_time: end,
        description: String(data.get('description')).trim(),
        location: String(data.get('location')).trim() || null,
        url: String(data.get('url')).trim() || null,
      };
      const { error } = await client.from('event_submissions').update(payload).eq('id', row.id);
      if (error) throw error;
    }
    if (action !== 'save') {
      const { error } = await client.rpc('review_event_submission', {p_id: row.id, p_action: action});
      if (error) throw error;
    }
    message.textContent = action === 'approve' ? 'Approved. The event record is ready for the live calendar route.' : 'Review saved.';
    await load();
  } catch (error) {
    message.textContent = error.message || 'The review action failed.';
  } finally { buttons.forEach(b => { b.disabled = false; }); }
}
async function load() {
  if (!authorized) return;
  const { data, error } = await client.from('event_submissions')
    .select('id,title,start_time,end_time,description,location,url,submitter_name,contact_email,status,created_at')
    .in('status', ['pending', 'approved']).order('created_at', {ascending: false}).limit(100);
  if (error) { message.textContent = 'Submissions could not be loaded.'; return; }
  render(data || []);
}
refresh.addEventListener('click', load);
async function checkAdmin() {
  const {data: {user} = {}} = await client.auth.getUser();
  authorized = false;
  if (user) {
    const {data, error} = await client.from('admin_users').select('user_id').eq('user_id', user.id).maybeSingle();
    authorized = !error && data?.user_id === user.id;
  }
  if (authorized) await load();
  else list.replaceChildren();
}
try {
  const response = await fetch('config.json', {cache:'no-store'});
  const {appGlobals: config} = await response.json();
  if (!response.ok || config?.communitySubmissionsEnabled !== true) {
    document.querySelector('.submission-review').hidden = true;
    throw new Error('not enabled');
  }
  if (!config?.supabaseUrl?.startsWith('https://') ||
      !config?.supabasePublishableKey?.startsWith('sb_publishable_')) throw new Error('configuration');
  client = createClient(config.supabaseUrl, config.supabasePublishableKey);
  client.auth.onAuthStateChange(() => { window.setTimeout(checkAdmin, 0); });
  await checkAdmin();
} catch { message.textContent = 'The submission review service is unavailable.'; }
