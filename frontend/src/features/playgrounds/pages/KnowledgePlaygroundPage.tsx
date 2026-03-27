import PlaygroundWorkspace from "../components/PlaygroundWorkspace";
import { knowledgePlaygroundConfig } from "../configs";

export default function KnowledgePlaygroundPage(): JSX.Element {
  return <PlaygroundWorkspace config={knowledgePlaygroundConfig} />;
}
