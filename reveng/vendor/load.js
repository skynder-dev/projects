'use strict';
// Loads frozen G280 modules unmodified (hash-checked against VENDOR_MANIFEST.json). Browser-only modules get a sandboxed `window`.
const fs = require('node:fs'), path = require('node:path'), vm = require('node:vm'), crypto = require('node:crypto');
const dir = path.join(__dirname, 'g280');
const manifest = JSON.parse(fs.readFileSync(path.join(dir, 'VENDOR_MANIFEST.json'), 'utf8'));
const cache = {};
function load(name) {
  const file = name.endsWith('.js') ? name : name + '.js';
  if (cache[file]) return cache[file];
  const src = fs.readFileSync(path.join(dir, file));
  const h = crypto.createHash('sha256').update(src).digest('hex');
  if (!manifest.files[file] || manifest.files[file].sha256 !== h) throw new Error(`VENDOR_HASH_MISMATCH:${file}`);
  const module_ = { exports: {} }, win = {};
  const ctx = vm.createContext({ module: module_, exports: module_.exports, window: win, globalThis: undefined, console, require: (m) => load(path.basename(m)) });
  ctx.globalThis = ctx;
  vm.runInContext(src.toString('utf8'), ctx, { filename: file });
  const api = (module_.exports && Object.keys(module_.exports).length) ? module_.exports : (Object.values(win)[0] || Object.values(ctx).find(v => v && v.CONTRACT_ID));
  return (cache[file] = api);
}
module.exports = { load, manifest };
