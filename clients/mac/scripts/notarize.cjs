const fs = require("node:fs");
const path = require("node:path");
const { notarize } = require("@electron/notarize");

function readEnv(name) {
  return String(process.env[name] || "").trim();
}

module.exports = async function notarizeApp(context) {
  if (process.platform !== "darwin" || context.electronPlatformName !== "darwin") {
    return;
  }

  const appName = context.packager.appInfo.productFilename;
  const appPath = path.join(context.appOutDir, `${appName}.app`);
  if (!fs.existsSync(appPath)) {
    throw new Error(`notarize target not found: ${appPath}`);
  }

  const appleApiKey = readEnv("APPLE_API_KEY");
  const appleApiKeyId = readEnv("APPLE_API_KEY_ID");
  const appleApiIssuer = readEnv("APPLE_API_ISSUER");
  const appleId = readEnv("APPLE_ID");
  const appleIdPassword = readEnv("APPLE_APP_SPECIFIC_PASSWORD");
  const teamId = readEnv("APPLE_TEAM_ID");

  if (appleApiKey && appleApiKeyId && appleApiIssuer) {
    const resolvedKeyPath = path.isAbsolute(appleApiKey)
      ? appleApiKey
      : path.resolve(process.cwd(), appleApiKey);
    if (!fs.existsSync(resolvedKeyPath)) {
      throw new Error(`APPLE_API_KEY file does not exist: ${resolvedKeyPath}`);
    }

    await notarize({
      appPath,
      appleApiKey: resolvedKeyPath,
      appleApiKeyId,
      appleApiIssuer,
      teamId: teamId || undefined
    });
    return;
  }

  if (appleId && appleIdPassword && teamId) {
    await notarize({
      appPath,
      appleId,
      appleIdPassword,
      teamId
    });
    return;
  }

  console.warn(
    "[notarize] skipped: provide APPLE_API_KEY/APPLE_API_KEY_ID/APPLE_API_ISSUER or APPLE_ID/APPLE_APP_SPECIFIC_PASSWORD/APPLE_TEAM_ID"
  );
};
