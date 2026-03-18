import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { coy } from "react-syntax-highlighter/dist/esm/styles/prism";

type ChatMessageBodyProps = {
  content: string;
  renderMarkdown: boolean;
};

function isExternalHref(href: string): boolean {
  return /^(https?:)?\/\//i.test(href);
}

export default function ChatMessageBody({
  content,
  renderMarkdown,
}: ChatMessageBodyProps): JSX.Element {
  if (!renderMarkdown) {
    return <p className="chatbot-message-text">{content}</p>;
  }

  return (
    <div className="chatbot-markdown">
      <Markdown
        remarkPlugins={[remarkGfm]}
        skipHtml
        components={{
          a({ href, children, ...props }) {
            const linkHref = href || "";
            const external = isExternalHref(linkHref);
            return (
              <a
                {...props}
                href={linkHref}
                target={external ? "_blank" : undefined}
                rel={external ? "noreferrer noopener" : undefined}
              >
                {children}
              </a>
            );
          },
          code(props) {
            const { children, className, node: _node, ...rest } = props;
            const match = /language-([\w-]+)/.exec(className || "");
            const code = String(children).replace(/\n$/, "");

            if (match) {
              return (
                <SyntaxHighlighter
                  PreTag="div"
                  language={match[1]}
                  style={coy}
                  className="chatbot-code-block"
                  customStyle={{ margin: 0, borderRadius: 12 }}
                >
                  {code}
                </SyntaxHighlighter>
              );
            }

            return (
              <code {...rest} className={className}>
                {children}
              </code>
            );
          },
        }}
      >
        {content}
      </Markdown>
    </div>
  );
}
