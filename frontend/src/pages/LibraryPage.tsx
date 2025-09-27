import PageTemplate, { usePageTitle } from "@/components/PageTemplate";

export default function LibraryPage() {
  usePageTitle("LibraryPage");
  return (
    <PageTemplate
      title="LibraryPage"
      description="Shows user library"
      // actions={<Button size="sm">Help</Button>}  // optional
    >
      {/* Replace with real form later */}
      <div className="text-sm text-muted-foreground">Page goes here.</div>
    </PageTemplate>
  );
}