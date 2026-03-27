import PlaygroundWorkspace from "../components/PlaygroundWorkspace";
import { chatPlaygroundConfig } from "../configs";

export default function ChatPlaygroundPage(): JSX.Element {
  return <PlaygroundWorkspace config={chatPlaygroundConfig} />;
}
