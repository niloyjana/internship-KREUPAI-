'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Search, X, Clock, ArrowUp, ArrowDown, CornerDownLeft } from 'lucide-react';
import { useCommandPalette } from './CommandPaletteProvider';
import { SearchResult, type SearchResultItem, type SearchResultCategory } from './SearchResult';

// ---------------------------------------------------------------------------
// Static page/route search data
// ---------------------------------------------------------------------------

const STATIC_PAGES: SearchResultItem[] = [
  {
    id: 'page-dashboard',
    title: 'Dashboard',
    description: 'Overview of your AI workforce activity and metrics',
    category: 'Pages',
    route: '/dashboard',
    icon: 'dashboard',
  },
  {
    id: 'page-analytics',
    title: 'Analytics',
    description: 'Performance analytics overview',
    category: 'Pages',
    route: '/analytics',
    icon: 'analytics',
  },
  {
    id: 'page-analytics-performance',
    title: 'Performance Analytics',
    description: 'Agent performance metrics, success rates, and trends',
    category: 'Pages',
    route: '/analytics/performance',
    icon: 'performance',
  },
  {
    id: 'page-analytics-cost',
    title: 'Cost Analytics',
    description: 'Token usage, LLM spend, and cost breakdowns',
    category: 'Pages',
    route: '/analytics/cost',
    icon: 'cost',
  },
  {
    id: 'page-analytics-compliance',
    title: 'Compliance',
    description: 'Activity audit trail and compliance logs',
    category: 'Pages',
    route: '/analytics/compliance',
    icon: 'audit',
  },
  {
    id: 'page-workforce',
    title: 'Workforce',
    description: 'Active AI agents overview and management',
    category: 'Pages',
    route: '/workforce',
    icon: 'workforce',
  },
  {
    id: 'page-workforce-catalog',
    title: 'Agent Catalog',
    description: 'Browse and subscribe to available AI agents',
    category: 'Pages',
    route: '/workforce/catalog',
    icon: 'catalog',
  },
  {
    id: 'page-tasks',
    title: 'Tasks',
    description: 'Task queue, workflow executions and history',
    category: 'Pages',
    route: '/tasks',
    icon: 'tasks',
  },
  {
    id: 'page-tasks-live',
    title: 'Live Tasks',
    description: 'Real-time view of currently running workflows',
    category: 'Pages',
    route: '/tasks/live',
    icon: 'live',
  },
  {
    id: 'page-tasks-escalations',
    title: 'Escalations',
    description: 'Review and manage escalated agent issues',
    category: 'Pages',
    route: '/tasks/escalations',
    icon: 'escalations',
  },
  {
    id: 'page-integrations',
    title: 'Integrations',
    description: 'Connect and manage third-party integrations',
    category: 'Pages',
    route: '/integrations',
    icon: 'integrations',
  },
  {
    id: 'page-billing',
    title: 'Billing',
    description: 'Subscription plans, usage, and invoices',
    category: 'Pages',
    route: '/billing',
    icon: 'billing',
  },
  {
    id: 'page-settings',
    title: 'Settings',
    description: 'Platform settings, team management, and preferences',
    category: 'Pages',
    route: '/settings',
    icon: 'settings',
  },
];

// ---------------------------------------------------------------------------
// Recent searches (persisted in localStorage)
// ---------------------------------------------------------------------------

const RECENT_SEARCHES_KEY = 'aisa:recent-searches';
const MAX_RECENT = 5;

