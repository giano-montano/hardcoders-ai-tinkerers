import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { spawnSync } from 'node:child_process';

test('bot attaches cards, handles callback once and resumes persisted jobs without LLM', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'med-delivery-'));
  try {
    const id = 'a'.repeat(32), chat = path.join(dir, 'chats/42');
    fs.mkdirSync(path.join(chat, 'work/ingest'), { recursive: true });
    fs.mkdirSync(path.join(dir, '.codex'));
    fs.writeFileSync(path.join(dir, '.codex/auth.json'), '{}');
    fs.writeFileSync(path.join(chat, 'work/ingest', `${id}.json`), JSON.stringify({
      kind: 'telegram', schema_version: 1, messages: ['Summary'],
      keyboards: [{ message_index: 0, inline_keyboard: [[{ text: 'Details', callback_data: 'ux:details:o0' }]] }],
      interaction_responses: { 'ux:details:o0': { messages: ['Verified details'] } },
    }));
    fs.writeFileSync(path.join(dir, 'telegram.json'), JSON.stringify({ offset: 0, jobs: [{
      id: 0, chatId: 42, status: 'ready', response: { text: '', attachments: [], presentations: [id] },
    }] }));
    const mock = path.join(dir, 'mock.mjs');
    fs.writeFileSync(mock, `
      import fs from 'node:fs';
      const sends=[]; let supplied=false, counter=0;
      globalThis.fetch=async (url, options) => {
        const method=url.split('/').at(-1), payload=JSON.parse(options.body);
        let result;
        if(method==='getMe') result={username:'fixture'};
        else if(method==='getWebhookInfo') result={url:''};
        else if(method==='sendMessage') { sends.push(payload); result={message_id:++counter}; }
        else if(method==='answerCallbackQuery') result=true;
        else if(method==='getUpdates') {
          await new Promise(r=>setTimeout(r,30)); result=[];
          if(sends.length===1 && !supplied) {
            supplied=true;
            const update={update_id:1,callback_query:{id:'q1',from:{id:42},message:{chat:{id:42,type:'private'},message_id:1},data:sends[0].reply_markup.inline_keyboard[0][0].callback_data}};
            result=[update,update];
          }
          if(sends.length===2) { fs.writeFileSync(${JSON.stringify(path.join(dir,'sends.json'))},JSON.stringify(sends)); process.kill(process.pid,'SIGTERM'); }
        } else throw new Error('Unexpected API method '+method);
        return {json:async()=>({ok:true,result})};
      };
    `);
    const run = spawnSync(process.execPath, ['--import', mock, path.resolve('prototypes/codex-telegram/src/bot.js')], {
      env: { PATH: process.env.PATH, HOME: dir, DATA_DIR: dir, TELEGRAM_BOT_TOKEN: 'fixture-only' },
      timeout: 10000, encoding: 'utf8',
    });
    assert.equal(run.status, 0, run.stderr);
    const sends = JSON.parse(fs.readFileSync(path.join(dir, 'sends.json')));
    assert.equal(sends.length, 2);
    assert.equal(sends[1].text, 'Verified details');
    const state = JSON.parse(fs.readFileSync(path.join(dir, 'telegram.json')));
    assert.equal(state.jobs.length, 2);
    assert.ok(state.jobs.every(j => j.status === 'done'));
    assert.equal(state.jobs[0].cardsSent, 1);
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});
