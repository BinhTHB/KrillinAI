// ==========================================================================
// KrillinAI v2 – Cloudflare Worker (API Gateway + Telegram Dispatcher)
// ==========================================================================
// Bridges TelegramBot webhooks → GitHub Repository Dispatch for workflow #1.
// NO secrets are hardcoded. All env vars must be set in Cloudflare Dashboard.
// ==========================================================================

/**
 * Validate a video URL (only basic pattern checks; actual download validation
 * happens inside the Ingest workflow). Returns `null` if invalid.
 */
function validateVideoUrl(raw) {
  if (typeof raw !== 'string') return null;
  const url = raw.trim();
  // Match common video sharing platforms
  const patterns = [
    /^https?:\/\/(www\.)?(youtube\.com|youtu\.be)\/.+/i,
    /^https?:\/\/(www\.)?(douyin\.com|tiktok\.com)\/.+/i,
    /^https?:\/\/(www\.)?(twitter\.com|x\.com)\/.+/i,
    /^https?:\/\/.*\.(mp4|mov|avi|mkv|webm)(\?.*)?$/i,
  ];
  if (patterns.some((re) => re.test(url))) return url;
  return null;
}

/**
 * Send an inline reply / status update to the user on Telegram.
 */
async function replyTelegram(chatId, text, replyToMessageId, env) {
  const url = `${env.TELEGRAM_API_URL}${env.TELEGRAM_BOT_TOKEN}/sendMessage`;
  const payload = {
    chat_id: chatId,
    text,
    parse_mode: 'HTML',
    disable_web_page_preview: true,
  };
  if (replyToMessageId) payload.reply_to_message_id = replyToMessageId;
  await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
}

/**
 * Trigger a GitHub repository_dispatch event to start Workflow #1 (Ingest).
 */
async function dispatchWorkflow(owner, repo, eventType, payload, env) {
  if (env.GITHUB_DISPATCH_REF) {
    const url = `${env.GITHUB_API_URL}/repos/${owner}/${repo}/actions/workflows/ingest.yml/dispatches`;
    const body = JSON.stringify({
      ref: env.GITHUB_DISPATCH_REF,
      inputs: {
        video_url: payload.videoUrl,
        chat_id: String(payload.chatId),
        message_id: String(payload.messageId)
      }
    });
    const resp = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${env.GITHUB_TOKEN}`,
        'User-Agent': 'KrillinAI-Worker'
      },
      body
    });
    if (!resp.ok) throw new Error(`GitHub workflow_dispatch failed: ${env.GITHUB_DISPATCH_REF} ${resp.status} ${await resp.text()}`);
    return;
  }

  const url = `${env.GITHUB_API_URL}/repos/${owner}/${repo}/dispatches`;
  const body = JSON.stringify({ event_type: eventType, client_payload: payload });
  const resp = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${env.GITHUB_TOKEN}`,
      'User-Agent': 'KrillinAI-Worker'
    },
    body
  });
  if (!resp.ok) throw new Error(`GitHub repository_dispatch failed: ${resp.status} ${await resp.text()}`);
}

// ── Request router ─────────────────────────────────────────────────────────

export default {
  async fetch(request, env, ctx) {
    // Only accept POST
    if (request.method !== 'POST') {
      return new Response('Method Not Allowed', { status: 405 });
    }

    const url = new URL(request.url);

    // ── Health check ────────────────────────────────────────────────────────
    if (url.pathname === '/health') {
      return new Response(JSON.stringify({ status: 'ok' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // ── Telegram webhook ────────────────────────────────────────────────────
    if (url.pathname === '/webhook/telegram') {
      try {
        const body = await request.json();

        // Ignore non-message / edited_message
        const msg = body.message || body.edited_message;
        if (!msg || !msg.text) {
          return new Response('OK');
        }

        const chatId = msg.chat.id;
        const messageId = msg.message_id;
        const text = msg.text;

        // Extract first URL from the message text
        const videoUrl = validateVideoUrl(text);
        if (!videoUrl) {
          await replyTelegram(chatId, '\u274c Vui l\xf2ng g\u1eedi m\u1ed9t link video h\u1ee3p l\u1ec7 (YouTube, TikTok, Douyin, Twitter/X ho\u1eb7c file MP4 tr\u1ef1c ti\u1ebfp).', messageId, env);
          return new Response('OK');
        }

        // Acknowledge receipt
        await replyTelegram(
          chatId,
          `\u2705 \u0110\xe3 nh\u1eadn video. \u0110ang x\u1eed l\xfd\u2026\n\nM\xe3 l\u1ec7nh: <code>${videoUrl.slice(0, 60)}...</code>`,
          messageId,
          env
        );

        // Dispatch GitHub Actions workflow #1
        await dispatchWorkflow(
          env.GITHUB_OWNER,
          env.GITHUB_REPO,
          env.GITHUB_DISPATCH_EVENT || 'telegram_video_ingest',
          { chatId, videoUrl, messageId },
          env
        );

        await replyTelegram(chatId, '\u23f3 \u0110\xe3 kh\u1edfi t\u1ea1o pipeline x\u1eed l\xfd! Ti\u1ebfn tr\xecnh s\u1ebd \u0111\u01b0\u1ee3c c\u1eadp nh\u1eadt sau.', messageId, env);

        return new Response('OK');
      } catch (err) {
        console.error('webhook error:', err);
        return new Response('Internal Error', { status: 500 });
      }
    }

    // ── 404 fallback ────────────────────────────────────────────────────────
    return new Response('Not Found', { status: 404 });
  },
};
