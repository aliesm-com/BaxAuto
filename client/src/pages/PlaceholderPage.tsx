import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export function PlaceholderPage({ title, description }: { title: string; description?: string }) {
  return (
    <div className="p-6 lg:p-8">
      <Card className="max-w-2xl border-dashed">
        <CardHeader>
          <CardTitle>{title}</CardTitle>
          {description ? <CardDescription>{description}</CardDescription> : null}
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          This section is scaffolded to match the dashboard navigation. Hook it to the API when you are ready.
        </CardContent>
      </Card>
    </div>
  )
}
