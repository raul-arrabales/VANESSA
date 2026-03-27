export type KnowledgeSourceCard = {
  id: string;
  title: string;
  snippet: string;
};

export default function KnowledgeSourcesList({ sources }: { sources: KnowledgeSourceCard[] }): JSX.Element {
  if (sources.length === 0) {
    return <></>;
  }

  return (
    <div className="card-stack">
      {sources.map((source) => (
        <div key={source.id} className="panel">
          <strong>{source.title}</strong>
          <p>{source.snippet}</p>
        </div>
      ))}
    </div>
  );
}
