"use strict";

module.exports = {
  branches: ["main"],
  tagFormat: "${version}",
  preset: "conventionalcommits",
  plugins: [
    [
      "@semantic-release/commit-analyzer",
      {
        // deprecations are patch releases
        releaseRules: [{ type: "depr", release: "patch" }],
        preset: "conventionalcommits",
      },
    ],
    [
      "@semantic-release/release-notes-generator",
      {
        preset: "conventionalcommits",
        presetConfig: {
          types: [
            { type: "feat", section: "Features" },
            { type: "fix", section: "Bug Fixes" },
            { type: "chore", hidden: true },
            { type: "docs", section: "Documentation" },
            { type: "style", hidden: true },
            { type: "refactor", section: "Refactors" },
            { type: "perf", section: "Performance" },
            { type: "test", hidden: true },
            { type: "depr", section: "Deprecations" },
          ],
        },
      },
    ],
    [
      "@semantic-release/changelog",
      {
        changelogTitle: "# Release Notes\n",
        changelogFile: "CHANGELOG.md",
      },
    ],
    [
      "semantic-release-replace-plugin",
      {
        replacements: [
          {
            files: ["numbsql/__init__.py"],
            from: '__version__ = ".*"',
            to: '__version__ = "${nextRelease.version}"',
            results: [
              {
                file: "numbsql/__init__.py",
                hasChanged: true,
                numMatches: 1,
                numReplacements: 1,
              },
            ],
            countMatches: true,
          },
        ],
      },
    ],
    [
      "@semantic-release/exec",
      {
        verifyConditionsCmd: "ci/release/verify.sh ${options.dryRun}",
        prepareCmd: "ci/release/prepare.sh ${nextRelease.version}",
        publishCmd: "ci/release/publish.sh",
      },
    ],
    [
      "@semantic-release/github",
      {
        successComment: false,
        assets: ["dist/*.whl"],
      },
    ],
    [
      "@semantic-release/git",
      {
        assets: [
          "pyproject.toml",
          "CHANGELOG.md",
          "numbsql/__init__.py",
        ],
        message: "chore(release): ${nextRelease.version}",
      },
    ],
  ],
};
