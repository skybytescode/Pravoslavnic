// Pinned schedule for the daily cycle of hours (Pravoslavnic).
// Times are local to Europe/Chisinau and the player evaluates them in that zone.
// Order matters: entries must be sorted ascending by `time`.
window.CEASLOVNIC_SCHEDULE = [
  { time: "00:00", slug: "01-miezonoptica",        title: "Miezonoptica" },
  { time: "05:00", slug: "02-utrenia",             title: "Utrenia" },
  { time: "06:00", slug: "03-ceasul-1",            title: "Ceasul Întâi" },
  { time: "07:30", slug: "04-mijloceasul-1",       title: "Mijloceasul Întâi" },
  { time: "09:00", slug: "05-ceasul-3",            title: "Ceasul al treilea" },
  { time: "10:30", slug: "06-mijloceasul-3",       title: "Mijloceasul al treilea" },
  { time: "12:00", slug: "07-ceasul-6",            title: "Ceasul al șaselea" },
  { time: "13:30", slug: "08-mijloceasul-6",       title: "Mijloceasul al șaselea" },
  { time: "15:00", slug: "09-ceasul-9",            title: "Ceasul al nouălea" },
  { time: "16:30", slug: "10-mijloceasul-9",       title: "Mijloceasul al nouălea" },
  { time: "18:00", slug: "11-vecernia",            title: "Vecernia" },
  { time: "21:00", slug: "12-pavecernita",         title: "Pavecernița mică" }
];

window.CEASLOVNIC_TZ = "Europe/Chisinau";