function getRecentSearches(): SearchResultItem[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = localStorage.getItem(RECENT_SEARCHES_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveRecentSearch(item: SearchResultItem) {
  try {
    const current = getRecentSearches().filter((r) => r.id !== item.id);
    const updated = [item, ...current].slice(0, MAX_RECENT);
    localStorage.setItem(RECENT_SEARCHES_KEY, JSON.stringify(updated));
  } catch {
    // localStorage might be unavailable
  }
}

// ---------------------------------------------------------------------------
// Search logic — client-side filter against static pages + API data
// ---------------------------------------------------------------------------

function filterResults(query: string, items: SearchResultItem[]): SearchResultItem[] {
  const q = query.toLowerCase().trim();
  if (!q) return [];

  return items.filter(
    (item) =>
      item.title.toLowerCase().includes(q) ||
      item.description.toLowerCase().includes(q) ||
      item.category.toLowerCase().includes(q),
  );
}

function groupByCategory(
  items: SearchResultItem[],
): { category: SearchResultCategory; items: SearchResultItem[] }[] {
  const order: SearchResultCategory[] = ['Pages', 'Agents', 'Tasks', 'Integrations'];
  const map = new Map<SearchResultCategory, SearchResultItem[]>();

  for (const item of items) {
    const list = map.get(item.category) || [];
    list.push(item);
    map.set(item.category, list);
  }

  return order
    .filter((cat) => map.has(cat))
    .map((cat) => ({ category: cat, items: map.get(cat)! }));
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function CommandPalette() {
  const router = useRouter();
  const { isOpen, closePalette } = useCommandPalette();
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [recentSearches, setRecentSearches] = useState<SearchResultItem[]>([]);

  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [debouncedQuery, setDebouncedQuery] = useState('');

  // Debounce the search query
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setDebouncedQuery(query);
    }, 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query]);

  // Compute results
  const allResults = useMemo(() => filterResults(debouncedQuery, STATIC_PAGES), [debouncedQuery]);

  const grouped = useMemo(() => groupByCategory(allResults), [allResults]);
  const flatResults = useMemo(() => grouped.flatMap((g) => g.items), [grouped]);

  // Load recent searches when modal opens
  useEffect(() => {
    if (isOpen) {
      setRecentSearches(getRecentSearches());
      setQuery('');
      setDebouncedQuery('');
      setSelectedIndex(0);
    }
  }, [isOpen]);

  // Focus input on open
  useEffect(() => {
    if (isOpen) {
      // Small delay to allow the dialog to render
      requestAnimationFrame(() => {
        inputRef.current?.focus();
      });
    }
  }, [isOpen]);

  // Items for display: either search results or recent searches
  const showRecent = !debouncedQuery.trim() && recentSearches.length > 0;
  const displayItems = showRecent ? recentSearches : flatResults;

  // Reset selected index when results change
  useEffect(() => {
    setSelectedIndex(0);
  }, [debouncedQuery]);

  // Navigate to a result
  const navigateTo = useCallback(
    (item: SearchResultItem) => {
      saveRecentSearch(item);
      closePalette();
      router.push(item.route);
    },
    [closePalette, router],
  );

  // Keyboard navigation
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          setSelectedIndex((prev) => (prev < displayItems.length - 1 ? prev + 1 : 0));
          break;
        case 'ArrowUp':
          e.preventDefault();
          setSelectedIndex((prev) => (prev > 0 ? prev - 1 : displayItems.length - 1));
          break;
        case 'Enter':
          e.preventDefault();
          if (displayItems[selectedIndex]) {
            navigateTo(displayItems[selectedIndex]);
          }
          break;
        case 'Escape':
          e.preventDefault();
          closePalette();
          break;
      }
    },
    [displayItems, selectedIndex, navigateTo, closePalette],
  );

  // Scroll selected item into view
  useEffect(() => {
    const el = listRef.current?.querySelector('[aria-selected="true"]');
    if (el) {
      el.scrollIntoView({ block: 'nearest' });
    }
  }, [selectedIndex]);

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-[100] bg-black/40 backdrop-blur-sm transition-opacity"
        onClick={closePalette}
        aria-hidden
      />

      {/* Modal */}
      <div
        className="fixed inset-0 z-[101] flex items-start justify-center pt-[15vh] px-4"
        onClick={closePalette}
      >
        <div
          role="combobox"
          aria-expanded="true"
          aria-haspopup="listbox"
          className="w-full max-w-xl bg-white rounded-2xl shadow-2xl border border-gray-200 overflow-hidden animate-command-palette-in"
          onClick={(e) => e.stopPropagation()}
          onKeyDown={handleKeyDown}
        >
          {/* Search input */}
          <div className="flex items-center gap-3 px-4 border-b border-gray-100">
            <Search className="w-5 h-5 text-gray-400 flex-shrink-0" />
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search pages, agents, tasks..."
              className="flex-1 py-4 text-sm text-gray-900 placeholder:text-gray-400 bg-transparent outline-none"
              aria-label="Search"
              autoComplete="off"
              spellCheck={false}
            />
            {query && (
              <button
                onClick={() => {
                  setQuery('');
                  inputRef.current?.focus();
                }}
                className="p-1 rounded-md text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
                aria-label="Clear search"
              >
                <X className="w-4 h-4" />
              </button>
            )}
            <kbd className="hidden sm:inline-flex items-center gap-0.5 px-2 py-1 text-[10px] font-medium text-gray-400 bg-gray-50 border border-gray-200 rounded-md">
              ESC
            </kbd>
          </div>

          {/* Results list */}
          <div
            ref={listRef}
            role="listbox"
            className="max-h-[360px] overflow-y-auto overscroll-contain"
          >
            {/* Recent searches (when input is empty) */}
            {showRecent && (
              <div>
                <div className="flex items-center gap-2 px-4 pt-3 pb-2">
                  <Clock className="w-3.5 h-3.5 text-gray-400" />
                  <span className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider">
                    Recent
                  </span>
                </div>
                {recentSearches.map((item, idx) => (
                  <SearchResult
                    key={item.id}
                    item={item}
                    isSelected={idx === selectedIndex}
                    query=""
                    onClick={() => navigateTo(item)}
                    onMouseEnter={() => setSelectedIndex(idx)}
                  />
                ))}
              </div>
            )}

            {/* Grouped search results */}
            {debouncedQuery.trim() && allResults.length > 0 && (
              <>
                {grouped.map((group) => {
                  // Calculate the start index for this group within flatResults
                  const groupStartIndex = flatResults.indexOf(group.items[0]);
                  return (
                    <div key={group.category}>
                      <div className="px-4 pt-3 pb-2">
                        <span className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider">
                          {group.category}
                        </span>
                      </div>
                      {group.items.map((item, idx) => (
                        <SearchResult
                          key={item.id}
                          item={item}
                          isSelected={groupStartIndex + idx === selectedIndex}
                          query={debouncedQuery}
                          onClick={() => navigateTo(item)}
                          onMouseEnter={() => setSelectedIndex(groupStartIndex + idx)}
                        />
                      ))}
                    </div>
                  );
                })}
              </>
            )}

            {/* No results */}
            {debouncedQuery.trim() && allResults.length === 0 && (
              <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
                <Search className="w-10 h-10 text-gray-200 mb-3" />
                <p className="text-sm font-medium text-gray-500">No results found</p>
                <p className="text-xs text-gray-400 mt-1">
                  Try searching for pages like &quot;Dashboard&quot; or &quot;Settings&quot;
                </p>
              </div>
            )}

            {/* Empty state (no query, no recent) */}
            {!debouncedQuery.trim() && recentSearches.length === 0 && (
              <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
                <Search className="w-10 h-10 text-gray-200 mb-3" />
                <p className="text-sm font-medium text-gray-500">Start typing to search</p>
                <p className="text-xs text-gray-400 mt-1">
                  Search pages, agents, tasks, and integrations
                </p>
              </div>
            )}
          </div>

          {/* Footer with keyboard hints */}
          <div className="flex items-center justify-between gap-4 px-4 py-2.5 border-t border-gray-100 bg-gray-50/50">
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1">
                <kbd className="inline-flex items-center justify-center w-5 h-5 text-[10px] font-medium text-gray-400 bg-white border border-gray-200 rounded">
                  <ArrowUp className="w-3 h-3" />
                </kbd>
                <kbd className="inline-flex items-center justify-center w-5 h-5 text-[10px] font-medium text-gray-400 bg-white border border-gray-200 rounded">
                  <ArrowDown className="w-3 h-3" />
                </kbd>
                <span className="text-[11px] text-gray-400 ml-1">Navigate</span>
              </div>
              <div className="flex items-center gap-1">
                <kbd className="inline-flex items-center justify-center h-5 px-1.5 text-[10px] font-medium text-gray-400 bg-white border border-gray-200 rounded">
                  <CornerDownLeft className="w-3 h-3" />
                </kbd>
                <span className="text-[11px] text-gray-400 ml-1">Open</span>
              </div>
              <div className="flex items-center gap-1">
                <kbd className="inline-flex items-center justify-center h-5 px-1.5 text-[10px] font-medium text-gray-400 bg-white border border-gray-200 rounded">
                  Esc
                </kbd>
                <span className="text-[11px] text-gray-400 ml-1">Close</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
