import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';

const ID = /^[a-f0-9]{32}$/;
export function loadPresentation(dir, id) {
  if (!ID.test(id)) throw new Error('Invalid presentation ID');
  const expected = path.join(fs.realpathSync(dir), 'work/ingest');
  const root = fs.realpathSync(expected);
  if (root !== expected) throw new Error('Artifact directory outside chat');
  const file = fs.realpathSync(path.join(root, `${id}.json`));
  if (path.dirname(file) !== root) throw new Error('Presentation outside chat');
  const value = JSON.parse(fs.readFileSync(file, 'utf8'));
  if (value.kind !== 'telegram' || value.schema_version !== 1 || !Array.isArray(value.messages)) throw new Error('Invalid presentation');
  return value;
}

export function packets(presentation, id) {
  return presentation.messages.map((text, index) => {
    if (typeof text !== 'string' || !text.length || text.length > 3500) throw new Error('Invalid message');
    const keyboard = presentation.keyboards?.find(k => k.message_index === index);
    const inline_keyboard = keyboard?.inline_keyboard.map(row => row.map(button => {
      if (button.callback_data) {
        if (!Object.hasOwn(presentation.interaction_responses || {}, button.callback_data)) throw new Error('Unknown action');
        const data = `${id}:${button.callback_data}`;
        if (Buffer.byteLength(data) > 64) throw new Error('Callback too long');
        return { text: button.text, callback_data: data };
      }
      const url = new URL(button.url);
      if (url.protocol !== 'https:' || url.hostname !== 'www.google.com' || url.pathname !== '/maps/search/') throw new Error('Invalid map URL');
      return { text: button.text, url: url.href };
    }));
    return { text, ...(inline_keyboard ? { reply_markup: { inline_keyboard } } : {}) };
  });
}

export function callbackAction(query, bindings, dir) {
  const message = query.message;
  if (message?.chat.type !== 'private' || String(query.from?.id) !== String(message.chat.id)) throw new Error('Unauthorized callback');
  const binding = bindings[`${message.chat.id}:${message.message_id}`];
  if (!binding || !binding.actions.includes(query.data)) throw new Error('Unknown callback');
  const id = query.data.slice(0, 32), action = query.data.slice(33);
  if (id !== binding.presentation_id) throw new Error('Wrong presentation');
  const presentation = loadPresentation(dir, id);
  if (!Object.hasOwn(presentation.interaction_responses || {}, action)) throw new Error('Unknown action');
  return { presentation, response: presentation.interaction_responses[action] };
}

export function expandPresentation(dir, cliDir, resultId) {
  if (!ID.test(resultId)) throw new Error('Invalid ranking ID');
  const root = path.join(fs.realpathSync(dir), 'work/ingest');
  if (fs.realpathSync(path.join(root, `${resultId}.json`)) !== path.join(root, `${resultId}.json`)) throw new Error('Ranking outside chat');
  // The only subprocess is a fixed deterministic command, without bot credentials.
  const output = execFileSync('python3', ['-m', 'medisaving', '--data-dir', path.join(dir, 'work/ingest'),
    'ux', 'telegram', resultId, '--expand'], {
    cwd: cliDir, env: { PATH: '/usr/bin:/bin', PYTHONPATH: cliDir, LANG: 'C.UTF-8' },
    encoding: 'utf8', timeout: 15000, maxBuffer: 2000000,
  });
  const result = JSON.parse(output);
  if (!result.ok) throw new Error('Could not expand presentation');
  return result.data.presentation_id;
}
