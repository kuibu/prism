function resolvePublishConfig() {
  const provider = String(process.env.PRISM_MAC_PUBLISH_PROVIDER || "").trim().toLowerCase();
  if (!provider) {
    return undefined;
  }

  if (provider === "generic") {
    const url = String(process.env.PRISM_MAC_UPDATE_URL || "").trim();
    if (!url) {
      throw new Error("PRISM_MAC_UPDATE_URL is required when PRISM_MAC_PUBLISH_PROVIDER=generic");
    }
    return [{ provider: "generic", url }];
  }

  if (provider === "github") {
    const repository = String(process.env.GITHUB_REPOSITORY || "").trim();
    const [repoOwnerFromEnv, repoNameFromEnv] = repository.includes("/")
      ? repository.split("/", 2)
      : ["", ""];
    const owner = String(process.env.PRISM_GH_OWNER || repoOwnerFromEnv).trim();
    const repo = String(process.env.PRISM_GH_REPO || repoNameFromEnv).trim();
    const privateRepo = String(process.env.PRISM_GH_PRIVATE || "").trim() === "1";
    const releaseType = String(process.env.PRISM_GH_RELEASE_TYPE || "release").trim();
    if (!["draft", "prerelease", "release"].includes(releaseType)) {
      throw new Error("PRISM_GH_RELEASE_TYPE must be one of: draft, prerelease, release");
    }
    if (!owner || !repo) {
      throw new Error(
        "PRISM_GH_OWNER and PRISM_GH_REPO are required when PRISM_MAC_PUBLISH_PROVIDER=github (or set GITHUB_REPOSITORY)"
      );
    }
    return [{ provider: "github", owner, repo, private: privateRepo, releaseType }];
  }

  throw new Error(`Unsupported PRISM_MAC_PUBLISH_PROVIDER: ${provider}`);
}

const publish = resolvePublishConfig();

module.exports = {
  appId: "com.prism.desktop",
  productName: "Prism Desktop",
  directories: {
    output: "dist",
    buildResources: "build"
  },
  files: ["main.js", "preload.js", "offline.html", "package.json"],
  asar: true,
  afterSign: "scripts/notarize.cjs",
  mac: {
    category: "public.app-category.productivity",
    target: [
      { target: "dmg", arch: ["arm64", "x64"] },
      { target: "zip", arch: ["arm64", "x64"] }
    ],
    artifactName: "${productName}-${version}-${arch}.${ext}",
    hardenedRuntime: true,
    gatekeeperAssess: false,
    entitlements: "build/entitlements.mac.plist",
    entitlementsInherit: "build/entitlements.mac.inherit.plist"
  },
  publish
};
