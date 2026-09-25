import { useQuery } from "@tanstack/react-query";

import { catalogue } from "../api/endpoints";

const HOUR = 60 * 60 * 1000;

export function useCategories() {
  return useQuery({ queryKey: ["categories"], queryFn: catalogue.categories, staleTime: HOUR });
}

export function useCategory(slug) {
  return useQuery({
    queryKey: ["category", slug],
    queryFn: () => catalogue.category(slug),
    staleTime: HOUR,
    enabled: Boolean(slug),
  });
}

export function useLocationTree() {
  return useQuery({ queryKey: ["location-tree"], queryFn: catalogue.locationTree, staleTime: HOUR });
}

export function useAllServices() {
  return useQuery({
    queryKey: ["services", "all"],
    queryFn: () => catalogue.services({ page_size: 100 }),
    staleTime: HOUR,
    select: (data) => data.results,
  });
}

export function flattenAreas(tree) {
  const rows = [];
  (tree ?? []).forEach((city) => {
    city.children.forEach((thana) => {
      rows.push({ id: thana.id, label: thana.name, level: "thana", thanaName: thana.name });
      thana.children.forEach((area) => {
        rows.push({ id: area.id, label: `${area.name}, ${thana.name}`, level: "area", thanaName: thana.name });
      });
    });
  });
  return rows;
}
