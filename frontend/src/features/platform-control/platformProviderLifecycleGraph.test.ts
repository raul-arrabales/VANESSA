import { describe, expect, it } from "vitest";
import type { PlatformDeploymentProfile, PlatformProvider } from "../../api/platform";
import { deriveLifecycleCounts } from "../../components/lifecycle-graph";
import { expectLifecycleDefinition, expectTerminalStateUncounted } from "../../test/lifecycleGraphAssertions";
import { deploymentsFixture, providersFixture } from "../../test/platformControlFixtures";
import {
  createPlatformProviderLifecycleGraphDefinition,
  getPlatformProviderLifecycleState,
  PLATFORM_PROVIDER_LIFECYCLE_STATE_IDS,
  PLATFORM_PROVIDER_LIFECYCLE_TRANSITIONS,
} from "./platformProviderLifecycleGraph";

const t = ((key: string) => key) as never;

function buildProvider(overrides: Partial<PlatformProvider> = {}): PlatformProvider {
  return {
    ...providersFixture[0],
    ...overrides,
  };
}

function buildDeployment(provider: PlatformProvider, overrides: Partial<PlatformDeploymentProfile> = {}): PlatformDeploymentProfile {
  return {
    ...deploymentsFixture[0],
    id: "deployment-test",
    slug: "deployment-test",
    display_name: "Deployment Test",
    is_active: false,
    bindings: [
      {
        ...deploymentsFixture[0].bindings[0],
        provider: {
          id: provider.id,
          slug: provider.slug,
          provider_key: provider.provider_key,
          provider_origin: provider.provider_origin,
          display_name: provider.display_name,
          endpoint_url: provider.endpoint_url,
          enabled: provider.enabled,
          adapter_kind: provider.adapter_kind,
        },
      },
    ],
    ...overrides,
  };
}

describe("platformProviderLifecycleGraph", () => {
  it("defines provider lifecycle states and transitions", () => {
    const definition = createPlatformProviderLifecycleGraphDefinition(t);

    expectLifecycleDefinition(definition, {
      stateIds: PLATFORM_PROVIDER_LIFECYCLE_STATE_IDS,
      transitions: PLATFORM_PROVIDER_LIFECYCLE_TRANSITIONS,
      i18nBase: "platformControl.providers.lifecycle",
    });
  });

  it.each([
    ["disabled", buildProvider({ enabled: false }), [], "disabled"],
    ["enabled unbound", buildProvider({ id: "provider-unbound" }), [], "enabled_unbound"],
    [
      "bound inactive",
      buildProvider({ id: "provider-inactive" }),
      [buildDeployment(buildProvider({ id: "provider-inactive" }), { is_active: false })],
      "bound_inactive",
    ],
    [
      "active ready",
      buildProvider({ id: "provider-active" }),
      [buildDeployment(buildProvider({ id: "provider-active" }), { is_active: true })],
      "active_ready",
    ],
    [
      "active attention",
      buildProvider({ id: "provider-loading", load_state: "loading" }),
      [buildDeployment(buildProvider({ id: "provider-loading" }), { is_active: true })],
      "active_attention",
    ],
  ])("classifies %s providers", (_label, provider, deployments, expectedState) => {
    expect(getPlatformProviderLifecycleState(provider, deployments)).toBe(expectedState);
  });

  it("counts known states and leaves deleted as an uncounted terminal state", () => {
    const activeProvider = buildProvider({ id: "provider-active" });
    const inactiveProvider = buildProvider({ id: "provider-inactive" });
    const definition = createPlatformProviderLifecycleGraphDefinition(t);
    const counts = deriveLifecycleCounts(
      [
        activeProvider,
        inactiveProvider,
        buildProvider({ id: "provider-disabled", enabled: false }),
      ],
      definition,
      (provider) => getPlatformProviderLifecycleState(provider, [
        buildDeployment(activeProvider, { is_active: true }),
        buildDeployment(inactiveProvider, { is_active: false }),
      ]),
    );

    expect(counts.byState.active_ready).toBe(1);
    expect(counts.byState.bound_inactive).toBe(1);
    expect(counts.byState.disabled).toBe(1);
    expectTerminalStateUncounted(counts);
    expect(counts.unknown).toBe(0);
  });
});
