import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';
import { romeInstants } from './submission-time.mjs';

const form = document.querySelector('#event-form');
const status = document.querySelector('#form-status');
const send = document.querySelector('#send-button');
const preview = document.querySelector('#preview');
let client;

function value(data, key) { return String(data.get(key) || '').trim(); }
function time(wall) {
  if (!wall) return null;
  const candidates = romeInstants(wall);
  if (candidates.length !== 1) throw new Error(candidates.length
    ? 'That time occurs twice when clocks change. Please choose another time or include clarification in the description.'
    : 'That local time does not exist in Genova. Please check the date and time.');
  return candidates[0];
}
function fields(data) {
  const start_time = time(value(data, 'start'));
  const end_time = time(value(data, 'end'));
  if (!start_time) throw new Error('A start date and time are required.');
  if (end_time && end_time <= start_time) throw new Error('The end must be after the start.');
  const url = value(data, 'url');
  if (url && new URL(url).protocol !== 'https:') throw new Error('Use an HTTPS link.');
  return {
    title: value(data, 'title'), start_time, end_time,
    description: value(data, 'description'),
    location: value(data, 'location') || null, url: url || null,
    submitter_name: value(data, 'submitter_name') || null,
    contact_email: value(data, 'contact_email') || null,
    rights_confirmed: data.has('rights_confirmed'),
  };
}
function show(message, kind = '') {
  status.textContent = message;
  status.className = 'message ' + kind;
}
document.querySelector('#preview-button').addEventListener('click', () => {
  if (!form.reportValidity()) return;
  try {
    const event = fields(new FormData(form));
    preview.textContent = `${event.title}\n${value(new FormData(form), 'start')} Europe/Rome\n${event.location || 'Venue to confirm'}\n\n${event.description}`;
    preview.hidden = false;
    show('Preview only. Select “Send for review” to submit.');
  } catch (error) { show(error.message, 'error'); }
});
form.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (!client || !form.reportValidity()) return;
  const data = new FormData(form);
  if (value(data, 'website')) return; // simple bot trap; database also caps intake
  let proposed;
  try { proposed = fields(data); }
  catch (error) { show(error.message, 'error'); return; }
  send.disabled = true;
  show('Sending your suggestion…');
  try {
    const { error } = await client.from('event_submissions').insert(proposed);
    if (error) throw error;
    form.reset(); preview.hidden = true;
    show('Thank you. Your event has been sent to the admin for review; it is not published yet.', 'success');
  } catch {
    show('The suggestion could not be sent. Check for a duplicate event or try again later.', 'error');
  } finally { send.disabled = false; }
});

try {
  const response = await fetch('config.json', { cache: 'no-store' });
  const { appGlobals: globals } = await response.json();
  if (!response.ok || globals?.communitySubmissionsEnabled !== true || !globals?.supabaseUrl?.startsWith('https://') ||
      !globals?.supabasePublishableKey?.startsWith('sb_publishable_')) throw new Error('Missing configuration');
  client = createClient(globals.supabaseUrl, globals.supabasePublishableKey);
} catch {
  document.querySelector('#setup-error').hidden = false;
  send.disabled = true;
}
