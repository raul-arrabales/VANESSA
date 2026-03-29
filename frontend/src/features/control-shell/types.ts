import type { OptionCardIconName } from "../../components/OptionCardGrid";
import type { Role } from "../../auth/types";

export type ControlCardSection = "aiOperations" | "vanessaPlatform";

export type ControlCardDefinition = {
  id: string;
  section: ControlCardSection;
  titleKey: string;
  descriptionKey: string;
  to: string;
  icon: OptionCardIconName;
  minimumRole: Role;
};
