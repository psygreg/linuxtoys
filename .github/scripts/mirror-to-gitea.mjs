import fetch from "node-fetch";

const {
  GITEA_TOKEN,
  GITEA_URL,
  GITEA_OWNER,
  GITEA_REPO,
  EVENT_NAME,
  EVENT_ACTION,
  ISSUE_NUMBER,
  ISSUE_TITLE,
  ISSUE_BODY,
  ISSUE_STATE,
  PR_NUMBER,
  PR_TITLE,
  PR_BODY,
  PR_STATE,
  PR_URL,
} = process.env;

// Validate required environment variables
const requiredEnvVars = [
  "GITEA_TOKEN",
  "GITEA_URL",
  "GITEA_OWNER",
  "GITEA_REPO",
];
for (const envVar of requiredEnvVars) {
  if (!process.env[envVar]) {
    throw new Error(`Missing required environment variable: ${envVar}`);
  }
}

// Validate GITEA_URL is a valid URL
try {
  new URL(GITEA_URL);
} catch {
  throw new Error(`Invalid GITEA_URL: "${GITEA_URL}" is not a valid URL`);
}

const baseUrl = `${GITEA_URL}/api/v1/repos/${GITEA_OWNER}/${GITEA_REPO}`;

// Headers with User-Agent to bypass Cloudflare challenges
const getHeaders = () => ({
  Authorization: `token ${GITEA_TOKEN}`,
  "Content-Type": "application/json",
  "User-Agent":
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
});

// ── Helpers ──────────────────────────────────────────────────────────────────

async function getIssue(number) {
  const url = `${baseUrl}/issues/${number}`;
  const res = await fetch(url, {
    headers: getHeaders(),
  });
  if (res.status === 404) return null;
  if (!res.ok) {
    const text = await res.text();
    throw new Error(
      `GET issue failed: ${res.status} ${text.substring(0, 200)}`,
    );
  }
  return res.json();
}

async function createIssue(payload) {
  const res = await fetch(`${baseUrl}/issues`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(
      `POST issue failed: ${res.status} ${text.substring(0, 200)}`,
    );
  }
  return res.json();
}

async function updateIssue(number, payload) {
  const url = `${baseUrl}/issues/${number}`;
  const res = await fetch(url, {
    method: "PATCH",
    headers: getHeaders(),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(
      `PATCH issue failed: ${res.status} ${text.substring(0, 200)}`,
    );
  }
  return res.json();
}

async function ensureLabel(name, color = "ededed") {
  // List existing labels and find a match
  const res = await fetch(`${baseUrl}/labels?limit=50`, {
    headers: getHeaders(),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(
      `GET labels failed: ${res.status} ${text.substring(0, 200)}`,
    );
  }
  const labels = await res.json();
  const existing = labels.find((l) => l.name === name);
  if (existing) return existing.id;

  // Create it if missing
  const create = await fetch(`${baseUrl}/labels`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify({ name, color }),
  });
  if (!create.ok) {
    const text = await create.text();
    throw new Error(
      `POST label failed: ${create.status} ${text.substring(0, 200)}`,
    );
  }
  const label = await create.json();
  return label.id;
}

// ── Issue mirroring ───────────────────────────────────────────────────────────

async function mirrorIssue() {
  const number = parseInt(ISSUE_NUMBER);
  const state = ISSUE_STATE === "closed" ? "closed" : "open";
  const title = ISSUE_TITLE;
  const body = ISSUE_BODY || "";

  const existing = await getIssue(number);

  if (existing) {
    console.log(`Updating Gitea issue #${number}...`);
    await updateIssue(number, { title, body, state });
    console.log(`✓ Updated issue #${number}`);
  } else {
    console.log(`Creating Gitea issue #${number}...`);
    // Gitea doesn't let you set the issue number directly on creation,
    // so we tag it for traceability.
    const taggedBody = `${body}\n\n---\n_Mirrored from GitHub issue #${number}_`;
    await createIssue({ title, body: taggedBody });
    console.log(`✓ Created issue (GitHub #${number})`);
  }
}

// ── PR mirroring ──────────────────────────────────────────────────────────────

async function mirrorPR() {
  const number = parseInt(PR_NUMBER);
  const state = PR_STATE === "closed" ? "closed" : "open";
  const title = `[PR #${number}] ${PR_TITLE}`;
  const body = [
    PR_BODY || "",
    "",
    "---",
    `_Mirrored from GitHub Pull Request: ${PR_URL}_`,
  ].join("\n");

  // Ensure a label exists to distinguish mirrored PRs
  const labelId = await ensureLabel("mirrored-pr", "0075ca");

  const existing = await getIssue(number);

  if (existing) {
    console.log(`Updating Gitea issue for PR #${number}...`);
    await updateIssue(number, { title, body, state });
    console.log(`✓ Updated PR mirror #${number}`);
  } else {
    console.log(`Creating Gitea issue for PR #${number}...`);
    await createIssue({ title, body, labels: [labelId] });
    console.log(`✓ Created PR mirror (GitHub PR #${number})`);
  }
}

// ── Entry point ───────────────────────────────────────────────────────────────

(async () => {
  try {
    console.log(`Event: ${EVENT_NAME} / Action: ${EVENT_ACTION}`);

    if (EVENT_NAME === "issues") {
      await mirrorIssue();
    } else if (EVENT_NAME === "pull_request") {
      await mirrorPR();
    } else {
      console.log("No mirroring needed for this event.");
    }
  } catch (err) {
    console.error("Mirror failed:", err.message);
    process.exit(1);
  }
})().catch((err) => {
  console.error("Fatal error:", err.message);
  process.exit(1);
});
