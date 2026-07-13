#!/usr/bin/env node
/**
 * 合并浏览器分块导出的歌单 JSON
 * node merge-playlist-chunks.js deploy/playlist-chunks/*.json
 */
const fs = require('fs');
const path = require('path');

const files = process.argv.slice(2).sort((a, b) => {
  const sa = JSON.parse(fs.readFileSync(a, 'utf8')).start;
  const sb = JSON.parse(fs.readFileSync(b, 'utf8')).start;
  return sa - sb;
});

if (!files.length) {
  console.error('usage: node merge-playlist-chunks.js chunk0.json chunk1.json ...');
  process.exit(1);
}

const songs = [];
let meta = {};
for (const f of files) {
  const chunk = JSON.parse(fs.readFileSync(f, 'utf8'));
  meta = { name: chunk.name, trackCount: chunk.trackCount, playlistId: 157658592 };
  songs.push(...chunk.songs);
}

const manifest = {
  ...meta,
  exportedAt: new Date().toISOString(),
  songsCount: songs.length,
  songs,
};

const out = path.join(path.dirname(files[0]), '..', 'playlist-157658592.json');
fs.writeFileSync(out, JSON.stringify(manifest, null, 2));
console.log('merged', songs.length, 'songs ->', out);
