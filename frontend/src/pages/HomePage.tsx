import PageTemplate, { usePageTitle } from "@/components/PageTemplate";

export default function HomePage() {
  usePageTitle("HomePage");
  return (
    <PageTemplate
      title="HomePage"
      description="Main page for AniSongLibrary"
      // actions={<Button size="sm">Help</Button>}  // optional
    >
      {/* Replace with real form later */}
      <div className="text-sm text-muted-foreground">HomePage goes here.</div>
    </PageTemplate>
  );
}