// Standalone sanity check of the slot-selection logic at various times.
const SCHEDULE = [
  { time: "00:00", slug: "01-miezonoptica",   title: "Miezonoptica" },
  { time: "05:00", slug: "02-utrenia",        title: "Utrenia" },
  { time: "06:00", slug: "03-ceasul-1",       title: "Ceasul Întâi" },
  { time: "07:30", slug: "04-mijloceasul-1",  title: "Mijloceasul Întâi" },
  { time: "09:00", slug: "05-ceasul-3",       title: "Ceasul al treilea" },
  { time: "10:30", slug: "06-mijloceasul-3",  title: "Mijloceasul al treilea" },
  { time: "12:00", slug: "07-ceasul-6",       title: "Ceasul al șaselea" },
  { time: "13:30", slug: "08-mijloceasul-6",  title: "Mijloceasul al șaselea" },
  { time: "15:00", slug: "09-ceasul-9",       title: "Ceasul al nouălea" },
  { time: "16:30", slug: "10-mijloceasul-9",  title: "Mijloceasul al nouălea" },
  { time: "18:00", slug: "11-vecernia",       title: "Vecernia" },
  { time: "21:00", slug: "12-pavecernita",    title: "Pavecernița mică" }
];
const toMin = (s) => { const [h,m] = s.split(":").map(Number); return h*60+m; };
function active(min) {
  let c = null;
  for (const s of SCHEDULE) { if (toMin(s.time) <= min) c = s; else break; }
  return c || SCHEDULE[SCHEDULE.length - 1];
}
function nxt(min) {
  for (const s of SCHEDULE) if (toMin(s.time) > min) return s;
  return SCHEDULE[0];
}
const cases = [
  ["00:00", "01-miezonoptica", "02-utrenia"],
  ["04:59", "01-miezonoptica", "02-utrenia"],
  ["05:00", "02-utrenia",      "03-ceasul-1"],
  ["06:00", "03-ceasul-1",     "04-mijloceasul-1"],
  ["07:29", "03-ceasul-1",     "04-mijloceasul-1"],
  ["07:30", "04-mijloceasul-1","05-ceasul-3"],
  ["12:00", "07-ceasul-6",     "08-mijloceasul-6"],
  ["20:59", "11-vecernia",     "12-pavecernita"],
  ["21:00", "12-pavecernita",  "01-miezonoptica"],
  ["23:59", "12-pavecernita",  "01-miezonoptica"]
];
let fail = 0;
for (const [hhmm, expActive, expNext] of cases) {
  const m = toMin(hhmm);
  const a = active(m).slug, n = nxt(m).slug;
  const ok = a === expActive && n === expNext;
  console.log(`${ok ? "OK " : "FAIL"}  ${hhmm}  active=${a}  next=${n}`);
  if (!ok) fail++;
}
process.exit(fail ? 1 : 0);
