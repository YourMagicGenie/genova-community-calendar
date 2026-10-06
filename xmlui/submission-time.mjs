const rome = new Intl.DateTimeFormat('en-GB', {
  timeZone: 'Europe/Rome', year: 'numeric', month: '2-digit', day: '2-digit',
  hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
});

export function romeInstants(wallTime) {
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(wallTime)) return [];
  const [year, month, day, hour, minute] = wallTime.match(/\d+/g).map(Number);
  if (year < 2020 || year > 2100 || month < 1 || month > 12 || day < 1 || day > 31 ||
      hour > 23 || minute > 59) return [];
  const wallUtc = Date.UTC(year, month - 1, day, hour, minute);
  const matches = [];
  for (const offset of [60, 120]) {
    const instant = new Date(wallUtc - offset * 60_000);
    const parts = Object.fromEntries(rome.formatToParts(instant)
      .filter((part) => part.type !== 'literal').map((part) => [part.type, Number(part.value)]));
    if (parts.year === year && parts.month === month && parts.day === day &&
        parts.hour === hour && parts.minute === minute) matches.push(instant.toISOString());
  }
  return matches;
}
