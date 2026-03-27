import type { OptionCardIconName } from "../../components/OptionCardGrid";
import type { Role } from "../../auth/types";

export type ControlCardDefinition = {
  id: string;
  titleKey: string;
  descriptionKey: string;
  to: string;
  icon: OptionCardIconName;
  minimumRole: Role;
};
