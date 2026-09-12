import fs from 'node:fs';
import path from 'node:path';
import dns from 'node:dns';
import net from 'node:net';
import { DATA, CLI_DIR, atomicJSON, readJSON, prepareChat, runAgent } from './codex.js';
import { loadPresentation, packets, callbackAction, expandPresentation } from './ux.js';

net.setDefaultAutoSelectFamily(false);
dns.setDefaultResultOrder('ipv4first');
process.umask(0o077);
const token = process.env.TELEGRAM_BOT_TOKEN;
if (!token) throw new Error('Falta TELEGRAM_BOT_TOKEN');
const stateFile = path.join(DATA, 'telegram.json');
const state = readJSON(stateFile, { offset: 0, jobs: [] });
for (const job of state.jobs) if (job.status === 'running') job.status = job.response ? 'ready' : 'pending';
state.ui ||= {};
const save = () => atomicJSON(stateFile, state);
const activeChats = new Set();
const concurrency = Number(process.env.CONCURRENCY || 2);
let stopping = false;

async function telegram(method, payload = {}) {
  for (let attempt = 0; attempt < 3; attempt++) {
    const response = await fetch(`https://api.telegram.org/bot${token}/${method}`, {
      method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(payload),
      signal: AbortSignal.timeout(method === 'getUpdates' ? 40000 : 20000)
    });
    const body = await response.json();
    if (body.ok) return body.result;
    if (body.error_code === 429 && attempt < 2) { await new Promise(r => setTimeout(r, (body.parameters?.retry_after || 3) * 1000)); continue; }
    throw new Error(`Telegram ${method}: ${body.error_code} ${body.description}`);
  }
}

async function sendText(chatId, text) {
  while (text.length) {
    let end = Math.min(text.length, 3900);
    if (end < text.length) { const nl = text.lastIndexOf('\n', end); if (nl > 1500) end = nl; }
    await telegram('sendMessage', { chat_id: chatId, text: text.slice(0, end), link_preview_options: { is_disabled: true } });
    text = text.slice(end).trimStart();
  }
}

async function download(message, chatId) {
  const photo = message.photo?.at(-1) || (message.document?.mime_type?.startsWith('image/') ? message.document : null);
  if (!photo) return [];
  if (photo.file_size > 15000000) throw new Error('La imagen supera 15 MB');
  const file = await telegram('getFile', { file_id: photo.file_id });
  const response = await fetch(`https://api.telegram.org/file/bot${token}/${file.file_path}`, { signal: AbortSignal.timeout(30000) });
  if (!response.ok) throw new Error('No se pudo descargar la foto');
  const extension = ['.png', '.jpg', '.jpeg', '.webp'].includes(path.extname(file.file_path)) ? path.extname(file.file_path) : '.jpg';
  const dest = path.join(prepareChat(chatId), 'work/inbox', `${message.message_id}${extension}`);
  fs.writeFileSync(dest, Buffer.from(await response.arrayBuffer()), { mode: 0o600 });
  return [dest];
}

async function sendPDF(chatId, file) {
  const form = new FormData(); form.set('chat_id', String(chatId));
  form.set('document', new Blob([fs.readFileSync(file)], { type: 'application/pdf' }), path.basename(file));
  const result = await (await fetch(`https://api.telegram.org/bot${token}/sendDocument`, { method: 'POST', body: form, signal: AbortSignal.timeout(45000) })).json();
  if (!result.ok) throw new Error('Telegram no aceptó el PDF');
}

async function deliverPresentations(job) {
  const dir = prepareChat(job.chatId);
  const items = (job.response.presentations || []).flatMap(id =>
    packets(loadPresentation(dir, id), id).map(packet => ({ id, packet })));
  job.cardsSent ||= 0;
  for (const { id, packet } of items.slice(job.cardsSent)) {
    const sent = await telegram('sendMessage', { chat_id: job.chatId, ...packet,
      link_preview_options: { is_disabled: true } });
    state.ui[`${job.chatId}:${sent.message_id}`] = { presentation_id: id,
      actions: (packet.reply_markup?.inline_keyboard || []).flat().map(b => b.callback_data).filter(Boolean) };
    job.cardsSent++; save();
  }
}

function interactionResponse(job) {
  const dir = prepareChat(job.chatId);
  const { presentation, response } = callbackAction(job.callback, state.ui, dir);
  if (response.action === 'start_new_prescription') {
    fs.rmSync(path.join(dir, 'session.json'), { force: true });
    return { text: 'Nueva conversación. Envíame los medicamentos y tu distrito.', attachments: [] };
  }
  if (response.action === 'render' && response.expand === true) {
    return { text: '', attachments: [], presentations: [expandPresentation(dir, CLI_DIR, presentation.result_id)] };
  }
  if (response.action === 'call_pharmacy') {
    return { text: `Teléfono reportado de la farmacia: ${response.phone}`, attachments: [] };
  }
  if (Array.isArray(response.messages)) return { text: response.messages.join('\n\n'), attachments: [] };
  throw new Error('Unsupported interaction');
}

