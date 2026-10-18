-- Docs: https://www.lazyvim.org/extras/ai/copilot-native
return {
  {
    "neovim/nvim-lspconfig",
    opts = {
      servers = {
        -- Attach only inside a Git workspace: `chezmoi edit` decrypts secrets into a temporary
        -- directory outside any repository, where inline completion would send them to GitHub.
        copilot = { workspace_required = true },
      },
    },
  },
}
