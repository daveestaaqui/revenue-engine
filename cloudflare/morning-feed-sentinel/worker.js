/**
 * Surplus Docket — Autonomous Morning Feed Failover Sentinel (Cloudflare Worker)
 * ==============================================================================
 * Free external redundancy running outside GitHub Actions.
 *
 * Capabilities:
 * 1. Scheduled Cron Triggers (Mon-Fri 7:00 AM, 7:15 AM, 7:30 AM EDT/EST)
 * 2. Reads live daily_dispatch_log.json from GitHub raw repository
 * 3. Enforces strict idempotency: if already dispatched today, exits immediately
 * 4. If NOT dispatched, calls GitHub API repository_dispatch to trigger immediate live delivery
 * 5. Serves an HTTP webhook for external cron monitors (cron-job.org, EasyCron, UptimeRobot)
 */

const REPO_OWNER = "daveestaaqui";
const REPO_NAME = "revenue-engine";
const DISPATCH_LOG_URL = `https://raw.githubusercontent.com/${REPO_OWNER}/${REPO_NAME}/main/portal/daily_dispatch_log.json`;

/**
 * Returns today's calendar date in America/New_York (EST/EDT) as YYYY-MM-DD
 */
function getTodayET() {
  const formatter = new Intl.DateTimeFormat("en-US", {
    timeZone: "America/New_York",
    year: "numeric",
    month: "2-digit",
    day: "2-digit"
  });
  const parts = formatter.formatToParts(new Date());
  const year = parts.find(p => p.type === "year").value;
  const month = parts.find(p => p.type === "month").value;
  const day = parts.find(p => p.type === "day").value;
  return `${year}-${month}-${day}`;
}

/**
 * Checks if the feed for today was already successfully dispatched.
 */
async function isAlreadyDispatchedToday(todayET) {
  try {
    const res = await fetch(`${DISPATCH_LOG_URL}?_t=${Date.now()}`, {
      headers: { "User-Agent": "SurplusDocket-Cloudflare-Sentinel/1.0" }
    });
    if (!res.ok) {
      console.warn(`Could not fetch dispatch log (HTTP ${res.status}). Assuming not dispatched.`);
      return false;
    }
    const data = await res.json();
    return data.last_dispatched_date === todayET && data.status === "SUCCESS";
  } catch (err) {
    console.error("Error reading dispatch log:", err);
    return false;
  }
}

/**
 * Triggers GitHub Actions repository_dispatch event.
 */
async function triggerGitHubDispatch(token, eventType = "dispatch_morning_feed") {
  if (!token) {
    throw new Error("GITHUB_TOKEN secret is not set in Cloudflare Worker environment variables.");
  }
  const url = `https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/dispatches`;
  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${token}`,
      "Accept": "application/vnd.github.v3+json",
      "Content-Type": "application/json",
      "User-Agent": "SurplusDocket-Cloudflare-Sentinel/1.0"
    },
    body: JSON.stringify({ event_type: eventType })
  });

  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`GitHub API error HTTP ${res.status}: ${errorText}`);
  }
  return true;
}

export default {
  /**
   * Cloudflare Cron Trigger handler
   */
  async scheduled(event, env, ctx) {
    const todayET = getTodayET();
    const now = new Date().toISOString();
    console.log(`[${now}] Cloudflare Sentinel triggered for date: ${todayET}`);

    const alreadySent = await isAlreadyDispatchedToday(todayET);
    if (alreadySent) {
      console.log(`[${now}] Morning feed for ${todayET} was ALREADY successfully dispatched. Skipping duplicate send.`);
      return;
    }

    console.warn(`[${now}] Morning feed for ${todayET} has NOT been dispatched yet. Triggering repository_dispatch...`);
    try {
      await triggerGitHubDispatch(env.GITHUB_TOKEN);
      console.log(`[${now}] Successfully triggered GitHub Actions morning feed failover dispatch!`);
    } catch (err) {
      console.error(`[${now}] Failed to trigger GitHub Actions dispatch:`, err);
    }
  },

  /**
   * HTTP Webhook handler (for cron-job.org, EasyCron, or manual browser/curl triggers)
   */
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const todayET = getTodayET();

    // Status endpoint
    if (url.pathname === "/status" || url.pathname === "/health") {
      const alreadySent = await isAlreadyDispatchedToday(todayET);
      return new Response(JSON.stringify({
        status: "ok",
        today_et: todayET,
        dispatched_today: alreadySent,
        server_time_utc: new Date().toISOString()
      }, null, 2), {
        headers: { "Content-Type": "application/json" }
      });
    }

    // Trigger endpoint (protected by optional SECRET_KEY param or header)
    if (url.pathname === "/trigger") {
      const authKey = request.headers.get("x-secret-key") || url.searchParams.get("key");
      if (env.SECRET_KEY && authKey !== env.SECRET_KEY) {
        return new Response(JSON.stringify({ error: "Unauthorized" }), {
          status: 401,
          headers: { "Content-Type": "application/json" }
        });
      }

      const force = url.searchParams.get("force") === "true";
      const alreadySent = await isAlreadyDispatchedToday(todayET);

      if (alreadySent && !force) {
        return new Response(JSON.stringify({
          status: "skipped",
          message: `Morning feed for ${todayET} already sent. Idempotency preserved.`,
          date: todayET
        }, null, 2), {
          headers: { "Content-Type": "application/json" }
        });
      }

      try {
        await triggerGitHubDispatch(env.GITHUB_TOKEN);
        return new Response(JSON.stringify({
          status: "triggered",
          message: `Successfully triggered GitHub Actions morning feed dispatch for ${todayET}.`,
          forced: force
        }, null, 2), {
          headers: { "Content-Type": "application/json" }
        });
      } catch (err) {
        return new Response(JSON.stringify({
          status: "error",
          message: err.message
        }), {
          status: 500,
          headers: { "Content-Type": "application/json" }
        });
      }
    }

    return new Response("Surplus Docket Cloudflare Sentinel active. Endpoints: /status, /trigger", {
      headers: { "Content-Type": "text/plain" }
    });
  }
};
