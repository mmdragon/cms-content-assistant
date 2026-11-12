const dateFormat = new Intl.DateTimeFormat("en-US", {
  year: "numeric",
  month: "short",
  day: "numeric",
  timeZone: "UTC",
});

const dateTimeFormat = new Intl.DateTimeFormat("en-US", {
  year: "numeric",
  month: "short",
  day: "numeric",
  hour: "numeric",
  minute: "2-digit",
  second: "2-digit",
  timeZone: "UTC",
  timeZoneName: "short",
});

export function formatDate(iso: string): string {
  return dateFormat.format(new Date(iso));
}

export function formatDateTime(iso: string): string {
  return dateTimeFormat.format(new Date(iso));
}

export const FIELD_LABELS: Record<string, string> = {
  title: "Title",
  content: "Body content",
  meta_title: "Meta title",
  meta_description: "Meta description",
};

export const CATEGORY_LABELS: Record<string, string> = {
  community: "Community",
  home: "Floor plan",
  blog: "Blog",
  faq: "FAQ",
  landing: "Landing page",
};

export const META_TITLE_MAX = 60;
export const META_DESCRIPTION_MAX = 160;
