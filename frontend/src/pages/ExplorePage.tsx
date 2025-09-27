import PageTemplate, { usePageTitle } from "@/components/PageTemplate";

export default function ExplorePage() {
  usePageTitle("ExplorePage");
  return (
    <PageTemplate
      title="ExplorePage"
      description="Explore songs in AniSongLibrary"
      // actions={<Button size="sm">Help</Button>}  // optional
    >
      {/* Replace with real form later */}
      <div className="text-sm text-muted-foreground">Page goes here.</div>
    </PageTemplate>
  );
}