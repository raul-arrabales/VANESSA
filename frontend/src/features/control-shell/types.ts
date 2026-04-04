import type { AppNavIconName } from "../../components/AppNavIcon";
import type { Role } from "../../auth/types";

export type ControlCardSection = "aiOperations" | "vanessaPlatform";

export type ControlCardDefinition = {
  id: string;
  section: ControlCardSection;
  titleKey: string;
  descriptionKey: string;
  to: string;
  icon: AppNavIconName;
  minimumRole: Role;
};
