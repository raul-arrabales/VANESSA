import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";

type TestRouterProps = {
  children: ReactNode;
  route?: string;
  routeState?: unknown;
};

export default function TestRouter({ children, route = "/", routeState }: TestRouterProps): JSX.Element {
  return (
    <MemoryRouter
      initialEntries={[{ pathname: route, state: routeState }]}
      future={{
        v7_startTransition: true,
        v7_relativeSplatPath: true,
      }}
    >
      {children}
    </MemoryRouter>
  );
}
