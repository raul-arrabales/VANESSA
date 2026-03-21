import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import SyntaxHighlighter from "react-syntax-highlighter/dist/esm/prism-light";
import bash from "react-syntax-highlighter/dist/esm/languages/prism/bash";
import javascript from "react-syntax-highlighter/dist/esm/languages/prism/javascript";
import json from "react-syntax-highlighter/dist/esm/languages/prism/json";
import jsx from "react-syntax-highlighter/dist/esm/languages/prism/jsx";
import python from "react-syntax-highlighter/dist/esm/languages/prism/python";
import tsx from "react-syntax-highlighter/dist/esm/languages/prism/tsx";
import typescript from "react-syntax-highlighter/dist/esm/languages/prism/typescript";
import { coy } from "react-syntax-highlighter/dist/esm/styles/prism";

type MarkdownMessageBodyProps = {
  content: string;
};

SyntaxHighlighter.registerLanguage("bash", bash);
SyntaxHighlighter.registerLanguage("sh", bash);
SyntaxHighlighter.registerLanguage("shell", bash);
SyntaxHighlighter.registerLanguage("javascript", javascript);
SyntaxHighlighter.registerLanguage("js", javascript);
SyntaxHighlighter.registerLanguage("json", json);
SyntaxHighlighter.registerLanguage("jsx", jsx);
SyntaxHighlighter.registerLanguage("python", python);
SyntaxHighlighter.registerLanguage("py", python);
SyntaxHighlighter.registerLanguage("typescript", typescript);
SyntaxHighlighter.registerLanguage("ts", typescript);
SyntaxHighlighter.registerLanguage("tsx", tsx);

function isExternalHref(href: string): boolean {
  return /^(https?:)?\/\//i.test(href);
}

export default function MarkdownMessageBody({
  content,
}: MarkdownMessageBodyProps): JSX.Element {
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
