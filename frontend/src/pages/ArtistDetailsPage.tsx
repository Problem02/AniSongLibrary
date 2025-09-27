import PageTemplate, { usePageTitle } from "@/components/PageTemplate";

export default function ArtistDetailsPage() {
  usePageTitle("ArtistDetailsPage");
  return (
    <PageTemplate
      title="ArtistDetailsPage"
      description="Gets artist details"
      // actions={<Button size="sm">Help</Button>}  // optional
    >
      {/* Replace with real form later */}
      <div className="text-sm text-muted-foreground">Page goes here.</div>
    </PageTemplate>
  );
}