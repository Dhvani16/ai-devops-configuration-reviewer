const supportedTypes = ["Dockerfile", "Docker Compose", "GitHub Actions"];

export default function HomePage() {
  return (
    <main>
      <section className="hero">
        <p className="eyebrow">AI DevOps Configuration Reviewer</p>
        <h1>Find configuration risk before it reaches production.</h1>
        <p className="intro">
          A developer-focused review workflow combining deterministic checks and
          schema-validated AI reasoning.
        </p>
      </section>
      <section aria-labelledby="supported-types">
        <h2 id="supported-types">Planned MVP support</h2>
        <ul>
          {supportedTypes.map((configurationType) => (
            <li key={configurationType}>{configurationType}</li>
          ))}
        </ul>
      </section>
    </main>
  );
}
