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

const baseUrl = `${GITEA_URL}/api/v1/repos/${GITEA_OWNER}/${GITEA_REPO}`;
const headers = {
  Authorization: `token ${GITEA_TOKEN}`,
  "Content-Type": "application/json",
};

// ── Helpers ──────────────────────────────────────────────────────────────────

async function getIssue(number) {
  const res = await fetch(`${baseUrl}/issues/${number}`, { headers });
  if (res.status === 404) return null;
  if (!res.ok)
    throw new Error(`GET issue failed: ${res.status} ${await res.text()}`);
  return res.json();
}

async function createIssue(payload) {
  const res = await fetch(`${baseUrl}/issues`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });
  if (!res.ok)
    throw new Error(`POST issue failed: ${res.status} ${await res.text()}`);
  return res.json();
}

async function updateIssue(number, payload) {
  const res = await fetch(`${baseUrl}/issues/${number}`, {
    method: "PATCH",
    headers,
    body: JSON.stringify(payload),
  });
  if (!res.ok)
    throw new Error(`PATCH issue failed: ${res.status} ${await res.text()}`);
  return res.json();
}

async function ensureLabel(name, color = "ededed") {
  // List existing labels and find a match
  const res = await fetch(`${baseUrl}/labels?limit=50`, { headers });
  if (!res.ok) throw new Error(`GET labels failed: ${res.status}`);
  const labels = await res.json();
  const existing = labels.find((l) => l.name === name);
  if (existing) return existing.id;

  // Create it if missing
  const create = await fetch(`${baseUrl}/labels`, {
    method: "POST",
    headers,
    body: JSON.stringify({ name, color }),
  });
  if (!create.ok) throw new Error(`POST label failed: ${create.status}`);
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
})();
