async function exportChunk(start, count) {
  const ID = 157658592;
  const B = 100;
  const d = await fetch(
    `https://music.163.com/api/v3/playlist/detail?id=${ID}&n=0&s=0`,
    { credentials: 'include' }
  ).then((r) => r.json());
  const allIds = d.playlist.trackIds.map((t) => t.id);
  const ids = allIds.slice(start, start + count);
  const out = [];
  for (let i = 0; i < ids.length; i += B) {
    const b = ids.slice(i, i + B);
    const r = await fetch(
      `https://music.163.com/api/song/detail/?ids=[${b.join(',')}]`,
      { credentials: 'include' }
    ).then((x) => x.json());
    for (const s of r.songs || []) {
      out.push({
        id: String(s.id),
        name: s.name,
        artist: (s.artists || []).map((a) => a.name).join(' / '),
        fee: s.fee || 0,
      });
    }
    await new Promise((r) => setTimeout(r, 150));
  }
  return {
    start,
    count: out.length,
    name: d.playlist.name,
    trackCount: d.playlist.trackCount,
    songs: out,
  };
}
