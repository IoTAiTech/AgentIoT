#!/usr/bin/env node
// SPDX-License-Identifier: MIT
// Author: Dr. Babak Sarkhpour, with AI assistance
// Version: 0.157.20 | Date: 2026-08-13
// Thin wrapper. Fetches the public curl installer only.

"use strict";

const { spawnSync } = require("child_process");
const repo = process.env.GITHUB_REPO || "IoTAiTech/AgentIoT";
const url = `https://raw.githubusercontent.com/${repo}/main/packaging/curl/install.sh`;

const result = spawnSync(
  "bash",
  ["-lc", `curl -fsSL ${JSON.stringify(url)} | bash`],
  { stdio: "inherit" }
);

process.exit(result.status === null ? 1 : result.status);
