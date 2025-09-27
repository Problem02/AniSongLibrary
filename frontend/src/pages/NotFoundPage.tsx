import PageTemplate, { usePageTitle } from "@/components/PageTemplate";

export default function NotFoundPage() {
  usePageTitle("NotFoundPage");
  return (
    <PageTemplate
      title="NotFoundPage"
      description="Redirect for any other page"
      // actions={<Button size="sm">Help</Button>}  // optional
    >
      {/* Replace with real form later */}
      <div className="text-sm text-muted-foreground">Not found</div>
    </PageTemplate>
  );
}