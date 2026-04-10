import type { ReactNode } from "react";
import { ModelOpsWorkspaceLayout } from "./ModelOpsWorkspaceLayout";

type ModelOpsWorkspaceFrameProps = {
  children: ReactNode;
};

export function ModelOpsWorkspaceFrame({ children }: ModelOpsWorkspaceFrameProps): JSX.Element {
  return (
    <ModelOpsWorkspaceLayout>
      {children}
    </ModelOpsWorkspaceLayout>
  );
}
