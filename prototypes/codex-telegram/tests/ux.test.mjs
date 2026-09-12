import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { loadPresentation, packets, callbackAction } from '../src/ux.js';

const id = 'a'.repeat(32);
const presentation = { kind: 'telegram', schema_version: 1, messages: ['A pharmacy'],
  keyboards: [{ message_index: 0, inline_keyboard: [[{ text: 'Details', callback_data: 'ux:details:o0' }]] }],
  interaction_responses: { 'ux:details:o0': { messages: ['Unit price: S/ 3.48'] } } };

test('persisted card bindings isolate actions by chat, message and presentation', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'med-ux-'));
  try {
    fs.mkdirSync(path.join(dir, 'work/ingest'), { recursive: true });
    fs.writeFileSync(path.join(dir, 'work/ingest', `${id}.json`), JSON.stringify(presentation));
    const card = packets(loadPresentation(dir, id), id)[0];
    const data = card.reply_markup.inline_keyboard[0][0].callback_data;
    assert.ok(Buffer.byteLength(data) <= 64);
    const bindings = { '42:7': { presentation_id: id, actions: [data] } };
    const q = { from: { id: 42 }, message: { chat: { id: 42, type: 'private' }, message_id: 7 }, data };
    assert.deepEqual(callbackAction(q, bindings, dir).response.messages, ['Unit price: S/ 3.48']);
    assert.throws(() => callbackAction({ ...q, from: { id: 99 } }, bindings, dir));
    assert.throws(() => callbackAction({ ...q, data: `${id}:ux:new` }, bindings, dir));
    assert.throws(() => callbackAction(q, {}, dir));
    assert.throws(() => loadPresentation(dir, '../secret'));
    const outside = path.join(dir, 'outside.json');
    fs.writeFileSync(outside, JSON.stringify(presentation));
    fs.unlinkSync(path.join(dir, 'work/ingest', `${id}.json`));
    fs.symlinkSync(outside, path.join(dir, 'work/ingest', `${id}.json`));
    assert.throws(() => loadPresentation(dir, id));
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});

test('only persisted actions and Maps search URLs are accepted', () => {
  const changed = structuredClone(presentation);
  changed.keyboards[0].inline_keyboard[0][0].callback_data = 'ux:unknown';
  assert.throws(() => packets(changed, id));
  changed.keyboards[0].inline_keyboard = [[{ text: 'Map', url: 'https://www.google.com/maps/search/?api=1&query=Lince' }]];
  assert.ok(packets(changed, id)[0].reply_markup);
  changed.keyboards[0].inline_keyboard[0][0].url = 'file:///etc/passwd';
  assert.throws(() => packets(changed, id));
});
