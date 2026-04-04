export type PageSectionTabItem = {
  id: string;
  label: string;
  to: string;
  isActive: boolean;
};

export type PageSubmenuItem = {
  id: string;
  label: string;
  isActive: boolean;
  to?: string;
  onSelect?: () => void;
};
