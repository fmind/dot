// Managed by fmind/dot (private_dot_pi/private_agent/extensions/google-vertex.ts); edit the source, not this copy.
// Docs: https://pi.dev/docs/latest/extensions
// Defaults Agent Platform to `global` when a dynamic GOOGLE_CLOUD_PROJECT/GCLOUD_PROJECT is set,
// and refreshes `google-vertex` model/thinking selection after startup auth evaluation.
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const defaultedLocation =
	!process.env.GOOGLE_CLOUD_LOCATION && Boolean(process.env.GOOGLE_CLOUD_PROJECT || process.env.GCLOUD_PROJECT);
if (defaultedLocation) {
	process.env.GOOGLE_CLOUD_LOCATION = "global";
}

export default function (pi: ExtensionAPI) {
	pi.on("session_start", async (event, ctx) => {
		// ModelRuntime evaluates provider auth before loading extensions; refresh it after defaulting GOOGLE_CLOUD_LOCATION.
		if (!defaultedLocation || event.reason !== "startup") return;
		if (!ctx.modelRegistry.getAvailable().some((model) => model.provider === "google-vertex")) {
			await ctx.modelRegistry.refresh();
		}
		const end = process.argv.indexOf("--");
		const flags = process.argv.slice(2, end === -1 ? undefined : end);
		if (
			flags.some(
				(arg) => arg === "--model" || arg.startsWith("--model=") || arg === "--provider" || arg.startsWith("--provider="),
			)
		) {
			return;
		}
		const hasThinkingFlag = flags.some((arg) => arg === "--thinking" || arg.startsWith("--thinking="));
		const branch = ctx.sessionManager.getBranch();
		// A new session records Pi's pre-extension fallback model in `branch`; trust `branch` only on resumed sessions.
		const resumed =
			flags.some(
				(arg) =>
					arg === "-c" ||
					arg === "--continue" ||
					arg === "-r" ||
					arg === "--resume" ||
					arg === "--session" ||
					arg.startsWith("--session=") ||
					arg === "--session-id" ||
					arg.startsWith("--session-id=") ||
					arg === "--fork" ||
					arg.startsWith("--fork="),
			) || branch.some((entry) => entry.type !== "model_change" && entry.type !== "thinking_level_change");
		let recordedModel: { provider: string; modelId: string } | undefined;
		let assistantModel: { provider: string; modelId: string } | undefined;
		let recordedThinking: ReturnType<typeof pi.getThinkingLevel> | undefined;
		if (resumed) {
			for (let i = branch.length - 1; i >= 0; i--) {
				const entry = branch[i];
				if (!recordedModel && entry.type === "model_change") {
					recordedModel = { provider: entry.provider, modelId: entry.modelId };
				} else if (!recordedThinking && entry.type === "thinking_level_change") {
					recordedThinking = entry.thinkingLevel;
				} else if (entry.type === "message" && entry.message.role === "assistant") {
					assistantModel ??= { provider: entry.message.provider, modelId: entry.message.model };
					if (!recordedThinking && "thinkingLevel" in entry.message && entry.message.thinkingLevel) {
						recordedThinking = entry.message.thinkingLevel;
					}
				}
			}
		}
		const sessionModel = recordedModel ?? assistantModel;
		const { defaultProvider, defaultModel, defaultThinkingLevel } = pi.getSettings();
		const targetModelId = sessionModel
			? sessionModel.provider === "google-vertex"
				? sessionModel.modelId
				: undefined
			: defaultProvider === "google-vertex"
				? defaultModel
				: undefined;
		if (!targetModelId) return;
		const model = ctx.modelRegistry.find("google-vertex", targetModelId);
		if (!model || !ctx.modelRegistry.hasConfiguredAuth(model)) return;
		if (ctx.model?.provider !== "google-vertex" || ctx.model.id !== model.id) {
			await pi.setModel(model);
		}
		const targetThinking = recordedThinking ?? defaultThinkingLevel;
		if (!hasThinkingFlag && targetThinking && pi.getThinkingLevel() !== targetThinking) {
			pi.setThinkingLevel(targetThinking);
		}
	});
}
