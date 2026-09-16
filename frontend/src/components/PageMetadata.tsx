type PageMetadataProps = {
  title: string;
  description: string;
  robots?: string;
};

export default function PageMetadata({
  title, description, robots = "index, follow"
}: PageMetadataProps) {
  return (
    <>
      <title>{title}</title>
      <meta property="og:title" content={title} />
      <meta name="twitter:title" content={title} />
      <meta name="description" content={description} />
      <meta property="og:description" content={description} />
      <meta name="twitter:description" content={description} />
      <meta name="robots" content={robots} />
    </>
  );
}