async function processJob(job) {
  activeChats.add(job.chatId); job.status = 'running'; save();
  let typing;
  try {
    const message = job.message;
    if (!job.response) {
      if (job.callback) {
        job.response = interactionResponse(job);
      } else if (message.text?.startsWith('/start')) {
        job.response = { text: '💊 Envíame una foto o escribe tus medicamentos con dosis y presentación, y dime tu distrito. Buscaré precios reportados en DIGEMID, con farmacia, dirección y precio por unidad/caja.', attachments: [] };
      } else if (message.text === '/nuevo') {
        const dir = prepareChat(job.chatId); fs.rmSync(path.join(dir, 'session.json'), { force: true });
        job.response = { text: 'Nueva conversación. Envíame los medicamentos y tu distrito.', attachments: [] };
      } else if (!message.text && !message.caption && !message.photo && !message.location && !message.document?.mime_type?.startsWith('image/')) {
        job.response = { text: 'Por ahora puedo leer texto y fotos. Envíame los medicamentos y tu distrito.', attachments: [] };
      } else {
        await telegram('sendChatAction', { chat_id: job.chatId, action: 'typing' });
        typing = setInterval(() => telegram('sendChatAction', { chat_id: job.chatId, action: 'typing' }).catch(() => {}), 4500);
        const images = await download(message, job.chatId);
        let text = message.text || message.caption || '';
        if (message.location) text += `\nUbicación compartida: latitud ${message.location.latitude}, longitud ${message.location.longitude}.`;
        if (message.reply_to_message?.text) text += `\nResponde a este mensaje previo: ${message.reply_to_message.text}`;
        job.response = await runAgent({ chatId: job.chatId, text, images, onEvent: event => {
          if (event.type === 'turn.completed') console.log(JSON.stringify({ event: 'turn.completed', updateId: job.id, usage: event.usage }));
        } });
      }
      job.status = 'ready'; save();
    }
    if (!job.textSent) { await sendText(job.chatId, job.response.text); job.textSent = true; save(); }
    await deliverPresentations(job);
    job.filesSent ||= 0;
    for (const file of job.response.attachments.slice(job.filesSent)) { await sendPDF(job.chatId, file); job.filesSent++; save(); }
    job.status = 'done';
    console.log(JSON.stringify({ event: 'delivered', updateId: job.id }));
  } catch (error) {
    console.error(JSON.stringify({ event: 'job.failed', updateId: job.id, error: error.message.replaceAll(token, '[redacted]') }));
    job.status = 'failed';
    await sendText(job.chatId, 'No pude completar esta consulta. Puedes reenviarla; no voy a darte precios sin verificar.').catch(() => {});
  } finally { clearInterval(typing); activeChats.delete(job.chatId); save(); }
}

function dispatch() {
  if (stopping) return;
  for (const job of state.jobs) {
    if (activeChats.size >= concurrency) break;
    if (['pending', 'ready'].includes(job.status) && !activeChats.has(job.chatId)) void processJob(job);
  }
}

async function main() {
  const me = await telegram('getMe');
  const webhook = await telegram('getWebhookInfo');
  if (webhook.url) throw new Error('Este bot ya usa webhook; no se reemplazó');
  console.log(JSON.stringify({ event: 'started', bot: me.username, concurrency }));
  save();
  const scheduler = setInterval(dispatch, 500); scheduler.unref();
  while (!stopping) {
    try {
      const updates = await telegram('getUpdates', { offset: state.offset, timeout: 25, allowed_updates: ['message', 'callback_query'] });
      for (const update of updates) {
        const callback = update.callback_query;
        if (callback) {
          await telegram('answerCallbackQuery', { callback_query_id: callback.id }).catch(() => {});
          if (callback.message?.chat.type === 'private' && String(callback.from?.id) === String(callback.message.chat.id)
              && !state.jobs.some(j => j.id === update.update_id)) {
            state.jobs.push({ id: update.update_id, chatId: callback.message.chat.id, callback, status: 'pending' });
          }
        }
        const m = update.message;
        if (m?.chat.type === 'private' && !m.from?.is_bot && !state.jobs.some(j => j.id === update.update_id)) {
          state.jobs.push({ id: update.update_id, chatId: m.chat.id, message: m, status: 'pending' });
        }
        state.offset = update.update_id + 1;
        save();
      }
      dispatch();
    } catch (error) {
      console.error(JSON.stringify({ event: 'poll.failed', error: error.message.replaceAll(token, '[redacted]') }));
      await new Promise(r => setTimeout(r, 3000));
    }
  }
}
process.on('SIGTERM', () => { stopping = true; save(); });
process.on('SIGINT', () => { stopping = true; save(); });
main().catch(error => { console.error(error.message.replaceAll(token, '[redacted]')); process.exit(1); });
