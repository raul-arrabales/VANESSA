import { describe, expect, it } from "vitest";
import type { PlatformDeploymentProfile } from "../../api/platform";
import { deriveLifecycleCounts } from "../../components/lifecycle-graph";
import { expectLifecycleDefinition, expectTerminalStateUncounted } from "../../test/lifecycleGraphAssertions";
import {
  createPlatformDeploymentLifecycleGraphDefinition,
  getPlatformDeploymentLifecycleState,
  PLATFORM_DEPLOYMENT_LIFECYCLE_STATE_IDS,
  PLATFORM_DEPLOYMENT_LIFECYCLE_TRANSITIONS,
} from "./platformDeploymentLifecycleGraph";

const t = ((key: string) => key) as never;

function buildDeployment(overrides: Partial<PlatformDeploymentProfile> = {}): PlatformDeploymentProfile {
  return {
    id: "deployment-1",
    slug: "local-default",
    display_name: "Local Default",
    description: "Default deployment.",
    is_active: false,
    configuration_status: {
      is_ready: true,
      incomplete_capabilities: [],
      summary: "Ready.",
    },
    bindings: [],
    ...overrides,
  };
}

describe("platformDeploymentLifecycleGraph", () => {
  it("defines deployment lifecycle states and transitions", () => {
    const definition = createPlatformDeploymentLifecycleGraphDefinition(t);

    expectLifecycleDefinition(definition, {
      stateIds: PLATFORM_DEPLOYMENT_LIFECYCLE_STATE_IDS,
      transitions: PLATFORM_DEPLOYMENT_LIFECYCLE_TRANSITIONS,
      i18nBase: "platformControl.deployments.lifecycle",
    });
  });

  it.each([
    [
      "incomplete",
      buildDeployment({
        is_active: false,
        configuration_status: {
          is_ready: false,
          incomplete_capabilities: ["llm_inference"],
          summary: "Missing LLM inference.",
        },
      }),
      "incomplete",
    ],
    [
      "missing status",
      buildDeployment({
        is_active: false,
        configuration_status: undefined,
      }),
      "incomplete",
    ],
    ["ready inactive", buildDeployment({ is_active: false }), "ready_inactive"],
    ["active ready", buildDeployment({ is_active: true }), "active_ready"],
    [
      "active degraded",
      buildDeployment({
        is_active: true,
        configuration_status: {
          is_ready: false,
          incomplete_capabilities: ["embeddings"],
          summary: "Embeddings incomplete.",
        },
      }),
      "active_degraded",
    ],
  ])("classifies %s deployments", (_label, deployment, expectedState) => {
    expect(getPlatformDeploymentLifecycleState(deployment)).toBe(expectedState);
  });

  it("counts known states and leaves deleted as an uncounted terminal state", () => {
    const definition = createPlatformDeploymentLifecycleGraphDefinition(t);
    const counts = deriveLifecycleCounts(
      [
        buildDeployment({ is_active: true }),
        buildDeployment({ is_active: false }),
        buildDeployment({
          is_active: false,
          configuration_status: {
            is_ready: false,
            incomplete_capabilities: ["vector_store"],
            summary: "Vector store incomplete.",
          },
        }),
      ],
      definition,
      getPlatformDeploymentLifecycleState,
    );

    expect(counts.byState.active_ready).toBe(1);
    expect(counts.byState.ready_inactive).toBe(1);
    expect(counts.byState.incomplete).toBe(1);
    expectTerminalStateUncounted(counts);
    expect(counts.unknown).toBe(0);
  });
});
