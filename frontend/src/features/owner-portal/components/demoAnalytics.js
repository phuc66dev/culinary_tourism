const DAY_MS = 24 * 60 * 60 * 1000;
const VIETNAM_OFFSET_MS = 7 * 60 * 60 * 1000;
const languageShares = { en: 18, zh: 9, ja: 6, ko: 4 };

export function createDemoAnalytics(days, now = new Date()) {
  const today = Math.floor((now.getTime() + VIETNAM_OFFSET_MS) / DAY_MS);
  const daily = Array.from({ length: days }, (_, index) => {
    const day = today - days + 1 + index;
    const date = new Date(day * DAY_MS);
    const weekend = date.getUTCDay() === 0 || date.getUTCDay() === 6;
    const views = 64 + ((day * 17) % 53) + (weekend ? 38 : 0);
    const audioStarts = Math.round(views * 0.42);
    return {
      date: date.toISOString().slice(0, 10),
      views,
      search_selections: Math.round(views * (0.24 + (day % 8) / 100)),
      audio_starts: audioStarts,
      audio_completions: Math.round(audioStarts * (0.58 + (day % 12) / 100)),
      listen_seconds: audioStarts * (39 + (day % 19)),
    };
  });

  const totals = { views: 0, search_selections: 0, audio_starts: 0, audio_completions: 0, listen_seconds: 0 };
  for (const day of daily) {
    for (const metric of Object.keys(totals)) totals[metric] += day[metric];
  }
  const languages = Object.entries(languageShares).map(([language, share]) => ({
    language,
    audio_starts: Math.floor(totals.audio_starts * share / 100),
  }));
  const otherStarts = languages.reduce((total, entry) => total + entry.audio_starts, 0);
  languages.unshift({ language: "vi", audio_starts: totals.audio_starts - otherStarts });
  return { totals, daily, languages };
}
