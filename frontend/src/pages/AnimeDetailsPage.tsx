import PageTemplate, { usePageTitle } from "@/components/PageTemplate";

export default function AnimeDetailsPage() {
  usePageTitle("AnimeDetailsPage");
  return (
    <PageTemplate
      title="AnimeDetailsPage"
      description="Shows anime details"
      // actions={<Button size="sm">Help</Button>}  // optional
    >
      {/* Replace with real form later */}
      <div className="text-sm text-muted-foreground">Page goes here.</div>
    </PageTemplate>
  );
}