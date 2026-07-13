/**
 * 在已登录 music.163.com 的浏览器控制台运行，导出完整歌单。
 * 用法：复制本文件内容到 DevTools Console，或 Cursor Browser CDP Runtime.evaluate。
 *
 * 原理：/api/v3/playlist/detail 返回完整 trackIds（7269），
 *       再用 /api/song/detail/?ids=[...] 分批补全歌名/歌手。
 */
(async () => {
  const PLAYLIST_ID = 157658592;
  const BATCH = 500;

  const detail = await fetch(
    `https://music.163.com/api/v3/playlist/detail?id=${PLAYLIST_ID}&n=0&s=0`,
    { credentials: 'include' }
  ).then((r) => r.json());

  if (detail.code !== 200 || !detail.playlist?.trackIds?.length) {
    throw new Error('playlist detail failed: ' + JSON.stringify(detail));
  }

  const pl = detail.playlist;
  const trackIds = pl.trackIds.map((t) => t.id);
  const songs = [];

  for (let i = 0; i < trackIds.length; i += BATCH) {
    const batch = trackIds.slice(i, i + BATCH);
    const idsParam = '[' + batch.join(',') + ']';
    const res = await fetch(
      `https://music.163.com/api/song/detail/?ids=${idsParam}`,
      { credentials: 'include' }
    ).then((r) => r.json());

    if (res.code !== 200) {
      throw new Error(`song detail batch ${i} failed: ${res.code}`);
    }

    for (const s of res.songs || []) {
      songs.push({
        id: String(s.id),
        name: s.name,
        artist: (s.ar || []).map((a) => a.name).join(' / '),
        album: s.al?.name || '',
        duration: s.dt || 0,
        fee: s.fee || 0,
      });
    }
    console.log(`batch ${i / BATCH + 1}: ${songs.length}/${trackIds.length}`);
    await new Promise((r) => setTimeout(r, 300));
  }

  const manifest = {
    playlistId: PLAYLIST_ID,
    name: pl.name,
    trackCount: pl.trackCount,
    exportedAt: new Date().toISOString(),
    songs,
  };

  const blob = new Blob([JSON.stringify(manifest, null, 2)], {
    type: 'application/json',
  });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `playlist-${PLAYLIST_ID}.json`;
  a.click();
  console.log('exported', manifest.songs.length, 'songs');
  return manifest;
})();
