import fs from 'node:fs';
import path from 'node:path';
import { spawn } from 'node:child_process';

export const ROOT = path.resolve(import.meta.dirname, '..');
export const DATA = path.resolve(process.env.DATA_DIR || path.join(ROOT, 'data'));
export const CLI_DIR = path.resolve(process.env.MEDISAVING_CLI_DIR || path.join(ROOT, 'cli'));

export function atomicJSON(file, value) {
  fs.mkdirSync(path.dirname(file), { recursive: true, mode: 0o700 });
  fs.writeFileSync(file + '.tmp', JSON.stringify(value), { mode: 0o600 });
  fs.renameSync(file + '.tmp', file);
}

export function readJSON(file, fallback) {
  return fs.existsSync(file) ? JSON.parse(fs.readFileSync(file, 'utf8')) : fallback;
}

export function prepareChat(chatId) {
  if (!/^-?\d+$/.test(String(chatId))) throw new Error('Chat inválido');
  const dir = path.join(DATA, 'chats', String(chatId));
  for (const sub of ['work/inbox', 'work/output', 'codex']) fs.mkdirSync(path.join(dir, sub), { recursive: true, mode: 0o700 });
  const auth = path.join(process.env.HOME, '.codex/auth.json');
  const target = path.join(dir, 'codex/auth.json');
  if (!fs.existsSync(target) || fs.statSync(auth).mtimeMs > fs.statSync(target).mtimeMs) {
    fs.copyFileSync(auth, target); fs.chmodSync(target, 0o600);
  }
  fs.writeFileSync(path.join(dir, 'codex/config.toml'), `
model = "${process.env.CODEX_MODEL || 'gpt-5.6-sol'}"
model_reasoning_effort = "medium"
approval_policy = "never"
sandbox_mode = "danger-full-access"
developer_instructions = "Use the installed med CLI for medicine data. Resolve/fetch with med u/r/f, calculate with med rank, join selected official details with med enrich, render with med show. Skills: /opt/medisaving/skills/ingesta/SKILL.md and /opt/medisaving/skills/ux/SKILL.md. Never dump full datasets, hand-code rankings, or browse for prices. Source order in med v is not a price ranking. Require exact dosage form for sublingual requests."
[projects."/work"]
trust_level = "trusted"
[mcp_servers.browser]
required = false
command = "/usr/bin/xvfb-run"
args = ["-a", "-s", "-screen 0 1280x900x24 -extension GLX", "/usr/bin/node", "/opt/browser/node_modules/@playwright/mcp/cli.js", "--isolated", "--executable-path", "/opt/chromium/chrome", "--no-sandbox", "--caps", "pdf", "--output-dir", "/work/output"]
startup_timeout_sec = 45
tool_timeout_sec = 90
`, { mode: 0o600 });
  return dir;
}

export function sandboxArgs(dir) {
  return ['--die-with-parent', '--unshare-pid', '--unshare-ipc', '--unshare-uts',
    '--ro-bind', '/usr', '/usr', '--ro-bind', '/lib', '/lib', '--ro-bind', '/lib64', '/lib64',
    '--ro-bind', '/bin', '/bin', '--ro-bind', '/etc', '/etc',
    '--ro-bind', fs.realpathSync('/etc/resolv.conf'), fs.realpathSync('/etc/resolv.conf'),
    '--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp', '--dir', '/tmp/.X11-unix',
    '--bind', path.join(dir, 'work'), '/work', '--bind', path.join(dir, 'codex'), '/codex',
    '--ro-bind', path.join(ROOT, 'node_modules'), '/opt/browser/node_modules',
    '--ro-bind', process.env.CHROMIUM_DIR || '/home/f3mt0/.cache/ms-playwright/chromium-1228/chrome-linux64', '/opt/chromium',
    '--ro-bind', path.join(ROOT, 'response.schema.json'), '/response.schema.json',
    '--ro-bind', fs.realpathSync(CLI_DIR), '/opt/medisaving',
    '--chdir', '/work', '--setenv', 'HOME', '/work', '--setenv', 'CODEX_HOME', '/codex',
    '--setenv', 'PATH', '/opt/medisaving/bin:/usr/bin:/bin'];
}

export async function runAgent({ chatId, text, images = [], onEvent = () => {} }) {
  const dir = prepareChat(chatId);
  const sessionFile = path.join(dir, 'session.json');
  const session = readJSON(sessionFile, {});
  const output = `/work/output/answer-${Date.now()}.json`;
  const args = [...sandboxArgs(dir), '/usr/bin/codex', 'exec'];
  if (session.threadId) args.push('resume');
  args.push('--json', '--skip-git-repo-check', '--output-schema', '/response.schema.json', '-o', output);
  if (session.threadId) args.push(session.threadId);
  for (const image of images) args.push('-i', '/work/inbox/' + path.basename(image));
  args.push('-');
  const prompt = `${fs.readFileSync(path.join(ROOT, 'agent.md'), 'utf8')}\n\nFecha local: ${new Date().toLocaleString('es-PE', { timeZone: 'America/Lima' })}\nMENSAJE ACTUAL DEL USUARIO:\n${text || '[foto adjunta]'}\n${images.length ? 'Observa las imágenes adjuntas.' : ''}`;
  const env = { PATH: '/usr/bin:/bin', LANG: 'C.UTF-8', TZ: 'America/Lima', HOME: process.env.HOME, NO_COLOR: '1' };
  await new Promise((resolve, reject) => {
    const child = spawn('/usr/bin/bwrap', args, { env, stdio: ['pipe', 'pipe', 'pipe'], detached: true });
    let buffer = '', errors = '';
    const stop = () => { try { process.kill(-child.pid, 'SIGTERM'); } catch {} };
    const timer = setTimeout(stop, Number(process.env.CODEX_TIMEOUT_MS || 720000));
    child.stdout.on('data', chunk => {
      buffer += chunk;
      let i;
      while ((i = buffer.indexOf('\n')) >= 0) {
        const line = buffer.slice(0, i); buffer = buffer.slice(i + 1);
        try {
          const event = JSON.parse(line);
          if (event.thread_id) { session.threadId = event.thread_id; atomicJSON(sessionFile, session); }
          onEvent(event);
        } catch {}
      }
    });
    child.stderr.on('data', chunk => { errors = (errors + chunk).slice(-3000); });
    child.on('error', e => { clearTimeout(timer); reject(e); });
    child.on('close', code => { clearTimeout(timer); fs.writeFileSync(path.join(dir, 'last-stderr.log'), errors, { mode: 0o600 }); code === 0 ? resolve() : reject(new Error(`Codex terminó con ${code}: ${errors.slice(-600)}`)); });
    child.stdin.end(prompt);
  });
  const response = readJSON(path.join(dir, output.replace('/work/', 'work/')), null);
  if (!response?.text?.trim() || !Array.isArray(response.attachments)) throw new Error('Codex no produjo respuesta válida');
  const base = fs.realpathSync(path.join(dir, 'work/output'));
  response.attachments = response.attachments.map(file => {
    if (!file.startsWith('/work/output/') || !file.endsWith('.pdf')) throw new Error('Adjunto inválido');
    const actual = fs.realpathSync(path.join(dir, file.replace('/work/', 'work/')));
    if (!actual.startsWith(base + path.sep)) throw new Error('Adjunto fuera del chat');
    return actual;
  });
  return response;
}
