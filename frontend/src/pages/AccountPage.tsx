import PageTemplate, { usePageTitle } from "@/components/PageTemplate";

export default function AccountPage() {
  usePageTitle("AccountPage");
  return (
    <PageTemplate
      title="AccountPage"
      description="Shows account"
      // actions={<Button size="sm">Help</Button>}  // optional
    >
      {/* Replace with real form later */}
      <div className="text-sm text-muted-foreground">Page goes here.</div>
    </PageTemplate>
  );
}