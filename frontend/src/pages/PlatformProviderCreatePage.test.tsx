import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithAppProviders } from "../test/renderWithAppProviders";
import { t } from "../test/translation";
import type { AuthUser } from "../auth/types";
import PlatformProviderCreatePage from "./PlatformProviderCreatePage";
import * as platformApi from "../api/platform";
import * as modelOpsCredentialsApi from "../api/modelops/credentials";
import { primePlatformControlMocks, providersFixture } from "../test/platformControlFixtures";

let mockUser: AuthUser | null = null;

vi.mock("../auth/AuthProvider", () => ({
  useAuth: () => ({
    user: mockUser,
    token: mockUser ? "token" : "",
    isAuthenticated: Boolean(mockUser),
  }),
}));

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useNavigate: () => vi.fn(),
  };
});

vi.mock("../api/platform", () => ({
  listPlatformCapabilities: vi.fn(),
  listPlatformProviderFamilies: vi.fn(),
  listPlatformProviders: vi.fn(),
  listPlatformDeployments: vi.fn(),
  listPlatformActivationAudit: vi.fn(),
  createPlatformProvider: vi.fn(),
}));

vi.mock("../api/modelops", () => ({
  listModelOpsModels: vi.fn(),
}));

vi.mock("../api/modelops/credentials", () => ({
  listModelCredentials: vi.fn(),
}));

vi.mock("../api/context", () => ({
  listKnowledgeBases: vi.fn(),
}));

describe("PlatformProviderCreatePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUser = {
      id: 1,
      email: "root@example.com",
      username: "root",
      role: "superadmin",
      is_active: true,
    };
    primePlatformControlMocks();
    vi.mocked(modelOpsCredentialsApi.listModelCredentials).mockResolvedValue([]);
  });

  it("creates a provider instance from the dedicated create page", async () => {
    vi.mocked(platformApi.createPlatformProvider).mockResolvedValue(providersFixture[0]);

    await renderWithAppProviders(<PlatformProviderCreatePage />);
    const providerOriginLabel = await t("platformControl.forms.provider.origin");
    const providerFamilyLabel = await t("platformControl.forms.provider.family");

    await userEvent.selectOptions(await screen.findByLabelText(providerOriginLabel), "local");
    await userEvent.selectOptions(await screen.findByLabelText(providerFamilyLabel), "vllm_local");
    await userEvent.type(screen.getByLabelText(await t("platformControl.forms.provider.slug")), "custom-vllm");
    await userEvent.type(screen.getByLabelText(await t("platformControl.forms.provider.displayName")), "Custom vLLM");
    await userEvent.type(screen.getByLabelText(await t("platformControl.forms.provider.endpoint")), "http://llm-alt:8000");
    await userEvent.click(screen.getByRole("button", { name: await t("platformControl.actions.createProvider") }));

    await waitFor(() => {
      expect(platformApi.createPlatformProvider).toHaveBeenCalledWith(
        expect.objectContaining({
          provider_key: "vllm_local",
          slug: "custom-vllm",
          display_name: "Custom vLLM",
        }),
        "token",
      );
    });
  });

  it("creates a cloud provider with a saved credential reference", async () => {
    vi.mocked(platformApi.listPlatformProviderFamilies).mockResolvedValue([
      {
        provider_key: "openai_compatible_cloud_llm",
        provider_origin: "cloud",
        capability: "llm_inference",
        adapter_kind: "openai_compatible_llm",
        display_name: "OpenAI-compatible cloud LLM",
        description: "Cloud LLM family.",
      },
    ]);
    vi.mocked(modelOpsCredentialsApi.listModelCredentials).mockResolvedValue([
      {
        id: "00000000-0000-0000-0000-000000000001",
        owner_user_id: 1,
        credential_scope: "platform",
        provider: "openai",
        display_name: "OpenAI key",
        api_base_url: "https://api.openai.com/v1",
        api_key_last4: "1234",
        is_active: true,
        revoked_at: null,
      },
    ]);
    vi.mocked(platformApi.createPlatformProvider).mockResolvedValue({
      ...providersFixture[0],
      id: "provider-cloud",
      slug: "openai-cloud",
      provider_key: "openai_compatible_cloud_llm",
      provider_origin: "cloud",
    });

    await renderWithAppProviders(<PlatformProviderCreatePage />);

    await userEvent.selectOptions(
      await screen.findByLabelText(await t("platformControl.forms.provider.origin")),
      "cloud",
    );
    await userEvent.selectOptions(
      await screen.findByLabelText(await t("platformControl.forms.provider.family")),
      "openai_compatible_cloud_llm",
    );
    expect(screen.getByLabelText(await t("platformControl.forms.provider.endpoint"))).toHaveValue("https://api.openai.com/v1");
    expect(screen.getByLabelText(await t("platformControl.forms.provider.healthcheck"))).toHaveValue("None");
    expect(screen.getByLabelText(await t("platformControl.forms.provider.config"))).toHaveValue(
      JSON.stringify({ models_path: "/models" }, null, 2),
    );

    await userEvent.selectOptions(
      await screen.findByLabelText(await t("platformControl.forms.provider.savedCredential")),
      "00000000-0000-0000-0000-000000000001",
    );
    await userEvent.type(screen.getByLabelText(await t("platformControl.forms.provider.slug")), "openai-cloud");
    await userEvent.type(screen.getByLabelText(await t("platformControl.forms.provider.displayName")), "OpenAI Cloud");
    await userEvent.click(screen.getByRole("button", { name: await t("platformControl.actions.createProvider") }));

    await waitFor(() => {
      expect(platformApi.createPlatformProvider).toHaveBeenCalledWith(
        expect.objectContaining({
          provider_key: "openai_compatible_cloud_llm",
          endpoint_url: "https://api.openai.com/v1",
          healthcheck_url: null,
          config: {
            models_path: "/models",
          },
          secret_refs: {
            api_key: "modelops://credential/00000000-0000-0000-0000-000000000001",
          },
        }),
        "token",
      );
    });
  });

  it("filters provider families by the selected provider origin", async () => {
    vi.mocked(platformApi.listPlatformProviderFamilies).mockResolvedValue([
      {
        provider_key: "vllm_local",
        provider_origin: "local",
        capability: "llm_inference",
        adapter_kind: "openai_compatible_llm",
        display_name: "vLLM local gateway",
        description: "Local LLM family.",
      },
      {
        provider_key: "openai_compatible_cloud_llm",
        provider_origin: "cloud",
        capability: "llm_inference",
        adapter_kind: "openai_compatible_llm",
        display_name: "OpenAI-compatible cloud LLM",
        description: "Cloud LLM family.",
      },
    ]);

    await renderWithAppProviders(<PlatformProviderCreatePage />);

    const familySelect = await screen.findByLabelText(await t("platformControl.forms.provider.family"));
    expect(familySelect).toBeDisabled();

    await userEvent.selectOptions(
      await screen.findByLabelText(await t("platformControl.forms.provider.origin")),
      "cloud",
    );

    expect(familySelect).toBeEnabled();
    expect(screen.getByRole("option", { name: "OpenAI-compatible cloud LLM" })).toBeVisible();
    expect(screen.queryByRole("option", { name: "vLLM local gateway" })).not.toBeInTheDocument();
  });
});
