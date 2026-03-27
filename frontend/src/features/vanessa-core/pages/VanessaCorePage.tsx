import PlaygroundWorkspace from "../../playgrounds/components/PlaygroundWorkspace";
import { vanessaCorePlaygroundConfig } from "../vanessaCoreConfig";

export default function VanessaCorePage(): JSX.Element {
  return <PlaygroundWorkspace config={vanessaCorePlaygroundConfig} />;
}
